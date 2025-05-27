import concurrent.futures
import socket
import pytest
from server import TCPServer, ServerConfig
import threading
import os


def is_server_ready(host: str, port: int) -> bool:
    # Checks if the server is ready by attempting to create a connection.
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except Exception:
        return False  # Return False if the connection fails


@pytest.fixture
def mock_config():
    # Creates a mock configuration file for testing purposes.
    config_data = """
    [SERVER]
    linuxpath = ${LINUX_PATH}
    REREAD_ON_QUERY = True
    use_ssl = True
    """
    config_file = "test_config.ini"
    with open(config_file, "w") as file:
        file.write(config_data)
    yield config_file
    if os.path.exists(config_file):
        os.remove(config_file)


def start_test_server(config_file):
    config = ServerConfig(config_file)
    server = TCPServer(config)
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()

    # Wait until the server is ready to accept connections
    if not is_server_ready("localhost", 44445):
        raise RuntimeError("Server did not start in time.")

    return server, server_thread


def client_request(host, port, query):
    # Sends a query to the server and returns the response.
    with socket.create_connection((host, port)) as client_socket:
        client_socket.sendall(query.encode("utf-8"))
        return client_socket.recv(1024).decode("utf-8").strip()


def test_concurrent_requests_handling(mock_config):
    # Tests handling of concurrent requests to the server.
    server, server_thread = start_test_server(mock_config)
    host = os.getenv("TEST_HOST", "localhost")
    port = int(os.getenv("TEST_PORT", "44445"))
    query = "exact_line"  # Define the query to be sent

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Create a thread pool for concurrent execution of client requests
            futures = [
                executor.submit(
                    client_request, host, port, query
                ) for _ in range(10)
            ]

            responses = [
                future.result()
                for future in concurrent.futures.as_completed(futures)
            ]

        assert all(
            response == f"Query '{query}' EXISTS"
            for response in responses
        )

    finally:
        server.shutdown()
        server_thread.join()
