# Linux-TCP-Daemon-Server

A high-performance, secure TCP server daemon for processing search queries with SSL support, Linux daemonization, and benchmarking functionality.

---

## 🚀 Project Overview

This project implements a robust TCP server designed to handle search queries efficiently. It runs as a Linux daemon managed by systemd, supports secure communication using SSL certificates, and includes comprehensive benchmarking to measure search algorithm performance.

---

## ✨ Key Features

- **TCP Server Daemon** running as a Linux systemd service
- **Secure SSL/TLS Communication** for encrypted client-server data exchange
- Multiple **search algorithms** implemented and benchmarked:
  - Linear Search
  - Binary Search
  - Hash-based Search
  - Trie Search
  - Regex Search
- **Performance benchmarking** with automatic report generation (PDF + graphs)
- Environment-variable-driven configuration for easy deployment and portability
- Clear, maintainable codebase with PEP 8 compliance

---

## ⚙️ Installation & Setup

1. **Clone the repository**
git clone https://github.com/yourusername/Linux-TCP-Daemon-Server.git
cd Linux-TCP-Daemon-Server


2. **Create and activate virtual environment**
python3 -m venv venv
source venv/bin/activate # Linux/macOS
venv\Scripts\activate # Windows


3. **Install dependencies**
pip install -r requirements.txt


4. **Generate SSL certificates**
openssl req -newkey rsa:2048 -nodes -keyout key.pem -x509 -days 365 -out cert.pem


5. **Configure environment variables**

Example:
export LINUX_PATH=/path/to/search/file.txt
export CERT_PATH=/path/to/cert.pem
export KEY_PATH=/path/to/key.pem


6. **Install and start the systemd service**
sudo cp tcpserver.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tcpserver.service
sudo systemctl start tcpserver.service



---

## 🎯 Running Benchmarks

Run the benchmarking script to test search algorithm performance:
python benchmark_file_search.py


This will generate a PDF report (`speed_testing_report.pdf`) and a performance graph saved to the system temp directory.

---

## 📄 Project Structure

Linux-TCP-Daemon-Server/
│
├── server.py - TCP server implementation
├── client.py - Client script to query the server
├── benchmark_file_search.py - Benchmarking and report generation
├── tcpserver.service - systemd service file for daemonization
├── requirements.txt - Python dependencies
├── cert.pem - SSL certificate (example)
├── key.pem - SSL private key (example)
└── README.md - Project overview and instructions


---

## 🛠 Technologies Used

- Python 3.12
- `socket`, `ssl`, `argparse`
- `FPDF` for PDF report generation
- `matplotlib` and `pandas` for benchmarks and visualization
- Linux systemd for daemon/service management
- OpenSSL for SSL certificate creation

---

Thank you for checking out my project! Feedback and contributions are welcome. 😊
