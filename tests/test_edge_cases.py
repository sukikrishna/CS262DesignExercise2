import unittest
from unittest.mock import patch, MagicMock
import threading
import time
import socket
import os
import sys

# Add 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Now import VirtualMachine
from virtual_machines import VirtualMachine

class TestVirtualMachine(unittest.TestCase):

    def setUp(self):
        """Initialize a test VirtualMachine instance."""
        self.simulation_id = 1
        self.vm = VirtualMachine(vm_id=0, peers=[1, 2], simulation_id=self.simulation_id)

    def tearDown(self):
        """Clean up after each test."""
        self.vm.stop()
        self.vm.log_file.close()
        if os.path.exists(f'logs/sim{self.simulation_id}_vm{self.vm.vm_id}_log.txt'):
            os.remove(f'logs/sim{self.simulation_id}_vm{self.vm.vm_id}_log.txt')

    @patch('socket.socket')
    def test_send_message_fail(self, mock_socket):
        """Test sending a message when the recipient VM is unavailable."""
        mock_socket.return_value.connect.side_effect = ConnectionRefusedError

        self.vm.send_message(5)  # VM 5 does not exist
        mock_socket.assert_called()

    def test_message_queue_handling(self):
        """Test messages being processed from network queue to message queue."""
        self.vm.network_queue.put(5)
        self.vm.network_queue.put(10)

        while not self.vm.network_queue.empty():
            self.vm.message_queue.put(self.vm.network_queue.get_nowait())

        self.assertEqual(self.vm.message_queue.get_nowait(), 5)
        self.assertEqual(self.vm.message_queue.get_nowait(), 10)

    def test_log_event(self):
        """Test event logging."""
        self.vm.log_event("Internal")
        with open(f'logs/sim{self.simulation_id}_vm{self.vm.vm_id}_log.txt', 'r') as f:
            log_contents = f.read()
        self.assertIn("Internal event", log_contents)

    def test_logical_clock_update(self):
        """Test logical clock updates correctly upon receiving a message."""
        self.vm.logical_clock = 5
        self.vm.network_queue.put(7)  # Received message with logical time 7

        while not self.vm.network_queue.empty():
            received_time = self.vm.network_queue.get_nowait()
            self.vm.logical_clock = max(self.vm.logical_clock, received_time) + 1

        self.assertEqual(self.vm.logical_clock, 8)  # max(5,7) + 1 = 8

    def test_invalid_message(self):
        """Test handling of invalid messages."""
        self.vm.network_queue.put("INVALID")  # Non-integer message
        with self.assertRaises(ValueError):
            received_time = int(self.vm.network_queue.get_nowait())

    def test_empty_queue_handling(self):
        """Test handling an empty message queue."""
        self.assertTrue(self.vm.network_queue.empty())
        self.assertTrue(self.vm.message_queue.empty())

    def test_high_clock_rate(self):
        """Test VM with high clock rate processes events quickly."""
        self.vm.clock_rate = 6
        start_time = time.time()
        self.vm.logical_clock += 1  # Simulating an internal event
        elapsed_time = time.time() - start_time
        self.assertLessEqual(elapsed_time, 1/6)

    def test_multiple_vms(self):
        """Test that multiple VMs run concurrently without errors."""
        vm1 = VirtualMachine(1, [0, 2], 1)
        vm2 = VirtualMachine(2, [0, 1], 1)

        thread1 = threading.Thread(target=vm1.run)
        thread2 = threading.Thread(target=vm2.run)

        thread1.start()
        thread2.start()

        time.sleep(2)  # Let them run briefly

        vm1.stop()
        vm2.stop()

        thread1.join()
        thread2.join()

        self.assertFalse(vm1.running)
        self.assertFalse(vm2.running)

    def test_stop_vm(self):
        """Test stopping the virtual machine."""
        self.vm.stop()
        self.assertFalse(self.vm.running)

    def test_abrupt_shutdown(self):
        """Test stopping the VM abruptly while processing messages."""
        self.vm.network_queue.put(10)
        self.vm.stop()
        self.assertFalse(self.vm.running)

    def test_no_peers(self):
        """Test VM behavior with no peers (edge case)."""
        vm_no_peers = VirtualMachine(3, [], self.simulation_id)
        self.assertEqual(vm_no_peers.peers, [])
        vm_no_peers.stop()

if __name__ == '__main__':
    unittest.main()
