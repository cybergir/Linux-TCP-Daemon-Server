import os
import pytest
import socket
import threading
import time
import concurrent.futures
from typing import Generator, Tuple
import asyncio
from server import AsyncTCPServer, ServerConfig, FileError


@pytest.fixture
def mock_config(tmp_path) -> Generator[str, None, None]:
    # Creates a mock configuration file for testing.
    config_data = f"""
[SERVER]
linuxpath = {tmp_path / "test_file.txt"}
REREAD_ON_QUERY = True
use_ssl = False
"""
    config_file = tmp_path / "test_config.ini"

    with open(config_file, "w") as file:
        file.write(config_data)

    yield str(config_file)


@pytest.fixture
def mock_file(tmp_path) -> Generator[str, None, None]:
    # Creates a mock data file dynamically for testing.
    file_content = "line1\nline2\nexact_line\n"
    test_file_path = tmp_path / "test_file.txt"

    with open(test_file_path, "w") as file:
        file.write(file_content)

    yield str(test_file_path)


def start_test_server(
        config_file: str
) -> Tuple[AsyncTCPServer, threading.Thread]:
    config = ServerConfig(config_file)
    server = AsyncTCPServer(
        host="127.0.0.1",
        port=44445,
        file_path=config.file_path,
        reread_on_query=config.reread_on_query,
        use_ssl=config.use_ssl,
    )

    async def run_server():
        await server.start()

    server_thread = threading.Thread(target=lambda: asyncio.run(run_server()))
    server_thread.daemon = True
    server_thread.start()
    time.sleep(1)  # Allow time for server startup
    return server, server_thread


def is_server_ready(host: str, port: int) -> bool:
    # Checks if the server is ready to accept connections.
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except Exception:
        return False


def test_server_startup(mock_config: str) -> None:
    # Tests that the server starts up correctly using a mock configuration.
    server, server_thread = start_test_server(mock_config)
    try:
        assert server.server is not None, "Server failed to start properly."
    finally:
        asyncio.run(server.shutdown())
        server_thread.join()


def test_load_file_content_success(mock_config: str, mock_file: str) -> None:
    # Tests successful loading of file content into the server.
    config = ServerConfig(mock_config)
    server = AsyncTCPServer(
        host="127.0.0.1",
        port=44445,
        file_path=config.file_path,
        reread_on_query=config.reread_on_query,
        use_ssl=config.use_ssl,
    )
    asyncio.run(server.load_file_content())
    assert server.file_content is not None, "File content should not be None"
    assert len(server.file_content) > 0, "File content should not be empty"
    assert "line1" in server.file_content[0], "File content is incorrect"


def test_load_file_content_missing_file(mock_config: str) -> None:
    # Tests behavior when attempting to load a non-existent file.
    config = ServerConfig(mock_config)

    file_path = os.environ.get("LINUX_PATH")
    assert config.file_path is not None, \
        "LINUX_PATH environment variable must be set for this test."

    server = AsyncTCPServer(
        host="127.0.0.1",
        port=44445,
        file_path=file_path,
        reread_on_query=True,
        use_ssl=False,
    )
    with pytest.raises(FileError, match=r"File does not exist: .*"):
        asyncio.run(server.load_file_content())


def test_load_file_content_empty_file(mock_config: str, tmp_path) -> None:
    # Tests behavior when attempting to load an empty file.
    empty_file_path = tmp_path / "empty_file.txt"
    open(empty_file_path, "w").close()

    config = ServerConfig(mock_config)
    server = AsyncTCPServer(
        host="127.0.0.1",
        port=44445,
        file_path=str(empty_file_path),
        reread_on_query=True,
        use_ssl=False,
    )
    try:
        asyncio.run(server.load_file_content())
    except FileError as e:
        assert False, f"Unexpected error: {e}"


def test_load_file_content_permission_error(
        mock_config: str, tmp_path
) -> None:
    # Tests behavior when attempting to load a file without permission.
    restricted_file_path = tmp_path / "restricted_file.txt"
    try:
        with open(restricted_file_path, "w") as file:
            file.write("Sample content for testing.")
        os.chmod(restricted_file_path, 0o000)  # Make the file read-only

        config = ServerConfig(mock_config)
        server = AsyncTCPServer(
            host="127.0.0.1",
            port=44445,
            file_path=str(restricted_file_path),
            reread_on_query=True,
            use_ssl=False,
        )
        with pytest.raises(FileError, match=r"Permission denied: .*"):
            asyncio.run(server.load_file_content())
    finally:
        os.chmod(restricted_file_path, 0o644)


def test_concurrent_file_access(mock_config: str, mock_file: str) -> None:
    # Tests concurrent access to loading of a single data file.
    config = ServerConfig(mock_config)
    server = AsyncTCPServer(
        host="127.0.0.1",
        port=44445,
        file_path=config.file_path,
        reread_on_query=config.reread_on_query,
        use_ssl=config.use_ssl,
    )

    async def load_content():
        start_time = time.time()  # Start timing
        await server.load_file_content()
        return time.time() - start_time  # Return elapsed time

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(
                lambda: asyncio.run(load_content())
            ) for _ in range(5)
        ]
        total_time = sum(
            future.result()
            for future in concurrent.futures.as_completed(futures)
        )

        avg_time = total_time / len(futures)
        print(
            f"Average load time for concurrent access: "
            f"{avg_time:.4f} seconds"
        )


def test_server_connection(mock_config: str) -> None:
    # Tests that we can connect to a running instance of our TCP Server.
    server, server_thread = start_test_server(mock_config)
    try:
        ready = is_server_ready("localhost", 44445)
        assert ready, "Server is not ready for connections."
    finally:
        asyncio.run(server.shutdown())
        server_thread.join()
