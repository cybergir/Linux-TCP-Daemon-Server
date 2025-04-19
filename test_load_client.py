import asyncio
import time
import os


async def send_query(host, port, query):
    # Sends a query to the server and measures the response time.
    reader, writer = await asyncio.open_connection(host, port)

    # Record the start time for performance measurement
    start_time = time.perf_counter()

    # Send the encoded query to the server
    writer.write(query.encode())
    await writer.drain()

    # Read the response from the server (up to 1024 bytes)
    data = await reader.read(1024)

    end_time = time.perf_counter()
    execution_time = end_time - start_time

    print(
        f"Received: {data.decode().strip()} ("
        f"Execution Time: {execution_time:.4f} seconds)"
    )

    writer.close()  # Close the connection to the server


async def main():
    # Main function to run multiple queries concurrently.
    host = os.getenv("SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("SERVER_PORT", 44445))
    queries = ["hello world", "test string", "another string"] * 100

    tasks = [send_query(host, port, query) for query in queries]

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
