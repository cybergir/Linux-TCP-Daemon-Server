import win32serviceutil
import win32service
import servicemanager
import os
import sys
import threading
import logging


class TCPServerService(win32serviceutil.ServiceFramework):
    # Defines the TCP Server Service as a Windows service.
    _svc_name_ = "TCPServerService"
    _svc_display_name_ = "TCP Server Service"
    _svc_description_ = "A TCP server running as a Windows service."

    def __init__(self, args):
        # Initializes the service and sets up the necessary attributes.
        super().__init__(args)
        self.stop_event = threading.Event()  # Event used to signal service termination

        # Get the path to the server script from the environment variable,
        # or use the default path if not specified.
        self.server_script_path = os.getenv(
            "SERVER_SCRIPT_PATH",
            os.path.join(os.path.dirname(__file__), "server.py")
        )

        # Get the path for the log file from the environment variable,
        # or use a default location if not set.
        self.log_file_path = os.getenv(
            "LOG_FILE_PATH",
            os.path.join(os.path.dirname(__file__), "service_debug.log"),
        )

    def SvcDoRun(self):
        # This function is executed when the service starts.
        # It initializes logging and runs the TCP server script.
        logging.basicConfig(
            filename=self.log_file_path,
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

        logging.info("Starting TCP Server Service...")

        try:
            # Construct and execute the command to run the server script.
            command = f'python "{self.server_script_path}"'
            logging.info(f"Running command: {command}")
            os.system(command)  # Execute the server script
        except Exception as e:
            # Log any errors encountered while launching the server script.
            logging.error(f"Error launching server.py: {e}")
            self.SvcStop()  # Stop the service in case of an error

    def SvcStop(self):
        # Handles the stopping of the service.
        servicemanager.LogInfoMsg("TCP Server Service is stopping...")
        self.stop_event.set()  # Signal the service to stop
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)


if __name__ == "__main__":
    # Entry point for running the service script.
    if len(sys.argv) == 1:
        # If no command-line arguments are provided, start the service dispatcher.
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(TCPServerService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Handle command-line service management (install, remove, start, stop, etc.).
        win32serviceutil.HandleCommandLine(TCPServerService)
