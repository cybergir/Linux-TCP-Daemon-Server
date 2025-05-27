import pytest
import socket
import ssl
import os
import time


def is_server_ready(host: str, port: int, timeout: float = 2.0) -> bool:
    # Checks if the server is ready by attempting a connection.
    for _ in range(int(timeout / 0.5)):
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.5)
    return False


@pytest.fixture
def server_host_and_port() -> tuple[str, int]:
    # Provides the server's host and port from environment variables.
    host = os.environ.get("TEST_SERVER_HOST", "localhost")
    port = int(os.environ.get("TEST_SERVER_PORT", 44445))
    return host, port


@pytest.fixture
def ssl_certificate_path() -> str:
    # Provides the path to the SSL certificate.
    return os.environ.get("TEST_SSL_CERT_PATH", "cert.pem")


def test_server_connection(server_host_and_port) -> None:
    # Tests basic server connection.
    host, port = server_host_and_port
    assert is_server_ready(host, port), "Server not ready for connection tests"


def test_ssl_connection(server_host_and_port, ssl_certificate_path) -> None:
    # Tests SSL connection to the server.
    host, port = server_host_and_port
    assert is_server_ready(
        host, port
    ), "Server not ready for SSL connection tests"

    context = ssl.create_default_context()
    context.load_verify_locations(ssl_certificate_path)

    with socket.create_connection((host, port)) as raw_socket:
        with context.wrap_socket(
            raw_socket, server_hostname=host
        ) as server_socket:  # Wrap the socket with SSL
            assert isinstance(server_socket, ssl.SSLSocket)
