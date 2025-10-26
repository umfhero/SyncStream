"""
SyncStream - File Transfer Protocol

Handles chunked file transfers with progress tracking, queuing, and retry logic.
"""

import json
import struct
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Optional, List
import hashlib
import socket


class TransferState(Enum):
    """Transfer state"""
    QUEUED = "queued"
    SENDING = "sending"
    RECEIVING = "receiving"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(Enum):
    """Protocol message types"""
    FILE_OFFER = "file_offer"          # Sender offers a file
    FILE_ACCEPT = "file_accept"        # Receiver accepts
    FILE_REJECT = "file_reject"        # Receiver rejects
    FILE_CHUNK = "file_chunk"          # File data chunk
    FILE_COMPLETE = "file_complete"    # Transfer complete
    FILE_ERROR = "file_error"          # Transfer error
    TRANSFER_PROGRESS = "progress"     # Progress update


@dataclass
class Transfer:
    """Represents a file transfer"""
    transfer_id: str
    filename: str
    file_path: str
    file_size: int
    file_hash: str
    chunk_size: int = 65536  # 64KB chunks
    sender: str = ""
    receiver: str = ""
    state: TransferState = TransferState.QUEUED
    bytes_transferred: int = 0
    chunks_total: int = 0
    chunks_sent: int = 0
    retry_count: int = 0
    max_retries: int = 3
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: str = ""

    def __post_init__(self):
        """Calculate chunks after initialization"""
        if self.chunks_total == 0:
            self.chunks_total = (
                self.file_size + self.chunk_size - 1) // self.chunk_size

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage"""
        if self.file_size == 0:
            return 100.0
        return (self.bytes_transferred / self.file_size) * 100

    @property
    def transfer_speed(self) -> float:
        """Calculate transfer speed in bytes/sec"""
        if not self.start_time or self.bytes_transferred == 0:
            return 0.0
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0.0
        return self.bytes_transferred / elapsed

    @property
    def eta_seconds(self) -> float:
        """Estimate remaining time in seconds"""
        speed = self.transfer_speed
        if speed == 0:
            return 0.0
        remaining = self.file_size - self.bytes_transferred
        return remaining / speed


class TransferProtocol:
    """
    File transfer protocol handler

    Manages file transfers with chunking, progress tracking, and retry logic.
    """

    def __init__(self, chunk_size: int = 65536):
        """
        Initialize transfer protocol

        Args:
            chunk_size: Size of each chunk in bytes (default 64KB)
        """
        self.chunk_size = chunk_size
        self.transfers: Dict[str, Transfer] = {}
        self.transfer_queue: List[str] = []
        self.active_transfers: Dict[str, threading.Thread] = {}
        self.callbacks: Dict[str, List[Callable]] = {
            'on_transfer_start': [],
            'on_transfer_progress': [],
            'on_transfer_complete': [],
            'on_transfer_error': [],
            'on_file_offer': [],
        }
        self._lock = threading.Lock()

    def register_callback(self, event: str, callback: Callable):
        """Register a callback for an event"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _trigger_callback(self, event: str, *args, **kwargs):
        """Trigger all callbacks for an event"""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"⚠️  Callback error ({event}): {e}")

    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(self.chunk_size)
                    if not data:
                        break
                    sha256.update(data)
            return sha256.hexdigest()
        except Exception as e:
            print(f"⚠️  Failed to hash file: {e}")
            return ""

    def create_transfer(self, file_path: str, sender: str, receiver: str) -> Optional[Transfer]:
        """
        Create a new transfer

        Args:
            file_path: Path to the file to transfer
            sender: Sender profile name
            receiver: Receiver profile name

        Returns:
            Transfer object or None if failed
        """
        try:
            path = Path(file_path)
            if not path.exists():
                print(f"⚠️  File not found: {file_path}")
                return None

            file_size = path.stat().st_size
            file_hash = self.calculate_file_hash(file_path)
            transfer_id = hashlib.md5(
                f"{file_path}{time.time()}".encode()).hexdigest()

            transfer = Transfer(
                transfer_id=transfer_id,
                filename=path.name,
                file_path=file_path,
                file_size=file_size,
                file_hash=file_hash,
                chunk_size=self.chunk_size,
                sender=sender,
                receiver=receiver
            )

            with self._lock:
                self.transfers[transfer_id] = transfer
                self.transfer_queue.append(transfer_id)

            return transfer

        except Exception as e:
            print(f"⚠️  Failed to create transfer: {e}")
            return None

    def send_file(self, sock: socket.socket, transfer_id: str) -> bool:
        """
        Send a file over socket

        Args:
            sock: Socket connection
            transfer_id: Transfer ID

        Returns:
            True if successful
        """
        transfer = self.transfers.get(transfer_id)
        if not transfer:
            return False

        try:
            # Send file offer
            offer = self._create_message(MessageType.FILE_OFFER, {
                'transfer_id': transfer_id,
                'filename': transfer.filename,
                'file_size': transfer.file_size,
                'file_hash': transfer.file_hash,
                'sender': transfer.sender
            })
            self._send_message(sock, offer)

            # Wait for acceptance (simplified - should have timeout)
            # In production, this would be handled by receive loop

            # Update state
            transfer.state = TransferState.SENDING
            transfer.start_time = time.time()
            self._trigger_callback('on_transfer_start', transfer)

            # Send file in chunks
            with open(transfer.file_path, 'rb') as f:
                chunk_num = 0
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break

                    # Send chunk
                    chunk_msg = self._create_message(MessageType.FILE_CHUNK, {
                        'transfer_id': transfer_id,
                        'chunk_num': chunk_num,
                        'chunk_data': chunk.hex()  # Convert to hex for JSON
                    })
                    self._send_message(sock, chunk_msg)

                    # Update progress
                    transfer.bytes_transferred += len(chunk)
                    transfer.chunks_sent += 1
                    chunk_num += 1

                    self._trigger_callback('on_transfer_progress', transfer)

            # Send completion message
            complete_msg = self._create_message(MessageType.FILE_COMPLETE, {
                'transfer_id': transfer_id,
                'file_hash': transfer.file_hash
            })
            self._send_message(sock, complete_msg)

            # Update state
            transfer.state = TransferState.COMPLETED
            transfer.end_time = time.time()
            self._trigger_callback('on_transfer_complete', transfer)

            return True

        except Exception as e:
            transfer.state = TransferState.FAILED
            transfer.error_message = str(e)
            transfer.retry_count += 1
            self._trigger_callback('on_transfer_error', transfer, str(e))
            print(f"⚠️  Transfer failed: {e}")
            return False

    def receive_file(self, sock: socket.socket, save_dir: str):
        """
        Receive file from socket (called by network manager)

        Args:
            sock: Socket connection
            save_dir: Directory to save received files
        """
        # This will be called when FILE_OFFER is received
        # Implementation will be in network manager's receive loop
        pass

    def handle_message(self, sock: socket.socket, message: dict, save_dir: str):
        """
        Handle incoming protocol message

        Args:
            sock: Socket connection
            message: Decoded message dict
            save_dir: Directory to save files
        """
        try:
            msg_type = MessageType(message.get('type'))
            data = message.get('data', {})

            if msg_type == MessageType.FILE_OFFER:
                self._handle_file_offer(sock, data, save_dir)
            elif msg_type == MessageType.FILE_CHUNK:
                self._handle_file_chunk(data, save_dir)
            elif msg_type == MessageType.FILE_COMPLETE:
                self._handle_file_complete(data, save_dir)
            elif msg_type == MessageType.FILE_ERROR:
                self._handle_file_error(data)

        except Exception as e:
            print(f"⚠️  Message handling error: {e}")

    def _handle_file_offer(self, sock: socket.socket, data: dict, save_dir: str):
        """Handle file offer from sender"""
        transfer_id = data['transfer_id']
        filename = data['filename']
        file_size = data['file_size']
        file_hash = data['file_hash']
        sender = data['sender']

        # Create receiving transfer
        save_path = str(Path(save_dir) / filename)
        transfer = Transfer(
            transfer_id=transfer_id,
            filename=filename,
            file_path=save_path,
            file_size=file_size,
            file_hash=file_hash,
            sender=sender,
            state=TransferState.RECEIVING
        )
        transfer.start_time = time.time()

        with self._lock:
            self.transfers[transfer_id] = transfer

        # Trigger callback for UI confirmation
        self._trigger_callback('on_file_offer', transfer)

        # Auto-accept for now (should show UI prompt)
        accept_msg = self._create_message(MessageType.FILE_ACCEPT, {
            'transfer_id': transfer_id
        })
        self._send_message(sock, accept_msg)

    def _handle_file_chunk(self, data: dict, save_dir: str):
        """Handle incoming file chunk"""
        transfer_id = data['transfer_id']
        chunk_num = data['chunk_num']
        chunk_data = bytes.fromhex(data['chunk_data'])

        transfer = self.transfers.get(transfer_id)
        if not transfer:
            return

        # Write chunk to file
        try:
            mode = 'ab' if chunk_num > 0 else 'wb'
            with open(transfer.file_path, mode) as f:
                f.write(chunk_data)

            transfer.bytes_transferred += len(chunk_data)
            transfer.chunks_sent += 1
            self._trigger_callback('on_transfer_progress', transfer)

        except Exception as e:
            print(f"⚠️  Failed to write chunk: {e}")

    def _handle_file_complete(self, data: dict, save_dir: str):
        """Handle transfer completion"""
        transfer_id = data['transfer_id']
        received_hash = data['file_hash']

        transfer = self.transfers.get(transfer_id)
        if not transfer:
            return

        # Verify hash
        file_hash = self.calculate_file_hash(transfer.file_path)
        if file_hash != received_hash:
            transfer.state = TransferState.FAILED
            transfer.error_message = "Hash mismatch - file corrupted"
            self._trigger_callback('on_transfer_error',
                                   transfer, "Hash verification failed")
            return

        transfer.state = TransferState.COMPLETED
        transfer.end_time = time.time()
        self._trigger_callback('on_transfer_complete', transfer)

    def _handle_file_error(self, data: dict):
        """Handle transfer error"""
        transfer_id = data['transfer_id']
        error = data.get('error', 'Unknown error')

        transfer = self.transfers.get(transfer_id)
        if not transfer:
            return

        transfer.state = TransferState.FAILED
        transfer.error_message = error
        self._trigger_callback('on_transfer_error', transfer, error)

    def _create_message(self, msg_type: MessageType, data: dict) -> dict:
        """Create a protocol message"""
        return {
            'type': msg_type.value,
            'data': data,
            'timestamp': time.time()
        }

    def _send_message(self, sock: socket.socket, message: dict):
        """
        Send a message over socket

        Message format: 4-byte length prefix + JSON data
        """
        try:
            json_data = json.dumps(message).encode('utf-8')
            length = struct.pack('!I', len(json_data))
            sock.sendall(length + json_data)
        except Exception as e:
            print(f"⚠️  Failed to send message: {e}")
            raise

    def cancel_transfer(self, transfer_id: str):
        """Cancel a transfer"""
        transfer = self.transfers.get(transfer_id)
        if transfer:
            transfer.state = TransferState.CANCELLED
            # TODO: Notify peer

    def get_transfer(self, transfer_id: str) -> Optional[Transfer]:
        """Get transfer by ID"""
        return self.transfers.get(transfer_id)

    def get_active_transfers(self) -> List[Transfer]:
        """Get all active transfers"""
        return [t for t in self.transfers.values()
                if t.state in [TransferState.SENDING, TransferState.RECEIVING]]

    def get_queued_transfers(self) -> List[Transfer]:
        """Get all queued transfers"""
        return [t for t in self.transfers.values()
                if t.state == TransferState.QUEUED]
