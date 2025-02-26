import socket
import threading
import queue
import time
import random
import json
from multiprocessing import Process

class VirtualMachine(Process):
    def __init__(self, port, other_ports, machine_id):
        super().__init__()
        self.port = port
        self.other_ports = sorted(other_ports)
        self.machine_id = machine_id
        self.clock_rate = random.randint(1, 6)
        self.logical_clock = 0
        self.message_queue = queue.Queue()
        self.outgoing_sockets = {}
        self.server_socket = None
        self.running = True
        self.connections = []

    def run(self):
        with open(f"machine_{self.machine_id}_log.txt", 'w') as log_file:
            self.start_server()
            self.connect_to_others()

            main_thread = threading.Thread(target=self.main_loop, args=(log_file,))
            main_thread.start()
            main_thread.join()

            self.cleanup()

    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('localhost', self.port))
        self.server_socket.listen(2)
        threading.Thread(target=self.accept_connections).start()

    def accept_connections(self):
        while self.running:
            try:
                client_socket, _ = self.server_socket.accept()
                self.connections.append(client_socket)
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
            except:
                break

    def handle_client(self, client_socket):
        buffer = b''
        while self.running:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    message = json.loads(line.decode())
                    self.message_queue.put(message)
            except:
                break

    def connect_to_others(self):
        for port in self.other_ports:
            connected = False
            while not connected and self.running:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect(('localhost', port))
                    self.outgoing_sockets[port] = sock
                    connected = True
                except:
                    time.sleep(0.1)

    def main_loop(self, log_file):
        while self.running:
            start_time = time.time()

            if not self.message_queue.empty():
                self.process_message(log_file)
            else:
                self.process_event(log_file)

            elapsed = time.time() - start_time
            sleep_time = max(0.0, (1.0 / self.clock_rate) - elapsed)
            time.sleep(sleep_time)

    def process_message(self, log_file):
        message = self.message_queue.get()
        received_time = message['logical_time']
        self.logical_clock = max(self.logical_clock, received_time) + 1
        log_entry = {
            'event': 'receive',
            'system_time': time.time(),
            'queue_length': self.message_queue.qsize(),
            'logical_time': self.logical_clock,
            'received_time': received_time
        }
        log_file.write(json.dumps(log_entry) + '\n')
        log_file.flush()

    def process_event(self, log_file):
        rand = random.randint(1, 10)
        if rand <= 3:
            recipients = self.other_ports[:] if rand == 3 else [self.other_ports[rand-1]]
            self.logical_clock += 1
            for port in recipients:
                sock = self.outgoing_sockets.get(port)
                if sock:
                    message = json.dumps({'logical_time': self.logical_clock, 'sender_port': self.port}) + '\n'
                    try:
                        sock.sendall(message.encode())
                    except:
                        pass
            log_entry = {
                'event': 'send',
                'system_time': time.time(),
                'logical_time': self.logical_clock,
                'recipients': recipients
            }
        else:
            self.logical_clock += 1
            log_entry = {
                'event': 'internal',
                'system_time': time.time(),
                'logical_time': self.logical_clock
            }
        log_file.write(json.dumps(log_entry) + '\n')
        log_file.flush()

    def cleanup(self):
        self.running = False
        for sock in self.outgoing_sockets.values():
            sock.close()
        self.server_socket.close()

if __name__ == '__main__':
    ports = [5000, 5001, 5002]
    processes = []
    for idx, port in enumerate(ports):
        other_ports = [p for p in ports if p != port]
        vm = VirtualMachine(port, other_ports, idx)
        processes.append(vm)
        vm.start()
    time.sleep(60)  # Run for 1 minute
    for vm in processes:
        vm.terminate()
    for vm in processes:
        vm.join()