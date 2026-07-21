import socket
import time
import threading
import csv
import random
import string
import sys
import psutil

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
RESULTS_FILE = "performance_results.csv"

# Concurrency levels to evaluate
CLIENT_SCENARIOS = [5,8,10]
MSGS_PER_CLIENT = 20

def find_server_process():
    """Finds active server.py or server_base.py process to monitor PID metrics."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = proc.info['cmdline']
            if cmd and any('server' in arg for arg in cmd):
                p = psutil.Process(proc.info['pid'])
                p.cpu_percent(interval=None) # Warm-up CPU baseline counter
                return p
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

def generate_random_string(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def simulate_client(client_id, results_list, lock):
    username = f"test_{client_id}_{generate_random_string()}"
    password = "password123"
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((SERVER_HOST, SERVER_PORT))
        
        # Authenticate
        handshake = f"{username}||{password}"
        sock.sendall(handshake.encode('utf-8'))
        welcome = sock.recv(1024).decode('utf-8', errors='ignore')
        
        if "AUTH_FAIL" in welcome:
            return

        sock.recv(1024) # Skip user list message

        for i in range(MSGS_PER_CLIENT):
            time.sleep(0.05)
            msg = f"Performance test message {i} from {username}"
            start_time = time.time()
            
            sock.sendall(msg.encode('utf-8'))
            sock.settimeout(3.0)
            
            try:
                reply = sock.recv(1024).decode('utf-8', errors='ignore')
                latency = (time.time() - start_time) * 1000 # ms
                
                with lock:
                    results_list.append({"status": "SUCCESS", "latency_ms": latency})
            except socket.timeout:
                with lock:
                    results_list.append({"status": "TIMEOUT", "latency_ms": 3000})

        sock.sendall("/logout".encode('utf-8'))
    except Exception:
        pass
    finally:
        sock.close()

def run_benchmarks(stage_tag):
    server_proc = find_server_process()
    if not server_proc:
        print("[-] Error: No server process found! Make sure a server is running.")
        sys.exit(1)

    print(f"[+] Attached monitoring to server PID {server_proc.pid} ({stage_tag})")

    file_exists = False
    try:
        with open(RESULTS_FILE, 'r'): file_exists = True
    except FileNotFoundError:
        pass

    if not file_exists:
        with open(RESULTS_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "stage", "concurrent_clients", "total_messages", 
                "avg_latency_ms", "p95_latency_ms", "throughput_msg_per_sec", 
                "cpu_usage_pct", "memory_usage_mb"
            ])

    for num_clients in CLIENT_SCENARIOS:
        print(f"    [*] Testing {num_clients} concurrent clients...")
        
        threads = []
        metrics = []
        lock = threading.Lock()
        
        cpu_samples = []
        mem_samples = []
        
        start_benchmark_time = time.time()
        
        for c_id in range(num_clients):
            t = threading.Thread(target=simulate_client, args=(c_id, metrics, lock))
            threads.append(t)
            t.start()

        # Sample hardware utilization during test execution
        while any(t.is_alive() for t in threads):
            try:
                cpu_samples.append(server_proc.cpu_percent(interval=0.1))
                mem_samples.append(server_proc.memory_info().rss / (1024 * 1024)) # MB
            except Exception:
                break
            time.sleep(0.1)

        for t in threads:
            t.join()

        total_duration = time.time() - start_benchmark_time
        total_msgs = len(metrics)
        
        latencies = sorted([m["latency_ms"] for m in metrics if m["status"] == "SUCCESS"])
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        
        # Calculate P95 latency percentile
        p95_idx = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_idx] if latencies else 0.0

        throughput = total_msgs / total_duration if total_duration > 0 else 0.0
        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0
        avg_mem = sum(mem_samples) / len(mem_samples) if mem_samples else 0.0

        # Save results to CSV
        with open(RESULTS_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                stage_tag,
                num_clients,
                total_msgs,
                round(avg_latency, 2),
                round(p95_latency, 2),
                round(throughput, 2),
                round(avg_cpu, 1),
                round(avg_mem, 2)
            ])

    print(f"[+] Recorded {stage_tag} metrics into '{RESULTS_FILE}'.")

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "Baseline"
    run_benchmarks(stage)