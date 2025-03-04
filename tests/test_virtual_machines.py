import unittest
import threading
import time
import socket
import sys
import os

# Add 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Now import VirtualMachine
from virtual_machines import VirtualMachine


class TestVirtualMachine(unittest.TestCase):

    def setUp(self):
        """Set up two virtual machines for testing with enhanced validation"""
        self.simulation_id = 999  # Unique ID for testing logs
        
        self.vm1 = VirtualMachine(vm_id=0, peers=[1], simulation_id=self.simulation_id)
        self.vm2 = VirtualMachine(vm_id=1, peers=[0], simulation_id=self.simulation_id)

        # Ensure the server sockets are listening
        def check_port(port, max_attempts=10):
            for _ in range(max_attempts):
                try:
                    with socket.create_connection(("localhost", port), timeout=1):
                        return True  # Connection successful, meaning server is up
                except (ConnectionRefusedError, socket.timeout):
                    time.sleep(1)  # Wait and retry
            return False  # Server never came up

        # Verify VM servers are ready before proceeding
        if not check_port(5000 + self.vm1.vm_id) or not check_port(5000 + self.vm2.vm_id):
            self.fail("VM servers did not start successfully")

        # Start the VM processing threads
        self.vm1_thread = threading.Thread(target=self.vm1.run)
        self.vm2_thread = threading.Thread(target=self.vm2.run)

        self.vm1_thread.start()
        self.vm2_thread.start()

        time.sleep(3)

        if not (self.vm1.running and self.vm2.running):
            self.fail("VMs failed to start properly")

    def test_message_sending(self):
        """Test if VM1 can send a message to VM2 and VM2 receives it correctly"""
        # Ensure VM2 is still listening for connections
        original_processing = self.vm2.running
        self.vm2.running = True  

        # Pause VM2's processing momentarily without stopping the server
        time.sleep(1)

        # Ensure VM1's logical clock has a value before sending
        with self.vm1.lock:
            if self.vm1.logical_clock == 0:
                self.vm1.logical_clock = 1

        initial_clock = self.vm1.logical_clock

        # Get VM2's initial logical clock
        initial_vm2_clock = self.vm2.logical_clock

        # Directly send a message from VM1 to VM2
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                target_port = 5000 + self.vm2.vm_id
                s.connect(("localhost", target_port))
                message = str(initial_clock)
                s.sendall(message.encode())
        except Exception as e:
            self.fail(f"Failed to send message: {e}")

        # Allow time for VM2 to process the message
        time.sleep(3)

        # Restore VM2’s original running state
        self.vm2.running = original_processing

        # Assert that VM2's logical clock increased
        self.assertGreater(self.vm2.logical_clock, initial_vm2_clock, 
                        "VM2's logical clock should increase upon receiving a message")


    def test_logical_clock_updates(self):
        """Test that logical clock updates correctly on message receive"""
        initial_clock_vm2 = self.vm2.logical_clock
        self.vm1.send_message(1)

        time.sleep(2)  # Wait for processing

        self.assertGreater(self.vm2.logical_clock, initial_clock_vm2, "VM2's logical clock should update upon receiving a message")

    def test_internal_event_logging(self):
        """Test if VM logs an internal event correctly"""
        log_entry = "Internal event"

        # Trigger an internal event
        self.vm1.log_event("Internal")

        time.sleep(1)

        with open(f'logs/sim{self.simulation_id}_vm0_log.txt', 'r') as f:
            logs = f.read()
        
        self.assertIn(log_entry, logs, "Log file should contain an internal event entry")

    def tearDown(self):
        """Shut down VMs and clean up"""
        self.vm1.stop()
        self.vm2.stop()

        # Ensure sockets are closed before restarting tests
        time.sleep(2)

        self.vm1_thread.join()
        self.vm2_thread.join()


if __name__ == "__main__":
    unittest.main()
