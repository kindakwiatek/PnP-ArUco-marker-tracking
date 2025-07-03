import socket
import json
import config # Import config to get the port number

# --- Configuration ---
HOST = config.NETWORK_HOST
PORT = config.NETWORK_PORT

# --- Client Logic ---
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print(f"Connecting to server at {HOST}:{PORT}...")
        s.connect((HOST, PORT))
        print("Connected! Waiting for 2D coordinate data...")
        
        # Use makefile for easy line-by-line reading from the socket
        f = s.makefile()
        
        while True:
            line = f.readline()
            if not line:
                break # Server closed connection
            
            try:
                # Deserialize the JSON string back into a list of marker dictionaries
                marker_positions = json.loads(line)
                
                # Clear the console line for clean output
                print("\033[K", end='') 
                
                if not marker_positions:
                    print("No markers detected.", end='\r')
                else:
                    output_str = ""
                    for marker in marker_positions:
                        x, y = marker['pos']
                        output_str += f"ID: {marker['id']:<2} | Pos (X,Y): ({x:<4}, {y:<4})   "
                    # Print the formatted string, using '\r' to return to the start of the line
                    print(output_str, end='\r')

            except json.JSONDecodeError:
                # This might happen if the client connects mid-stream
                print("Received incomplete data. Waiting for next message...", end='\r')

except ConnectionRefusedError:
    print(f"Connection refused. Is the server script running on {HOST}?")
except KeyboardInterrupt:
    print("\nClient stopped by user.")
finally:
    print("\nConnection closed.")
