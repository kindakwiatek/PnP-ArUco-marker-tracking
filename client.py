"""
client.py

This script runs on the main control computer. It performs the following:
- Connects to multiple Raspberry Pi servers.
- Sends commands to the servers (e.g., to start streaming or PnP calibration).
- Receives 2D marker coordinate data from each server.
- Triangulates the 3D position of markers using data from multiple cameras.
- Displays the final 3D coordinates of the tracked markers.
"""

import socket
import json
import threading
import time
import numpy as np
import config


# --- Global Data Structures ---
# Thread-safe dictionary to store the latest marker data from all servers.
# Format: {marker_id: {server_host: (x, y), ...}, ...}
live_marker_data = {}
data_lock = threading.Lock()


class CameraClient:
    """Manages the connection and state for a single Raspberry Pi server."""
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.is_connected = False
        self.state = "Disconnected"
        self.listener_thread = None

    def connect(self):
        """
        Attempts to establish a TCP connection to the server.
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5) # 5-second timeout for connection
            self.sock.connect((self.host, self.port))
            self.is_connected = True
            self.state = "Connected"
            print(f"[{self.host}] Connection successful.")
            
            # Start a dedicated thread to listen for data from this server.
            self.listener_thread = threading.Thread(target=self.listen_for_data)
            self.listener_thread.daemon = True
            self.listener_thread.start()
            return True
        except (ConnectionRefusedError, socket.gaierror, socket.timeout) as e:
            print(f"[{self.host}] Connection failed: {e}")
            return False

    def listen_for_data(self):
        """
        Listens for incoming data from the server in a separate thread.
        """
        f = self.sock.makefile()
        while self.is_connected:
            try:
                line = f.readline()
                if not line:
                    self.disconnect()
                    break
                self._process_server_message(line.strip())
            except (IOError, ConnectionResetError):
                self.disconnect()
                break

    def _process_server_message(self, message):
        """
        Processes incoming JSON data from the server and updates the
        global marker data dictionary.
        """
        global live_marker_data
        try:
            marker_positions = json.loads(message)
            with data_lock:
                # Update data for the received markers from this specific host.
                for marker in marker_positions:
                    marker_id = marker['id']
                    if marker_id not in live_marker_data:
                        live_marker_data[marker_id] = {}
                    live_marker_data[marker_id][self.host] = tuple(marker['pos'])
        except json.JSONDecodeError:
            # Silently ignore malformed data or status messages.
            pass

    def send_command(self, command):
        """Sends a command string to the server."""
        if self.is_connected:
            try:
                self.sock.sendall(f"{command}\n".encode('utf-8'))
                return True
            except (ConnectionResetError, BrokenPipeError):
                self.disconnect()
                return False
        return False

    def disconnect(self):
        """Cleans up the connection resources."""
        if self.is_connected:
            self.is_connected = False
            self.state = "Disconnected"
            if self.sock:
                self.sock.close()
            print(f"\n[{self.host}] Disconnected.")


def broadcast_command(command, clients):
    """Sends a command to all connected servers."""
    print(f"\nBroadcasting command: '{command}'...")
    for client in clients.values():
        client.send_command(command)


# --- 3D Triangulation (Assuming PnP has been completed) ---

def triangulate_marker_position(observations, camera_poses, camera_matrix, dist_coeffs):
    """
    Calculates the 3D position of a marker from multiple 2D observations
    using cv2.triangulatePoints.

    Note: This requires pre-calibrated camera poses from a PnP process.
    """
    if len(observations) < 2:
        return None # Triangulation requires at least two views.

    proj_matrices = []
    points_2d = []

    for host, point_2d in observations.items():
        if host not in camera_poses:
            continue
            
        pose = camera_poses[host]
        rvec = pose['rvec']
        tvec = pose['tvec']
        
        # Create projection matrix: P = K * [R | t]
        R, _ = cv2.Rodrigues(rvec)
        extrinsic_matrix = np.hstack((R, tvec))
        proj_matrix = camera_matrix @ extrinsic_matrix
        
        proj_matrices.append(proj_matrix)
        points_2d.append(np.array(point_2d, dtype=np.float32))

    if len(proj_matrices) < 2:
        return None
        
    # Prepare points for triangulation
    points1 = points_2d[0].reshape(2, 1)
    points2 = points_2d[1].reshape(2, 1)
    
    # Triangulate
    points_4d_hom = cv2.triangulatePoints(proj_matrices[0], proj_matrices[1], points1, points2)
    
    # Convert from homogeneous to 3D coordinates
    points_3d = (points_4d_hom[:3] / points_4d_hom[3]).flatten()
    
    return points_3d


def triangulation_thread_func():
    """
    A thread that continuously calculates and prints 3D marker positions.
    """
    # Load the shared camera intrinsic parameters.
    try:
        with open(config.DISTORTION_DATA_FILE, 'r') as f:
            calib_data = json.load(f)
        camera_matrix = np.array(calib_data['camera_matrix'])
        dist_coeffs = np.array(calib_data['distortion_coefficients'])
    except FileNotFoundError:
        print("[Triangulation] Distortion calibration file not found. Cannot proceed.")
        return

    # Load the pre-calculated camera poses (extrinsic parameters).
    # In a real system, you would fetch these from each Pi after PnP.
    camera_poses = {}
    for host in config.SERVER_HOSTS:
        pose_file = f"pnp_camera_pose_{host}.json" # Assumes a naming convention
        try:
            with open(pose_file, 'r') as f:
                pose_data = json.load(f)
                camera_poses[host] = {
                    'rvec': np.array(pose_data['rotation_vector']),
                    'tvec': np.array(pose_data['translation_vector'])
                }
                print(f"Loaded camera pose for {host}.")
        except FileNotFoundError:
            print(f"Warning: PnP pose file not found for {host}. It cannot be used for triangulation.")

    if len(camera_poses) < 2:
        print("Error: Fewer than two camera poses are available. Triangulation is not possible.")
        return

    while True:
        time.sleep(0.1)  # Control the update rate.
        with data_lock:
            if not live_marker_data:
                continue
            
            output_lines = []
            for marker_id, observations in live_marker_data.items():
                pos_3d = triangulate_marker_position(observations, camera_poses, camera_matrix, dist_coeffs)
                if pos_3d is not None:
                    line = f"  ID: {marker_id:<2} | World Pos (X,Y,Z): ({pos_3d[0]:6.1f}, {pos_3d[1]:6.1f}, {pos_3d[2]:6.1f}) cm"
                    output_lines.append(line)
            
            # Clear the screen and print updated positions
            os.system('cls' if os.name == 'nt' else 'clear')
            print("--- Live 3D Marker Positions ---")
            if output_lines:
                print("\n".join(output_lines))
            else:
                print("  (No markers detected by multiple cameras)")
            print("--------------------------------")


def main():
    """Main function to handle user commands and manage server connections."""
    server_clients = {}
    # Connect to all servers defined in the config.
    for host in config.SERVER_HOSTS:
        client = CameraClient(host, config.NETWORK_PORT)
        if client.connect():
            server_clients[host] = client

    if not server_clients:
        print("Could not connect to any servers. Exiting.")
        return

    triangulation_thread = None

    # --- Main Command Loop ---
    while True:
        print("\n--- Motion Capture Control ---")
        for host, client in server_clients.items():
            print(f"  - {host}: {client.state}")
        print("\nCommands: [stream], [stop], [pnp] (Not Implemented), [quit]")
        command = input("Enter command: ").strip().lower()

        if command == "stream":
            broadcast_command("start_stream", server_clients)
            # Start the triangulation thread if it's not already running.
            if triangulation_thread is None or not triangulation_thread.is_alive():
                print("Starting 3D triangulation process...")
                triangulation_thread = threading.Thread(target=triangulation_thread_func)
                triangulation_thread.daemon = True
                triangulation_thread.start()
            print("Broadcast 'start_stream' command to all servers.")

        elif command == "stop":
            broadcast_command("stop_stream", server_clients)
            # The triangulation thread will continue running but will see no new data.
            print("Broadcast 'stop_stream' command to all servers.")

        elif command == "pnp":
            print("PnP command is not yet implemented in this version.")
            # Here you would implement the logic to trigger PnP on servers
            # and retrieve the resulting pose files.

        elif command == "quit":
            for client in server_clients.values():
                client.disconnect()
            break
        else:
            print("Invalid command.")

    print("Client application shut down.")


if __name__ == "__main__":
    main()