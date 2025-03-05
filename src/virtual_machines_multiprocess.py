import multiprocessing
import threading
import socket
import random
import time
import queue
import datetime
import os

class VirtualMachine:
    """Class representing a single virtual machine in a distributed system.
    
    Attributes:
        vm_id: An integer identifying the virtual machine.
        clock_rate: An integer (1-6) indicating ticks per second.
        logical_clock: An integer tracking the logical clock time.
        peers: A list of peer VM IDs to communicate with.
        message_queue: A queue for storing incoming messages.
        lock: A threading lock for synchronization.
        log_file: An open file for writing logs.
        running: A boolean indicating if the VM is running.
    """

    def __init__(self, vm_id, peers, simulation_id):
        """Initialize the virtual machine with its parameters.
        
        Args:
            vm_id: Identifier for the virtual machine.
            peers: List of peer VM IDs to communicate with.
            simulation_id (int): The ID of the simulation run.
        """
        self.vm_id = vm_id
        self.clock_rate = random.randint(1, 6)  # Ticks per second
        self.logical_clock = 0
        self.peers = peers
        
        self.network_queue = queue.Queue()  # Incoming network messages
        self.message_queue = queue.Queue()  # Messages ready for processing
        self.lock = threading.Lock()
        
        os.makedirs('logs', exist_ok=True)
        self.log_file = open(f'logs/sim{simulation_id}_vm{vm_id}_log.txt', 'w')
        self.running = True

        print(f"VM{self.vm_id} on localhost:{5000 + self.vm_id} started with clock rate {self.clock_rate} ticks/second")

        # Log initialization information
        self.log_file.write(f"============= VM{vm_id} LOG START =============\n")
        self.log_file.write(f"Clock rate: {self.clock_rate} ticks per second\n")
        self.log_file.write(f"Peers: {peers}\n\n")
        self.log_file.flush()

        # Start server thread for listening to incoming messages
        self.server_thread = threading.Thread(target=self.listen_for_messages)
        self.server_thread.daemon = True
        self.server_thread.start()

    def listen_for_messages(self):
        """Thread for receiving messages and storing them in the network queue."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("localhost", 5000 + self.vm_id))
        server_socket.listen(len(self.peers))
        server_socket.settimeout(1.0)  # Allow periodic checking for shutdown

        self.server_socket = server_socket  # Save reference to close later

        while self.running:
            try:
                conn, addr = server_socket.accept()
                client_handler = threading.Thread(
                    target=self.handle_client,
                    args=(conn,)
                )
                client_handler.daemon = True
                client_handler.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"VM{self.vm_id} server error: {e}")
        
        server_socket.close()
    
    def handle_client(self, conn):
        """Handle an individual client connection.
        
        Args:
            conn: Socket connection to client.
        """
        try:
            message = conn.recv(1024).decode()
            if message:
                self.network_queue.put(int(message))  # Store in network queue
            conn.close()
        except Exception as e:
            print(f"VM{self.vm_id} error handling client: {e}")

    def send_message(self, recipient_id):
        """Send logical clock time to another VM."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(("localhost", 5000 + recipient_id))
                s.sendall(str(self.logical_clock).encode())
        except ConnectionRefusedError:
            print(f"VM{self.vm_id}: Connection refused when sending to VM{recipient_id}")
        except Exception as e:
            print(f"VM{self.vm_id} error sending message: {e}")

    def log_event(self, event_type, received_time=None):
        """Log an event with formatted details.
        
        Args:
            event_type: Type of event (Received, Sent, Internal).
            received_time: For received messages, the logical time received.
        """
        system_time = datetime.datetime.now()
        queue_length = self.message_queue.qsize()

        if event_type == "Received":
            log_entry = (
                f"{event_type}: {received_time} | "
                f"System time: {system_time} | "
                f"Logical Clock Time: {self.logical_clock} | "
                f"Message Queue Length: {queue_length}\n"
            )
        elif event_type == "Sent":
            log_entry = (
                f"{event_type}: {self.logical_clock} | "
                f"System time: {system_time} | "
                f"Logical Clock Time: {self.logical_clock}\n"
            )
        else:  # Internal event
            log_entry = (
                f"Internal event | "
                f"System time: {system_time} | "
                f"Logical Clock Time: {self.logical_clock}\n"
            )

        self.log_file.write(log_entry)
        self.log_file.flush()

    def run(self):
        """Main execution loop for the virtual machine."""
        time.sleep(1)  # Allow all VMs to start

        while self.running:
            start_time = time.time()

            # Move messages from network queue to message queue
            while not self.network_queue.empty():
                self.message_queue.put(self.network_queue.get_nowait())

            # Process messages in the message queue
            if not self.message_queue.empty():
                with self.lock:
                    received_time = self.message_queue.get_nowait()
                    self.logical_clock = max(self.logical_clock, received_time) + 1
                self.log_event("Received", received_time)
            else:
                # No incoming messages, generate an event
                event_type = random.randint(1, 10)
                with self.lock:
                    self.logical_clock += 1

                if event_type == 1 and len(self.peers) > 0:
                    # Send to one random peer
                    self.send_message(self.peers[0])
                    self.log_event("Sent")
                elif event_type == 2 and len(self.peers) > 1:
                    # Send to another random peer
                    self.send_message(self.peers[1])
                    self.log_event("Sent")
                elif event_type == 3:
                    # Send to all peers
                    for peer in self.peers:
                        self.send_message(peer)
                    self.log_event("Sent")
                else:
                    # Internal event (values 4-10)
                    self.log_event("Internal")

            elapsed = time.time() - start_time
            sleep_time = max(0, (1 / self.clock_rate) - elapsed)
            time.sleep(sleep_time)

    def stop(self):
        """Stop the virtual machine and clean up resources."""
        self.running = False
        if hasattr(self, 'server_socket'):  # Check if server socket exists
            self.server_socket.close()  # Close socket to free port
        if self.log_file and not self.log_file.closed:  # Check if file is open before writing
            self.log_file.write("\n============= VM LOG END =============\n")
            self.log_file.close()
        print(f"VM{self.vm_id} stopped")

def run_vm(vm_id, peers, simulation_id):
    vm = VirtualMachine(vm_id, peers, simulation_id)
    vm.run()

def run_simulation(simulation_id):
    """
    Runs a single instance of the virtual machine simulation.

    Args:
        simulation_id (int): The ID of the simulation run.
    
    This function initializes and runs a set of virtual machines, each running
    in a separate thread. The VMs communicate with each other and maintain
    logical clocks. The simulation runs for 60 seconds before shutting down.
    """
    num_machines = 3
    processes = []
    
    for vm_id in range(num_machines):
        peers = [j for j in range(num_machines) if j != vm_id]
        p = multiprocessing.Process(target=run_vm, args=(vm_id, peers, simulation_id))
        p.start()
        processes.append(p)
    
    try:
        print(f"Simulation {simulation_id} running for 60 seconds...")
        time.sleep(60)
    except KeyboardInterrupt:
        print("Simulation interrupted by user")
    
    for p in processes:
        p.terminate()
    
    for p in processes:
        p.join()
    
    time.sleep(3)
    print(f"Simulation {simulation_id} complete. Check log files for details.")

def main():
    """
    Runs multiple simulations sequentially.

    This function runs the virtual machine simulation five times,
    each for a duration of 60 seconds.
    """
    for i in range(1, 6):
        run_simulation(i)

if __name__ == "__main__":
    main()