import threading
import socket
import random
import time
import queue

class VirtualMachine:
    def __init__(self, vm_id, peers):
        self.vm_id = vm_id
        self.clock_rate = random.randint(1, 6)
        self.logical_clock = 0
        self.peers = peers
        self.message_queue = queue.Queue()
        self.lock = threading.Lock()
        self.log_file = open(f'vm_{vm_id}_log.txt', 'w')
        self.running = True

        # Start server thread
        self.server_thread = threading.Thread(target=self.listen_for_messages)
        self.server_thread.start()

    def listen_for_messages(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(("localhost", 5000 + self.vm_id))
        server_socket.listen(len(self.peers))

        while self.running:
            conn, _ = server_socket.accept()
            message = conn.recv(1024).decode()
            conn.close()
            if message:
                self.message_queue.put(int(message))
    
    def send_message(self, recipient_id):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(("localhost", 5000 + recipient_id))
                s.sendall(str(self.logical_clock).encode())
        except ConnectionRefusedError:
            pass  # Ignore if peer not yet listening

    def log_event(self, event_type, extra=""):
        system_time = time.time()
        self.log_file.write(f"{event_type} | System Time: {system_time:.4f} | Logical Clock: {self.logical_clock} {extra}\n")
        self.log_file.flush()

    def run(self):
        while self.running:
            time.sleep(1 / self.clock_rate)

            if not self.message_queue.empty():
                received_time = self.message_queue.get()
                with self.lock:
                    self.logical_clock = max(self.logical_clock, received_time + 1)
                self.log_event("Received", f"| Queue Length: {self.message_queue.qsize()}")
            else:
                event_type = random.randint(1, 10)
                if event_type == 1:
                    self.send_message(random.choice(self.peers))
                elif event_type == 2:
                    self.send_message(random.choice(self.peers))
                elif event_type == 3:
                    for peer in self.peers:
                        self.send_message(peer)
                with self.lock:
                    self.logical_clock += 1
                self.log_event("Internal Event" if event_type > 3 else "Sent")

    def stop(self):
        self.running = False
        self.server_thread.join()
        self.log_file.close()

if __name__ == "__main__":
    num_machines = 3
    machines = [VirtualMachine(i, [j for j in range(num_machines) if j != i]) for i in range(num_machines)]
    threads = [threading.Thread(target=m.run) for m in machines]
    
    for t in threads:
        t.start()
    
    time.sleep(60)  # Run for one minute
    
    for m in machines:
        m.stop()
    for t in threads:
        t.join()
