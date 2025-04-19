import socket
import ssl
import argparse

def parse_arguments() -> argparse.Namespace:
    # Parses command-line arguments provided by the user.
    # Returns the parsed arguments.
    parser = argparse.ArgumentParser(
        description="Send a query to the server."
    )

    # Define command-line arguments
    parser.add_argument(
        "--server_address", type=str,
        default="localhost", help="Server address"
    )
    parser.add_argument(
        "--server_port", type=int,
        default=44445, help="Server port"
    )
    parser.add_argument(
        "--use_ssl", action="store_true", help="Use SSL for secure connection"
    )
    parser.add_argument(
        "--query", type=str, required=True, help="Query string to search for"
    )
    parser.add_argument(
        "--cert_path",
        type=str, default="cert.pem",
        help="Path to SSL certificate"
    )
    return parser.parse_args()


def main() -> None:
    # Main function to connect to the server and send the query.
    args = parse_arguments()

    # Display connection details
    print(
        f"[*] Connecting to server at "
        f"{args.server_address}:{args.server_port} "
        f"with SSL={'Yes' if args.use_ssl else 'No'}"
    )
    print(f"[*] Sending query: {args.query}")

    try:
        # Create an SSL context for secure connections
        context = ssl.create_default_context()

        # Configure SSL settings if enabled
        if args.use_ssl:
            cert_path = args.cert_path
            # Disable hostname verification and certificate validation for simplicity
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            # Load the SSL certificate
            context.load_verify_locations(cert_path)

        # Establish a socket connection to the server
        with socket.create_connection(
            (args.server_address, args.server_port)
        ) as client_socket:
            # Wrap the socket with SSL if enabled
            if args.use_ssl:
                client_socket = context.wrap_socket(
                    client_socket, server_hostname=args.server_address
                )

            # Send the query to the server
            client_socket.sendall(args.query.encode("utf-8"))
            # Receive the server's response
            response = client_socket.recv(1024).decode("utf-8")
            print(f"[*] Server response: {response}")

    except Exception as e:
        # Handle any exceptions during connection or query processing
        print(f"Error: {e}")


if __name__ == "__main__":
    # Run the main function when the script is executed directly
    main()
