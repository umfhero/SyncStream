"""
Unit tests for TransferProtocol
"""

from core.transfer_protocol import TransferProtocol, Transfer
import unittest
import tempfile
import time
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestTransferProtocol(unittest.TestCase):
    """Test cases for TransferProtocol"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory
        self.test_dir = tempfile.mkdtemp()

        # Create test file
        self.test_file = Path(self.test_dir) / "test_file.txt"
        with open(self.test_file, 'w') as f:
            f.write("Test content " * 1000)  # ~13KB file

        # Create transfer protocol instance
        self.protocol = TransferProtocol()

        # Track callbacks
        self.callback_data = {
            'started': [],
            'progress': [],
            'completed': [],
            'errors': []
        }

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def callback_start(self, transfer):
        """Callback for transfer start"""
        self.callback_data['started'].append(transfer.transfer_id)

    def callback_progress(self, transfer):
        """Callback for transfer progress"""
        self.callback_data['progress'].append({
            'id': transfer.transfer_id,
            'progress': transfer.progress_percent
        })

    def callback_complete(self, transfer):
        """Callback for transfer complete"""
        self.callback_data['completed'].append(transfer.transfer_id)

    def callback_error(self, transfer, error_msg):
        """Callback for transfer error"""
        self.callback_data['errors'].append({
            'id': transfer.transfer_id,
            'error': error_msg
        })

    def test_create_transfer(self):
        """Test creating a transfer"""
        transfer = self.protocol.create_transfer(
            file_path=str(self.test_file),
            sender="Alice",
            receiver="Bob"
        )

        self.assertIsNotNone(transfer)
        self.assertEqual(transfer.filename, "test_file.txt")
        self.assertEqual(transfer.sender, "Alice")
        self.assertEqual(transfer.receiver, "Bob")
        self.assertGreater(transfer.file_size, 0)
        self.assertEqual(transfer.status, "pending")

    def test_transfer_id_generation(self):
        """Test unique transfer ID generation"""
        transfer1 = self.protocol.create_transfer(
            str(self.test_file), "A", "B")
        transfer2 = self.protocol.create_transfer(
            str(self.test_file), "A", "B")

        self.assertNotEqual(transfer1.transfer_id, transfer2.transfer_id)

    def test_transfer_progress_calculation(self):
        """Test progress percentage calculation"""
        transfer = Transfer(
            transfer_id="test123",
            file_path=str(self.test_file),
            filename="test.txt",
            file_size=1000,
            sender="Alice",
            receiver="Bob"
        )

        transfer.bytes_transferred = 0
        self.assertEqual(transfer.progress_percent, 0.0)

        transfer.bytes_transferred = 500
        self.assertEqual(transfer.progress_percent, 50.0)

        transfer.bytes_transferred = 1000
        self.assertEqual(transfer.progress_percent, 100.0)

    def test_transfer_speed_calculation(self):
        """Test transfer speed calculation"""
        transfer = Transfer(
            transfer_id="test123",
            file_path=str(self.test_file),
            filename="test.txt",
            file_size=10000,
            sender="Alice",
            receiver="Bob"
        )

        # Initially no speed (no start time)
        self.assertEqual(transfer.transfer_speed, 0)

        # Set start time and transferred bytes
        transfer.start_time = time.time() - 1  # 1 second ago
        transfer.bytes_transferred = 1000

        # Speed should be ~1000 bytes/sec
        self.assertGreater(transfer.transfer_speed, 900)
        self.assertLess(transfer.transfer_speed, 1100)

    def test_transfer_eta_calculation(self):
        """Test ETA calculation"""
        transfer = Transfer(
            transfer_id="test123",
            file_path=str(self.test_file),
            filename="test.txt",
            file_size=10000,
            sender="Alice",
            receiver="Bob"
        )

        # Set start time and progress
        transfer.start_time = time.time() - 1
        transfer.bytes_transferred = 5000  # 50% done

        # ETA should be approximately 1 second (50% remaining at current speed)
        eta = transfer.eta_seconds
        self.assertGreater(eta, 0.5)
        self.assertLess(eta, 1.5)

    def test_register_callbacks(self):
        """Test registering callbacks"""
        self.protocol.on_transfer_start = self.callback_start
        self.protocol.on_transfer_progress = self.callback_progress
        self.protocol.on_transfer_complete = self.callback_complete
        self.protocol.on_transfer_error = self.callback_error

        # Create a transfer
        transfer = self.protocol.create_transfer(str(self.test_file), "A", "B")

        # Manually trigger start callback (normally done by send/receive)
        if self.protocol.on_transfer_start:
            self.protocol.on_transfer_start(transfer)

        self.assertIn(transfer.transfer_id, self.callback_data['started'])

    def test_transfer_status_transitions(self):
        """Test transfer status transitions"""
        transfer = self.protocol.create_transfer(str(self.test_file), "A", "B")

        self.assertEqual(transfer.status, "pending")

        transfer.status = "in_progress"
        self.assertEqual(transfer.status, "in_progress")

        transfer.status = "completed"
        self.assertEqual(transfer.status, "completed")

    def test_transfer_with_nonexistent_file(self):
        """Test creating transfer with non-existent file"""
        transfer = self.protocol.create_transfer(
            "/nonexistent/file.txt",
            "Alice",
            "Bob"
        )

        # Should handle gracefully (return None or raise exception)
        # Depending on implementation
        if transfer is not None:
            self.assertEqual(transfer.file_size, 0)

    def test_multiple_simultaneous_transfers(self):
        """Test managing multiple transfers"""
        # Create multiple test files
        files = []
        for i in range(3):
            f = Path(self.test_dir) / f"file{i}.txt"
            with open(f, 'w') as fh:
                fh.write(f"Content {i}")
            files.append(f)

        # Create transfers
        transfers = []
        for f in files:
            t = self.protocol.create_transfer(str(f), "Alice", "Bob")
            if t:
                transfers.append(t)

        # Should be able to track all transfers
        self.assertEqual(len(transfers), 3)

        # All should have unique IDs
        ids = [t.transfer_id for t in transfers]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == '__main__':
    unittest.main()
