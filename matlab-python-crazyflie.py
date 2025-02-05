import time
import socket
import struct
from threading import Thread, Event
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.util import uri_helper

# Initialize the library
import cflib.crtp
cflib.crtp.init_drivers()

# Set the URI of your Crazyflie
URI = uri_helper.uri_from_env(default='radio://0/80/2M')

# UDP Configuration
udp_ip = "127.0.0.1"
udp_port = 52001
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((udp_ip, udp_port))

# Shared data structure for roll, pitch, yaw
control_data = {'roll': 0, 'pitch': 0, 'yaw_rate': 0, 'thrust': 0}
stop_event = Event()

def udp_listener():
    """Listens for UDP packets and updates control data."""
    global control_data
    while not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(1024)
            if len(data) == 6:
                roll, pitch, yaw_rate = struct.unpack('<hhh', data)
                control_data['roll'] = roll / 100  # Scale appropriately
                control_data['pitch'] = pitch / 100  # Scale appropriately
                control_data['yaw_rate'] = yaw_rate / 100  # Scale appropriately
                control_data['thrust'] = 40000  # Example thrust value
            else:
                print(f"Unexpected data length: {len(data)}. Skipping...")
        except Exception as e:
            print(f"UDP listener error: {e}")
            break

def send_attitude_commands(scf):
    """Sends attitude commands to the Crazyflie."""
    commander = scf.cf.commander
    try:
        print("Sending attitude commands...")
        while not stop_event.is_set():
            roll = control_data['roll']
            pitch = control_data['pitch']
            yaw_rate = control_data['yaw_rate']
            thrust = control_data['thrust']
            
            commander.send_setpoint(roll, pitch, yaw_rate, thrust)
            time.sleep(0.1)  # Send commands at ~10Hz
    finally:
        # Stop sending commands to land the Crazyflie
        commander.send_setpoint(0, 0, 0, 0)

# Start UDP listener in a separate thread
listener_thread = Thread(target=udp_listener)
listener_thread.start()

try:
    # Connect to the Crazyflie and start sending commands
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
        send_attitude_commands(scf)
except KeyboardInterrupt:
    print("Interrupted by user.")
finally:
    stop_event.set()
    listener_thread.join()
    sock.close()
    print("Resources cleaned up. Exiting...")
