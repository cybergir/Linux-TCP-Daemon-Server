import concurrent.futures
import time
import socket
import threading
import ssl
import os
import pytest
from server import TCPServer, ServerConfig
from typing import Generator, Tuple


@pytest.fixture
def mock_config() -> Generator[str, None, None]:
    # Creates a mock configuration file for testing.
    config_data = """
[SERVER]
linuxpath = ${LINUX_PATH}
REREAD_ON_QUERY = True
use_ssl = True
"""
    config_file = os.environ.get("TEST_CONFIG_PATH", "test_config.ini")

    with open(config_file, "w") as file:
        file.write(config_data)  # Writes the config data to the file

    yield config_file  # Provides the config file path to the test
    os.remove(config_file)  # Clean up the created file after the test


def start_test_server(config_file: str) -> Tuple[TCPServer, threading.Thread]:
    # Starts the test server in a separate thread.
    config = ServerConfig(config_file)  # Loads the server config
    server = TCPServer(config)  # Initializes the TCPServer

    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True  # Sets the thread as a daemon
    server_thread.start()

    # Waits until the server is ready before returning
    if not is_server_ready("localhost", 44445):
        raise RuntimeError("Server did not start in time.")

    return server, server_thread  # Returns the server and its thread


def is_server_ready(host: str, port: int, timeout: float = 2.0) -> bool:
    # Checks if the server is ready to accept connections.
    for _ in range(int(timeout / 0.5)):
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True  # Returns True if connection is successful
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.5)  # Waits before retrying
    return False


def test_concurrency(mock_config: str) -> None:
    # Tests the server's ability to handle concurrent requests.
    server, server_thread = start_test_server(mock_config)

    query = "exact_line"  # Defines the query to be sent

    def client_request(query: str):
        # Sends a client request to the server.
        with socket.create_connection(("localhost", 44445)) as client_socket:
            client_socket.sendall(query.encode("utf-8"))  # Sends the query
            return client_socket.recv(1024).decode("utf-8").strip()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Creates a thread pool to handle concurrent requests
            futures = [
                executor.submit(client_request, query) for _ in range(10)
            ]  # Submits multiple requests
            responses = [
                future.result()
                for future in concurrent.futures.as_completed(futures)
            ]

        assert all(
            response == f"Query '{query}' EXISTS" for response in responses
        )

    finally:
        server.shutdown()  # Shuts down the server
        # Waits for the server thread to complete
        server_thread.join()


def test_performance_under_load(mock_config: str) -> None:
    # Tests the server's performance under load using SSL.
    server, server_thread = start_test_server(mock_config)

    query = "exact_line"  # Defines the query

    try:
        context = ssl.create_default_context()

        with socket.create_connection(("localhost", 44445)) as sock:
            with context.wrap_socket(
                sock, server_hostname="localhost"
            ) as ssl_socket:  # Wraps the socket with SSL
                ssl_socket.sendall(query.encode("utf-8"))
                response = ssl_socket.recv(1024).decode("utf-8").strip()
                assert response == f"Query '{query}' EXISTS"
                print("SSL connection and query response successful!")

    finally:
        server.shutdown()
        server_thread.join()
