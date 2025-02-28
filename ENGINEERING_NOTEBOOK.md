# Engineering Notebook

## Project Overview

We aimed to simulate a distributed system with multiple virtual machines (VMs) running on a single physical machine. Each VM operates at its own speed (clock rate) and communicates with other VMs through socket connections.

## Design Decisions

### Processing Messages
We have two queues in our implementation:
1. Network Queue: A queue where incoming messages are initially stored when they arrive via a socket connection.
2. Message Queue: A separate queue that holds messages that are ready to be processed by the virtual machine on its logical clock cycle.
In our design, messages are first received in the network queue, which operates independently of the machine's clock cycle. The machine then moves messages from the network queue to the message queue, where they wait to be processed according to the machine’s clock rate. This separation ensures that network delays and processing delays are independent, just as in real-world distributed systems.

### Assigning Different Ports for Each VM 
Each VM listens on a different port because they're all running on the same machine (i.e. 127.0.0.1 or localhost). If they used the same port, there would be a conflict since only one process can bind to a specific port at a time.
We assign each VM a unique port by adding the VM's ID to a base port number (5000). So VM 0 listens on port 5000, VM 1 on port 5001, and VM 2 on port 5002.

### Each VM is Handled in a Separate Thread
Initially we thought to implement each of the VMs as a separate process but later decided to implement each VM in a separate thread for simplicity. We implemented the VirtualMachine class as a regular class and used threads to run each VM instance concurrently. This design allows VMs to execute independently while still sharing memory, making message passing easier without requiring inter-process communication.

Our implementation uses three threads to handle different aspects of each VM's operation:
1. Main Thread: Initializes the VMs and runs the main execution logic
2. Server Thread: Waits and listens for incoming messages
3. Client Handler Threads: Takes in incoming messages, and places them in the network queue
However, to ensure synchronization, only the main execution thread updates the logical clock. This prevents race conditions and ensures that logical time updates happen in a controlled manner.

### Continuous Server Listening Using Non-Blocking Sockets
We decided to keep the server continuously listening for incoming messages using a dedicated thread without blocking execution. Each incoming message spawns a new thread to handle the client request, allowing multiple messages to be received in parallel. A timeout mechanism ensures that the server remains responsive and can shut down gracefully when needed.

### Thread-Safe Synchronization with Locks
We use a thread lock to ensure that updates to the logical clock are atomic since multiple threads access the logical clock concurrently (main thread, message processing thread, network listener). This prevents race conditions where two threads might update the clock simultaneously, leading to inconsistencies.

### Logical Clock Update Following [Lamport's algorithm](https://en.wikipedia.org/wiki/Lamport_timestamp)
Each virtual machine maintains a logical clock that is updated based on Lamport’s logical clock rules:
1. If a message is received, the logical clock is updated to `max(local_clock, received_timestamp) + 1`.
2. If an internal event occurs, the logical clock is simply incremented by 1. This ensures that event ordering is maintained in the distributed system, even if messages arrive out of order.

---------------------------------

## Communication Flow

1. Initialization:
- Each VM starts a server thread (`listen_for_messages()`) that listens on its assigned port
- Each VM knows the IDs of its peer VMs
2. Sending Messages:
- When a VM decides to send a message (based on the random event 1-3), it calls `send_message(recipient_id)`
- This method creates a socket connection to the recipient's port: `s.connect(("localhost", 5000 + recipient_id))`
- It sends the current logical clock value as a message: s.`sendall(str(self.logical_clock).encode())`
3. Receiving Messages:
- The server thread accepts incoming connections: `conn, addr = server_socket.accept()`
- For each connection, it spawns a client handler thread
- The client handler reads the message from the connection: `message = conn.recv(1024).decode()`
- It puts the received logical clock value into the message queue: self.message_queue.put(int(message))
4. Processing Messages:
- In the `run()` method, each VM checks its message queue on each clock cycle
- If there's a message, it updates its logical clock according to the logical clock rules (taking the maximum of the received time and its own clock, then incrementing by 1)
- If there's no message, it generates a random event (internal or send)
