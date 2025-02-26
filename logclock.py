import threading
import socket
import random
import time
import queue
import datetime

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
    
    def __init__(self, vm_id, peers):
        """Initialize the virtual machine with its parameters.
        
        Args:
            vm_id: Identifier for the virtual machine.
            peers: List of peer VM IDs to communicate with.
        """
        self.vm_id = vm_id
        self.clock_rate = random.randint(1, 6)
        self.logical_clock = 0
        self.peers = peers
        self.message_queue = queue.Queue()
        self.lock = threading.Lock()
        self.log_file = open(f'VM_{vm_id}_log.txt', 'w')
        self.running = True
        
        # Log initialization information
        self.log_file.write(f"============= VM{vm_id} LOG START =============\n")
        self.log_file.write(f"Clock rate: {self.clock_rate} ticks per second\n")
        self.log_file.write(f"Peers: {peers}\n\n")
        self.log_file.flush()

        # Start server thread to listen for incoming messages
        self.server_thread = threading.Thread(target=self.listen_for_messages)
        self.server_thread.daemon = True
        self.server_thread.start()

    def listen_for_messages(self):
        """Thread for listening and receiving messages from other VMs."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("localhost", 5000 + self.vm_id))
        server_socket.listen(len(self.peers))
        server_socket.settimeout(1.0)  # Add timeout to allow clean shutdown
        
        print(f"VM{self.vm_id}: Listening on localhost:{5000 + self.vm_id}")

        while self.running:
            try:
                conn, addr = server_socket.accept()
                client_handler = threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr)
                )
                client_handler.daemon = True
                client_handler.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"VM{self.vm_id} server error: {e}")
        
        server_socket.close()
    
    def handle_client(self, conn, addr):
        """Handle an individual client connection.
        
        Args:
            conn: Socket connection to client.
            addr: Address of the client.
        """
        try:
            message = conn.recv(1024).decode()
            if message:
                self.message_queue.put(int(message))
            conn.close()
        except Exception as e:
            print(f"VM{self.vm_id} error handling client: {e}")
    
    def send_message(self, recipient_id):
        """Send logical clock time to another VM.
        
        Args:
            recipient_id: ID of the recipient VM.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(("localhost", 5000 + recipient_id))
                s.sendall(str(self.logical_clock).encode())
                s.close()
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
                f"Logical Clock Time: {self.logical_clock} |"
                f"Message Queue Length: {queue_length} \n"
            )
        elif event_type == "Sent":
            log_entry = (
                f"{event_type}: {self.logical_clock} | "
                f"System time: {system_time} | "
                f"Logical Clock Time] {self.logical_clock}\n"
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
        print(f"VM{self.vm_id} started with clock rate {self.clock_rate}")
        
        # Allow time for all VMs to start up
        time.sleep(1)
        
        while self.running:
            start_time = time.time()
            
            # Check for messages in the queue
            if not self.message_queue.empty():
                received_time = self.message_queue.get()
                with self.lock:
                    self.logical_clock = max(self.logical_clock, received_time) + 1
                self.log_event("Received", received_time)
            else:
                # No message in queue, generate an event
                event_type = random.randint(1, 10)
                with self.lock:
                    self.logical_clock += 1
                
                if event_type == 1:
                    # Send to one random peer
                    peer = self.peers[0]
                    self.send_message(peer)
                    self.log_event("Sent")
                elif event_type == 2:
                    # Send to another random peer
                    peer = self.peers[1]
                    self.send_message(peer)
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
        if self.log_file:
            self.log_file.write("\n============= VM LOG END =============\n")
            self.log_file.close()
        print(f"VM{self.vm_id} stopped")


def main():
    """Main function to initialize and run the virtual machines."""
    num_machines = 3
    machines = []
    
    # Create virtual machines
    for i in range(num_machines):
        peers = [j for j in range(num_machines) if j != i]
        machines.append(VirtualMachine(i, peers))
    
    # Log the clock rates
    print("Clock rates:")
    for i, m in enumerate(machines):
        print(f"VM{i}: {m.clock_rate} ticks/second")
    
    # Start all machines
    threads = []
    for m in machines:
        t = threading.Thread(target=m.run)
        t.start()
        threads.append(t)
    
    try:
        # Run for one minute
        print("System running for 60 seconds...")
        time.sleep(60)
    except KeyboardInterrupt:
        print("Interrupted by user")
    
    # Stop all machines
    for m in machines:
        m.stop()
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    print("All virtual machines stopped. Check log files for details.")


if __name__ == "__main__":
    main()