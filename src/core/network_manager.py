"""
SyncStream - Network Manager

Handles TCP socket connections, auto-reconnect logic, and network events.
"""

import socket
import threading
import time
from enum import Enum
from typing import Callable, Optional, Dict, Any
from datetime import datetime, timedelta
from .transfer_protocol import TransferProtocol


class ConnectionState(Enum):
    """Connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"


class NetworkManager:
    """Manages network connections and communication"""

    def __init__(self, port: int = 12345):
        """
        Initialize network manager

        Args:
            port: Port number for connections
        """
        self.port = port
        self.state = ConnectionState.DISCONNECTED

        # Sockets
        self.server_socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        self.peer_socket: Optional[socket.socket] = None

        # Connection info
        self.peer_ip: Optional[str] = None
        self.peer_name: Optional[str] = None
        self.my_name: Optional[str] = None

        # Auto-reconnect settings
        self.auto_reconnect_enabled = True
        self.reconnect_timeout = 180  # 3 minutes
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        self.last_disconnect_time: Optional[datetime] = None

        # Transfer protocol
        self.transfer_protocol = TransferProtocol()

        # Threading
        self._running = False
        self._server_thread: Optional[threading.Thread] = None
        self._receive_thread: Optional[threading.Thread] = None
        self._reconnect_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Callbacks
        self.callbacks: Dict[str, list] = {
            'on_connected': [],
            'on_disconnected': [],
            'on_connecting': [],
            'on_data_received': [],
            'on_connection_error': []
        }

        # Start server
        self.start_server()

    def register_callback(self, event: str, callback: Callable) -> None:
        """
        Register a callback for network events

        Args:
            event: Event name (on_connected, on_disconnected, etc.)
            callback: Function to call when event occurs
        """
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _trigger_callback(self, event: str, *args, **kwargs) -> None:
        """Trigger all callbacks for an event"""
        for callback in self.callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f"❌ Error in {event} callback: {e}")

    def start_server(self) -> None:
        """Start the TCP server to listen for incoming connections"""
        if self._server_thread and self._server_thread.is_alive():
            return

        self._running = True
        self._server_thread = threading.Thread(
            target=self._server_loop, daemon=True)
        self._server_thread.start()
        print(f"🌐 Server started on port {self.port}")

    def _server_loop(self) -> None:
        """Server loop to accept incoming connections"""
        try:
            self.server_socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("0.0.0.0", self.port))
            self.server_socket.listen(5)
            # Timeout for checking _running flag
            self.server_socket.settimeout(1.0)

            print(f"👂 Listening for connections on 0.0.0.0:{self.port}")

            while self._running:
                try:
                    client_socket, addr = self.server_socket.accept()

                    with self._lock:
                        if self.peer_socket is not None:
                            # Already connected, reject new connection
                            client_socket.close()
                            continue

                        self.peer_socket = client_socket
                        self.peer_ip = addr[0]

                    self._set_state(ConnectionState.CONNECTED)
                    print(f"✅ Accepted connection from {addr[0]}")

                    # Start receiving data
                    self._start_receive_thread()

                except socket.timeout:
                    continue
                except Exception as e:
                    if self._running:
                        print(f"❌ Server accept error: {e}")

        except Exception as e:
            print(f"❌ Server setup error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def connect(self, peer_ip: str, peer_name: str, my_name: str) -> bool:
        """
        Connect to a peer as client

        Args:
            peer_ip: IP address of peer
            peer_name: Name of peer
            my_name: Your name

        Returns:
            True if connection initiated
        """
        if self.state == ConnectionState.CONNECTED:
            print("⚠️  Already connected")
            return False

        self.peer_ip = peer_ip
        self.peer_name = peer_name
        self.my_name = my_name

        # Start connection in background
        threading.Thread(target=self._connect_background, daemon=True).start()
        return True

    def _connect_background(self) -> None:
        """Background thread for connecting"""
        self._set_state(ConnectionState.CONNECTING)

        try:
            self.client_socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(10.0)  # 10 second timeout

            print(f"🔄 Connecting to {self.peer_ip}:{self.port}...")
            self.client_socket.connect((self.peer_ip, self.port))

            with self._lock:
                self.peer_socket = self.client_socket

            self._set_state(ConnectionState.CONNECTED)
            print(f"✅ Connected to {self.peer_ip}")

            # Start receiving data
            self._start_receive_thread()

        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self._set_state(ConnectionState.DISCONNECTED)
            self._trigger_callback('on_connection_error', str(e))

            # Start auto-reconnect if enabled
            if self.auto_reconnect_enabled:
                self._start_reconnect_thread()

    def _start_receive_thread(self) -> None:
        """Start the receive thread"""
        if self._receive_thread and self._receive_thread.is_alive():
            return

        self._receive_thread = threading.Thread(
            target=self._receive_loop, daemon=True)
        self._receive_thread.start()

    def _receive_loop(self) -> None:
        """Loop to receive data from peer"""
        buffer = b""

        try:
            while self._running and self.state == ConnectionState.CONNECTED:
                try:
                    data = self.peer_socket.recv(8192)

                    if not data:
                        # Connection closed
                        print("📡 Connection closed by peer")
                        self.disconnect()
                        break

                    buffer += data

                    # Process complete messages (ending with \n)
                    while b'\n' in buffer:
                        message, buffer = buffer.split(b'\n', 1)
                        try:
                            decoded = message.decode('utf-8')
                            self._trigger_callback('on_data_received', decoded)
                        except Exception as e:
                            print(f"❌ Error decoding message: {e}")

                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"❌ Receive error: {e}")
                    self.disconnect()
                    break

        except Exception as e:
            print(f"❌ Receive loop error: {e}")
            self.disconnect()

    def send_data(self, data: str) -> bool:
        """
        Send data to connected peer

        Args:
            data: String data to send

        Returns:
            True if sent successfully
        """
        if self.state != ConnectionState.CONNECTED or not self.peer_socket:
            print("⚠️  Not connected, cannot send")
            return False

        try:
            message = (data + "\n").encode('utf-8')
            self.peer_socket.sendall(message)
            return True
        except Exception as e:
            print(f"❌ Send error: {e}")
            self.disconnect()
            return False

    def disconnect(self) -> None:
        """Disconnect from current peer"""
        with self._lock:
            if self.peer_socket:
                try:
                    self.peer_socket.close()
                except:
                    pass
                self.peer_socket = None

            if self.client_socket and self.client_socket != self.peer_socket:
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None

        self.last_disconnect_time = datetime.now()
        self._set_state(ConnectionState.DISCONNECTED)

        # Start auto-reconnect if enabled
        if self.auto_reconnect_enabled and self.peer_ip:
            self._start_reconnect_thread()

    def _start_reconnect_thread(self) -> None:
        """Start auto-reconnect thread"""
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return

        self._reconnect_thread = threading.Thread(
            target=self._reconnect_loop, daemon=True)
        self._reconnect_thread.start()

    def _reconnect_loop(self) -> None:
        """Auto-reconnect loop with timeout"""
        print("🔄 Starting auto-reconnect...")
        self.reconnect_attempts = 0
        start_time = datetime.now()

        while self._running and self.state == ConnectionState.DISCONNECTED:
            # Check timeout
            if (datetime.now() - start_time).total_seconds() > self.reconnect_timeout:
                print("⏱️  Auto-reconnect timeout reached")
                self._trigger_callback(
                    'on_connection_error', "Auto-reconnect timeout")
                break

            # Check max attempts
            if self.reconnect_attempts >= self.max_reconnect_attempts:
                print(
                    f"⚠️  Max reconnect attempts ({self.max_reconnect_attempts}) reached")
                # Wait before trying again
                time.sleep(30)
                self.reconnect_attempts = 0
                continue

            self.reconnect_attempts += 1
            print(
                f"🔄 Reconnect attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")

            # Try to connect
            if self.peer_ip:
                self._connect_background()

                # Wait before next attempt
                if self.state != ConnectionState.CONNECTED:
                    time.sleep(10)  # Wait 10 seconds between attempts
            else:
                break

    def try_reconnect(self) -> None:
        """Manually trigger reconnection attempt"""
        if self.state == ConnectionState.DISCONNECTED and self.peer_ip:
            print("🔄 Manual reconnect triggered")
            self.reconnect_attempts = 0
            self._start_reconnect_thread()

    def _set_state(self, new_state: ConnectionState) -> None:
        """Set connection state and trigger callbacks"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            print(f"📊 State: {old_state.value} → {new_state.value}")

            # Trigger appropriate callback
            if new_state == ConnectionState.CONNECTED:
                self._trigger_callback('on_connected', self.peer_ip)
            elif new_state == ConnectionState.DISCONNECTED:
                self._trigger_callback('on_disconnected')
            elif new_state == ConnectionState.CONNECTING:
                self._trigger_callback('on_connecting')

    def shutdown(self) -> None:
        """Shutdown network manager"""
        print("🛑 Shutting down network manager...")
        self._running = False
        self.auto_reconnect_enabled = False
        self.disconnect()

        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass


if __name__ == "__main__":
    # Test the network manager
    print("🧪 Testing NetworkManager...")

    manager = NetworkManager()

    def on_connected(peer_ip):
        print(f"✅ Connected to {peer_ip}")

    def on_disconnected():
        print("❌ Disconnected")

    manager.register_callback('on_connected', on_connected)
    manager.register_callback('on_disconnected', on_disconnected)

    print(f"📊 Current state: {manager.state.value}")

    # Keep alive
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        manager.shutdown()
