import asyncio
import time
import os
import ssl  # Import ssl module for SSL support


async def send_query(host, port, query, use_ssl=False):
    # Sends a query to the server and measures response time.
    start_time = time.perf_counter()  # Start timing

    ssl_context = None
    if use_ssl:
        ssl_context = ssl.create_default_context()

    # Establish connection to the server, optionally using SSL
    reader, writer = await asyncio.open_connection(host, port, ssl=ssl_context)
    # Send the query
    writer.write(query.encode())
    await writer.drain()

    response = await reader.read(1024)
    end_time = time.perf_counter()

    # Calculate execution time
    execution_time = end_time - start_time

    print(
        f"Query: '{query}' | "
        f"Response: {response.decode().strip()} | "
        f"Time: {execution_time:.4f} sec"
    )

    writer.close()
    await writer.wait_closed()


async def main():
    host = os.getenv("TEST_HOST", "127.0.0.1")
    port = int(os.getenv("TEST_PORT", "44445"))
    use_ssl = False  # Set to True if testing with SSL
    queries = ["hello", "test", "another test"] * 100

    tasks = [send_query(host, port, query, use_ssl) for query in queries]

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
