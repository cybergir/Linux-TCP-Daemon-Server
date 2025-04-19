# !/home/ruby/project/myenv/bin/python
import asyncio
import ssl
import configparser
import logging
import os
import sys
import time
import signal
import re
from typing import Optional
from concurrent.futures import ProcessPoolExecutor
from loguru import logger
import cProfile
import pstats
import multiprocessing
import psutil
import atexit
import mmap


# Configure logging to output messages with timestamps and severity levels
logging.basicConfig(
    filename="service_debug.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger()


# Define custom exceptions for specific error scenarios
class ConfigError(Exception):
    pass


class FileError(Exception):
    pass


class ServerError(Exception):
    pass


# Function to search for a query in the loaded file content
def query_in_file(query: str, file_content: set) -> str:
    # Searches for a full match of the query in the file content.
    if query.strip() in file_content:
        return f"Query '{query}' EXISTS"
    return f"Query '{query}' NOT FOUND"


# Class to handle server configuration
class ServerConfig:
    def __init__(self, config_path: str) -> None:
        try:
            # Read configuration from the specified path
            (
                self.file_path,
                self.reread_on_query,
                self.use_ssl,
                self.logfile
            ) = self._read_config(config_path)
            print(f"DEBUG: file_path={self.file_path}, logfile={self.logfile}")
            # Validate the file path to ensure it exists and is a file
            self.validate_file_path(self.file_path)
        except configparser.Error as e:
            raise ConfigError(f"Failed to read configuration: {e}") from e

    def _read_config(self, config_path: str) -> tuple[str, bool, bool, str]:
        # Reads the server configuration from the file and extracts required parameters
        config = configparser.ConfigParser()
        config.read(config_path)

        # Read the log file path with a fallback to /tmp/your_server.log
        try:
            logfile = config["LOGGING"]["logfile"]
        except KeyError:
            logfile = "/tmp/server_debug.log"

        # Read other configuration values
        try:
            file_path = os.environ.get("LINUX_PATH") or config.get(
                "SERVER", "linuxpath"
            )
            return (
                file_path,
                config.getboolean("SERVER", "REREAD_ON_QUERY"),
                config.getboolean("SERVER", "use_ssl"),
                logfile,
            )
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            raise ConfigError(f"Configuration error: {e}") from e

    @staticmethod
    def validate_file_path(file_path: str) -> None:
        # Validates the configured file path.
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Configured file path does not exist: {file_path}"
            )
        if os.path.isdir(file_path):
            raise ValueError(
                f"Configured file path is a directory, not a file: {file_path}"
            )


# Class representing the asynchronous TCP server
class AsyncTCPServer:
    def __init__(
        self,
            host: str,
            port: int,
            file_path: str,
            reread_on_query: bool,
            use_ssl: bool
    ) -> None:
        self.host = host
        self.port = port
        self.file_path = file_path
        self.reread_on_query = reread_on_query
        self.use_ssl = use_ssl

        # Cache file content in a set
        self.file_content: Optional[set] = None
        self.mmapped_file = None  # Memory-mapped file
        self.server = None

        # Initialize a process pool executor for CPU-bound tasks
        self.executor = ProcessPoolExecutor(
            max_workers=multiprocessing.cpu_count(),
            mp_context=multiprocessing.get_context("spawn"),
        )

        # Initialize request counters for performance metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0

        # Initialize Rate Limiting Attributes
        self.rate_limit = 10  # Requests per second limit per IP address
        self.ip_request_count = {}  # Track request counts per IP

    async def load_file_content(self) -> None:
        # Load the file content into memory using mmap.
        if not os.path.exists(self.file_path):
            raise FileError(f"File does not exist: {self.file_path}")

        try:
            # Open the file and memory-map it
            with open(self.file_path, "r+b") as f:
                self.mmapped_file = mmap.mmap(
                        f.fileno(), 0, access=mmap.ACCESS_READ
                    )
                contents = self.mmapped_file.read().\
                    decode("utf-8").splitlines()
                # Cache file content in a set
                self.file_content = set(contents)

            if not self.file_content:
                raise FileError(f"File is empty: {self.file_path}")

        except Exception as e:
            logger.error(
                f"Failed to load file content from {self.file_path}: {e}")
            raise

    def sanitize_query(self, query: str) -> str:
        # Sanitizes the query to prevent command injection.
        sanitized_query = re.sub(r"[;&|><`$\\]", "", query)
        return sanitized_query

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:

        # Handles communication with a single client.
        pr = cProfile.Profile()
        pr.enable()

        peername = writer.get_extra_info("peername")
        client_ip = peername[0]
        logger.info(f"Client connected: {peername}")
        start_time = time.time()

        # Implement rate limiting per client IP
        if client_ip not in self.ip_request_count:
            self.ip_request_count[client_ip] = []
        now = time.time()

        # Remove timestamps older than one second from the list.
        self.ip_request_count[client_ip] = [
            t for t in self.ip_request_count[client_ip] if now - t < 1
        ]

        if len(self.ip_request_count[client_ip]) >= self.rate_limit:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            writer.write(
                "Rate limit exceeded. Please try again later.\n".
                encode("utf-8")
            )
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return

        # Record the current request timestamp for this IP address.
        self.ip_request_count[client_ip].append(now)

        # Read data from the client
        try:
            self.total_requests += 1  # Increment total request counter

            data = await reader.read(1024)
            if len(data) > 1024:
                writer.write(
                    "Request too large. Please limit your request size.\n".
                    encode("utf-8")
                )
                await writer.drain()
                return

            query = data.decode("utf-8").strip()

            # Sanitize the query input before processing it.
            sanitized_query = self.sanitize_query(query)

            if not sanitized_query:
                writer.write("Invalid query received.\n".encode("utf-8"))
                await writer.drain()
                return

            logger.info(f"Request from client {peername}: {sanitized_query}")

            start_time_measurement = time.perf_counter()

            if self.reread_on_query:
                logger.debug(
                    f"DEBUG: Rereading file content for {peername} "
                    f"as reread_on_query is True."
                )
                await self.load_file_content()
                file_set = self.file_content
            else:
                logger.debug(
                    f"DEBUG: Using cached file content for {peername} "
                    f"as reread_on_query is False."
                )
                file_set = self.file_content

            response = await asyncio.get_event_loop().run_in_executor(
                self.executor, query_in_file, sanitized_query, file_set
            )

            writer.write((response + "\n").encode("utf-8"))
            await writer.drain()

            end_time_measurement = time.perf_counter()
            response_time_measurement = \
                end_time_measurement - start_time_measurement
            logger.info(
                f"Response Time: {response_time_measurement:.4f} seconds"
            )
            # Increment successful request counter
            self.successful_requests += 1
            logger.info(f"Response sent to client: {peername}")
            logger.info(f"Connection closed for client: {peername}")

            execution_time_total = time.time() - start_time
            logger.debug(
                f"DEBUG: Client IP: {client_ip}, "
                f"Total Execution Time: {execution_time_total:.4f} seconds"
            )

        except Exception as e:
            self.failed_requests += 1  # Increment failed request counter
            logger.error(
                f"Unexpected error handling client {peername}: {e}",
                exc_info=True
            )
            # Generic error message
            writer.write(
                "An internal server error occurred.\n".encode("utf-8")
            )
            await writer.drain()

        finally:
            writer.close()
            await writer.wait_closed()
            pr.disable()
            stats = pstats.Stats(pr)
            stats.sort_stats("tottime").print_stats(10)
            memory_info = psutil.virtual_memory()
            cpu_usage = psutil.cpu_percent(interval=1)
            logger.info(f"Memory Usage: {memory_info.percent}%")
            logger.info(f"CPU Usage: {cpu_usage}%")
            logger.info(
                f"Total Requests: {self.total_requests}, "
                f"Successful Requests: {self.successful_requests}, "
                f"Failed Requests: {self.failed_requests}"
            )

    async def start(self) -> None:
        # Starts the asynchronous server.
        try:
            # Load file content at startup only when reread_on_query is False
            if not self.reread_on_query:
                logger.info("Loading file content at startup...")
                await self.load_file_content()
                logger.info("File content loaded at startup.")

            ssl_context = self.create_ssl_context() if self.use_ssl else None
            logger.info(
                "Creating SSL context..."
                if self.use_ssl
                else "Starting server without SSL."
            )
            self.server = await asyncio.start_server(
                self.handle_client,
                host=self.host,
                port=self.port,
                reuse_address=True,
                ssl=ssl_context,
            )

            addr = self.server.sockets[0].getsockname()
            logger.info(f"Server started on {addr}")
            async with self.server:
                logger.info("Server is running...")
                await self.server.serve_forever()

        except Exception as e:
            logger.critical(
                f"Unexpected error occurred while starting the server: {e}"
            )
            sys.exit(1)

    async def shutdown(self) -> None:
        # Gracefully shuts down the server.
        logger.info("Shutting down server...")
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        logger.info("Server connections closed.")
        logger.info("Shutting down executor...")
        self.executor.shutdown(wait=True)
        logger.info("Executor shut down successfully.")
        logger.info("Server shut down successfully.")

        # Clean up memory-mapped file
        if self.mmapped_file:
            self.mmapped_file.close()
            logger.info("Memory-mapped file closed.")

        # Log final performance metrics at shutdown.
        logger.info(f"Final Total Requests: {self.total_requests}")
        logger.info(f"Final Successful Requests: {self.successful_requests}")
        logger.info(f"Final Failed Requests: {self.failed_requests}")

    async def my_async_function():
        # Your async code here
        pass

    asyncio.run(my_async_function())

    def create_ssl_context(self) -> ssl.SSLContext:
        # Creates an SSL context for secure communication.
        cert_path = os.environ.get("CERT_PATH")
        if not cert_path:
            raise ValueError("CERT_PATH environment variable must be set.")
        key_path = os.environ.get("KEY_PATH")
        if not key_path:
            raise ValueError("KEY_PATH environment variable must be set.")

        if not os.path.exists(cert_path):
            logger.error(f"SSL Certificate file not found: {cert_path}")
            raise FileNotFoundError(
                f"SSL Certificate file not found: {cert_path}"
            )
        if not os.path.exists(key_path):
            logger.error(f"SSL Key file not found: {key_path}")
            raise FileNotFoundError(f"SSL Key file not found: {key_path}")

        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        return context


class Daemon:
    def __init__(self, pidfile, logfile=None):
        self.pidfile = pidfile
        self.logfile = logfile
        self._cleanup_registered = False

    def cleanup_pid_file(self):

        # Remove the PID file if it exists
        if os.path.exists(self.pidfile):
            os.remove(self.pidfile)
            print(f"DEBUG: Cleaning up PID file {self.pidfile}")

    def daemonize(self):
        # Register cleanup logic to remove PID file on exit
        if not self._cleanup_registered:
            atexit.register(self.cleanup_pid_file)
            self._cleanup_registered = True

        # Fork the parent process.
        pid = os.fork()
        if pid > 0:
            # Exit the parent process.
            sys.exit(0)

        # Create a new session.
        os.setsid()

        # Fork again to ensure the daemon cannot
        # acquire a controlling terminal.
        pid = os.fork()
        if pid > 0:
            # Exit the second parent process.
            sys.exit(0)

        # Redirect standard file descriptors.
        sys.stdout.flush()
        sys.stderr.flush()

        if self.logfile:
            # Redirect stdout and stderr to the log file.
            with open(self.logfile, "a+") as f:
                os.dup2(f.fileno(), sys.stdout.fileno())
                os.dup2(f.fileno(), sys.stderr.fileno())
        else:
            # Redirect stdout and stderr to /dev/null.
            with open(os.devnull, "r") as fnull:
                os.dup2(fnull.fileno(), sys.stdin.fileno())
            with open(os.devnull, "a+") as fnull_out:
                os.dup2(fnull_out.fileno(), sys.stdout.fileno())
                os.dup2(fnull_out.fileno(), sys.stderr.fileno())

        # Write the PID file.
        atexit.register(self.remove_pidfile)
        pid = str(os.getpid())
        with open(self.pidfile, "w+") as f:
            f.write(pid + "\n")

    def remove_pidfile(self):
        # Use the cleanup method here
        self.cleanup_pid_file()

    def start(self):
        # Start the daemon.
        if os.path.exists(self.pidfile):
            print(
                f"PID file {self.pidfile} already exists. "
                f"Is the daemon already running?"
            )
            sys.exit(1)
        self.daemonize()
        self.run()

    def stop(self):
        # Stop the daemon.
        if not os.path.exists(self.pidfile):
            print(
                f"PID file {self.pidfile} does not exist. "
                f"Is the daemon running?"
            )
            return

        with open(self.pidfile, "r") as f:
            pid = int(f.read().strip())

        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            print(f"Process with PID {pid} does not exist.")
            os.remove(self.pidfile)
            return

        os.remove(self.pidfile)

    def restart(self):
        # Restart the daemon.
        self.stop()
        self.start()

    def run(self):
        # Override this method in your subclass.
        raise NotImplementedError("You must override the run() method.")


class ServerDaemon(Daemon):
    def __init__(self, pidfile, logfile=None):
        super().__init__(pidfile, logfile)
        self.server = None

    def run(self):
        try:
            config_path = os.environ.get("CONFIG_PATH")
            if not config_path:
                raise ValueError(
                    "CONFIG_PATH environment variable must be set."
                )
            config = ServerConfig(config_path)
            self.server = AsyncTCPServer(
                host="0.0.0.0",
                port="44445",
                file_path=config.file_path,
                reread_on_query=config.reread_on_query,
                use_ssl=config.use_ssl,
            )

            if not self.server.reread_on_query:
                asyncio.run(self.server.load_file_content())

            loop = asyncio.get_event_loop()
            loop.add_signal_handler(
                signal.SIGINT,
                lambda: asyncio.create_task(self.server.shutdown())
            )
            loop.add_signal_handler(
                signal.SIGTERM,
                lambda: asyncio.create_task(self.server.shutdown())
            )
            loop.run_until_complete(self.server.start())

        except Exception as e:
            logger.error(f"Server failed to start: {e}")
            sys.exit(1)


def main():
    config_path = os.environ.get("CONFIG_PATH")
    if not config_path:
        raise ValueError("CONFIG_PATH environment variable must be set.")
    config = ServerConfig(config_path)

    pidfile = "/home/ruby/project/server_debug.pid"
    logfile = (
        config.logfile
        if config.logfile
        else "/home/ruby/project/server_debug.log"
    )
    daemon = ServerDaemon(pidfile, logfile)

    if len(sys.argv) == 2:
        if sys.argv[1] == "start":
            daemon.start()
        elif sys.argv[1] == "stop":
            daemon.stop()
        elif sys.argv[1] == "restart":
            daemon.restart()
        else:
            print("Usage: server.py {start|stop|restart}")
            sys.exit(2)
    else:
        print("Usage: server.py {start|stop|restart}")
        sys.exit(2)


if __name__ == "__main__":
    try:
        if sys.platform == "win32":
            print("Running in Windows. Daemonization is not supported.")
            # Just run the server directly in Windows
            config_path = os.environ.get("CONFIG_PATH")
            if not config_path:
                raise ValueError(
                    "CONFIG_PATH environment variable must be set."
                )
            config = ServerConfig(config_path)
            server = AsyncTCPServer(
                host="0.0.0.0",
                port="44445",
                file_path=config.file_path,
                reread_on_query=config.reread_on_query,
                use_ssl=config.use_ssl,
            )

            if not server.reread_on_query:
                asyncio.run(server.load_file_content())
            asyncio.run(server.start())
        else:
            main()
    except KeyboardInterrupt:
        logger.info("Server interrupted by keyboard, exiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
