# Assignment 8 - Application Optimization, Scalability and Reliability

**ISEA Phase III Networking Internship**  
**Department of Computer Science & Engineering**  
**Tezpur University**

---

## Objective

This assignment extends the GUI-based Multi-Client Chat Application developed in Assignment 7 by improving its scalability, reliability, maintainability, and overall software quality.

The communication protocol from the previous assignment is preserved while implementing software optimizations such as automatic reconnection, timeout handling, better resource management, configuration management, and performance evaluation.

---

## Features

### Connection Management
- Automatic detection of disconnected clients
- Removal of inactive client connections
- Proper socket and resource cleanup
- User-friendly error messages

### Reliability Enhancements
- Automatic client reconnection
- Graceful shutdown
- Socket timeout handling
- Improved exception handling

### Scalability Improvements
- Supports up to 10 concurrent clients
- Efficient thread management
- Stable message broadcasting
- Proper handling of multiple client connections

### Configuration Management
- All configurable parameters stored in `config.json`
- No hardcoded IP addresses or ports
- Easy deployment and maintenance

### Performance Evaluation
- Delay measurement
- Throughput calculation
- CPU usage monitoring
- Memory usage monitoring
- Automatic generation of performance data

### Wireshark Verification
- Verification of TCP three-way handshake
- Chat message transmission analysis
- Connection termination verification

---

## Project Structure

```
Assignment_8/
│
├── server.py
├── client_gui.py
├── config.json
├── performance_results.csv
├── chat_log.txt
├── server_log.txt
│
├── graphs/
│   ├── delay_vs_clients.png
│   ├── throughput_vs_clients.png
│   ├── cpu_usage.png
│   └── memory_usage.png
│
├── screenshots/
│   ├── server_running.png
│   ├── clients_connected.png
│   ├── performance_graphs.png
│   └── wireshark_capture.png
│
├── report.pdf
├── handwritten_reflection.pdf
└── README.md
```

---

## Requirements

- Python 3.10 or later
- Mininet
- Wireshark
- Windows/Linux operating system

---

## Python Modules Used

```python
socket
threading
json
time
datetime
os
csv
psutil
tkinter
```

Install additional dependency:

```bash
pip install psutil
```

---

## Configuration

All application settings are stored in `config.json`.

Example:

```json
{
    "SERVER_IP": "127.0.0.1",
    "SERVER_PORT": 5000,
    "BUFFER_SIZE": 1024,
    "TIMEOUT": 10,
    "MAX_CLIENTS": 10,
    "RECONNECT_DELAY": 5
}
```

---

## Running the Server

```bash
python server.py
```

---

## Running the Client

```bash
python client_gui.py
```

Run multiple client instances to test concurrent communication.

---

## Mininet Setup

Create a single topology with eleven hosts.

```bash
sudo mn --topo single,11
```

Test with:

- 5 clients
- 8 clients
- 10 clients

---

## Performance Evaluation

The optimized application is evaluated using the following metrics:

- Average Message Delay
- Throughput (messages/second)
- CPU Usage
- Memory Usage

Results are stored in:

```
performance_results.csv
```

Graphs are saved inside:

```
graphs/
```

---

## Wireshark Verification

Capture TCP packets while clients communicate with the server.

Verify:

- TCP Three-Way Handshake
- Data Transmission
- ACK Packets
- Graceful Connection Termination

---

## Optimizations Implemented

- Automatic client reconnection
- Graceful shutdown
- Timeout handling
- Better exception handling
- Resource cleanup
- Improved thread management
- Configuration file support
- Performance monitoring
- Better scalability for concurrent users

---

## Output Files

The project generates the following files automatically:

- `chat_log.txt`
- `server_log.txt`
- `performance_results.csv`

Generated graphs are stored in:

```
graphs/
```

---

## Learning Outcomes

After completing this assignment, the following concepts are demonstrated:

- TCP Client-Server Programming
- Multi-threading
- Resource Management
- Fault Tolerance
- Scalability
- Reliability
- Performance Analysis
- Configuration Management
- Wireshark Packet Analysis

---

## Future Improvements

- Support for 100+ concurrent users
- Thread Pool implementation
- Asynchronous socket programming
- SSL/TLS encryption
- User authentication
- File transfer support
- Private messaging
- Database integration
- Message persistence
- Cross-platform executable packaging

---

## Author

Name : Piyush Kumar
Roll : CSB24051
Course : B.Tech in Computer Science and Engineering
University : Tezpur University
ISEA Phase III Networking Internship  
Department of Computer Science & Engineering  
Tezpur University
