import socket
import time


def is_server_ready(host: str, port: int, timeout: int = 5) -> bool:
    # Checks if the server is ready to accept connections.
    for _ in range(timeout):
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(1)  # Wait for 1 second before retrying
    return False
