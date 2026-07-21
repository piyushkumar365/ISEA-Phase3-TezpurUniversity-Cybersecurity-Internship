import socket
import threading
import datetime
import csv
import os
import hashlib
import re
import time
import json
import html  # Task 5: Added for input sanitization & XSS escaping
from concurrent.futures import ThreadPoolExecutor  # Task 3: Scalable Thread Pool

# Configuration Setup File Path
CONFIG_FILE = "config.json"

# Task 4: Default fallback configuration if config.json is missing or corrupted
DEFAULT_CONFIG = {
    "network": {
        "host": "0.0.0.0",
        "port": 5000,
        "max_queue_backlog": 25,
        "max_workers": 20
    },
    "security": {
        "lockout_limit": 5,
        "lockout_duration_minutes": 5,
        "inactivity_timeout_minutes": 5,
        "socket_timeout_seconds": 600.0,
        "max_msg_length": 1000,
        "rate_limit_max_msgs": 5,
        "rate_limit_window_seconds": 3
    },
    "storage": {
        "history_file": "chat_history.csv",
        "credentials_file": "users.csv",
        "security_log": "security_log.txt"
    }
}

def load_config():
    """Task 4: Dynamic JSON configuration loader with automatic generation & fallback."""
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            print("[+] Created default config.json configuration file.")
        except Exception as e:
            print(f"[-] Could not create config.json: {e}")
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[-] Failed to load config.json ({e}). Falling back to defaults.")
        return DEFAULT_CONFIG

# Load Config
config = load_config()

# Task 4 Configuration Variables
HOST = config["network"]["host"]
PORT = config["network"]["port"]
MAX_QUEUE_BACKLOG = config["network"]["max_queue_backlog"]
MAX_WORKERS = config["network"]["max_workers"]

LOCKOUT_LIMIT = config["security"]["lockout_limit"]
LOCKOUT_DURATION = datetime.timedelta(minutes=config["security"]["lockout_duration_minutes"])
INACTIVITY_TIMEOUT = datetime.timedelta(minutes=config["security"]["inactivity_timeout_minutes"])
SOCKET_TIMEOUT = config["security"]["socket_timeout_seconds"]
MAX_MSG_LENGTH = config["security"]["max_msg_length"]

# Task 5 Security Configuration
RATE_LIMIT_MAX_MSGS = config["security"].get("rate_limit_max_msgs", 5)
RATE_LIMIT_WINDOW = config["security"].get("rate_limit_window_seconds", 3)

HISTORY_FILE = config["storage"]["history_file"]
CREDENTIALS_FILE = config["storage"]["credentials_file"]
SECURITY_LOG = config["storage"]["security_log"]

# Thread Synchronization Locks
client_lock = threading.Lock()
stats_lock = threading.Lock()
rate_limit_lock = threading.Lock()  # Task 5 Lock

# Task 1: Complete Client Profiles State Store
clients = {} 

# Task 1: Required Server Metrics Tracker
server_stats = {
    "messages_processed": 0,
    "broadcast_messages": 0,
    "private_messages": 0
}

# Lockout state databases (in-memory)
failed_attempts = {}  # {username: count}
lockouts = {}         # {username: lockout_expiry_datetime}

# Task 5: In-memory rate limiting tracker {username: [timestamp1, timestamp2, ...]}
rate_limit_tracker = {}

def init_csv_stores():
    """Initializes chat histories and user accounts storage safely."""
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "sender", "receiver", "message_type", "message"])
            
    if not os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["username", "password_hash"])

def log_chat_event(sender, receiver, msg_type, message):
    """Logs ordinary chat events to the chat history database."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(HISTORY_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, sender, receiver, msg_type, message])
    except Exception as e:
        print(f"[-] CSV Logging Error: {e}")

def log_security_event(event_type, username, ip, port, details):
    """Write to security log file securely without storing plaintext passwords."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {event_type.upper()} | User: {username} | Host: {ip}:{port} | Info: {details}\n"
    try:
        with open(SECURITY_LOG, mode='a', encoding='utf-8') as f:
            f.write(log_line)
    except Exception as e:
        print(f"[-] Security Log Error: {e}")

def hash_password(password):
    """Task 2: Secure password storage using SHA-256 hashing."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def is_valid_username(username):
    """Task 4: Alphanumeric constraint on usernames (3-15 characters)."""
    return bool(re.match(r"^[a-zA-Z0-9_]{3,15}$", username))

def sanitize_input(text):
    """Task 5: Strips dangerous control characters and escapes HTML/XSS payloads."""
    if not text:
        return ""
    # Strip non-printable ASCII / control characters
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    # Escape HTML entities to prevent client-side script rendering
    return html.escape(cleaned.strip())

def is_rate_limited(username):
    """Task 5: Anti-Spam check evaluating message window limits per user."""
    now = time.time()
    with rate_limit_lock:
        timestamps = rate_limit_tracker.get(username, [])
        # Keep timestamps within the configured active time window
        timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
        
        if len(timestamps) >= RATE_LIMIT_MAX_MSGS:
            rate_limit_tracker[username] = timestamps
            return True  # Rate limit exceeded
            
        timestamps.append(now)
        rate_limit_tracker[username] = timestamps
        return False  # Allowed

def authenticate_user(username, password):
    """Task 2: Handles secure user verification and auto-registration."""
    pwd_hash = hash_password(password)
    users = {}
    
    try:
        with open(CREDENTIALS_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) == 2:
                    users[row[0]] = row[1]
    except Exception as e:
        print(f"[-] Credentials Reading Error: {e}")

    if username in users:
        if users[username] == pwd_hash:
            return "AUTH_SUCCESS"
        else:
            return "AUTH_FAIL"
    else:
        try:
            with open(CREDENTIALS_FILE, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([username, pwd_hash])
            return "REGISTERED"
        except Exception as e:
            print(f"[-] Registration Error: {e}")
            return "AUTH_ERROR"

def fetch_historical_catchup(username):
    """Retrieves last 5 sent messages for state recovery upon reconnect."""
    records = []
    if not os.path.exists(HISTORY_FILE):
        return records
    try:
        with open(HISTORY_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0] == "timestamp":
                    continue
                if len(row) >= 5 and row[1] == username:
                    records.append(f"[{row[0]}] To {row[2]}: {row[4]}")
    except Exception as e:
        print(f"[-] History Fetch Error: {e}")
        
    return records[-5:]

def update_and_display_dashboard():
    """Prints active server telemetry to console."""
    with client_lock:
        active_count = sum(1 for c in clients.values() if c["status"] == "ONLINE")
    with stats_lock:
        print("\n========== SERVER SECURITY DASHBOARD ==========")
        print(f"Active Secure Connections: {active_count}")
        print(f"System Message Load      : {server_stats['messages_processed']}")
        print(f"Global Broadcasts        : {server_stats['broadcast_messages']}")
        print(f"Private Secret Messages  : {server_stats['private_messages']}")
        print("===============================================\n")

def broadcast_system_message(text_content, exclude_user=None):
    """Task 3: Scalable broadcast using Snapshot pattern to eliminate lock contention."""
    with client_lock:
        targets = [
            (user, metadata["socket"]) 
            for user, metadata in clients.items() 
            if metadata["status"] == "ONLINE" and user != exclude_user
        ]

    encoded_payload = text_content.encode('utf-8')
    for user, sock in targets:
        try:
            sock.sendall(encoded_payload)
        except Exception:
            pass

def inactivity_monitor_thread():
    """Periodically scans for inactive TCP clients and times them out."""
    while True:
        time.sleep(10)
        now = datetime.datetime.now()
        timed_out_clients = []
        
        with client_lock:
            for user, metadata in list(clients.items()):
                if metadata["status"] == "ONLINE":
                    if now - metadata["last_activity"] > INACTIVITY_TIMEOUT:
                        timed_out_clients.append((user, metadata["socket"], metadata["ip"], metadata["port"]))
                        
        for user, sock, ip, port in timed_out_clients:
            try:
                sock.sendall("SYSTEM:TIMEOUT:Your session expired due to inactivity.".encode('utf-8'))
                sock.close()
            except Exception:
                pass
            log_security_event("session_timeout", user, ip, port, "Disconnected due to inactivity.")

def handle_client_worker(client_socket, client_address):
    ip, port = client_address
    username = None
    
    # Task 1: TCP keepalive activation
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    
    try:
        auth_payload = client_socket.recv(1024).decode('utf-8', errors='ignore').strip()
        if not auth_payload or "||" not in auth_payload:
            client_socket.sendall("AUTH_FAIL:Invalid authentication protocol.".encode('utf-8'))
            client_socket.close()
            return
        
        username_payload, password_payload = auth_payload.split("||", 1)
        
        # Task 5: Guard against protocol delimiter injection
        if "||" in username_payload or "||" in password_payload:
            client_socket.sendall("AUTH_FAIL:Security alert: Illegal delimiter '||' detected.".encode('utf-8'))
            log_security_event("injection_attempt", username_payload, ip, port, "Attempted protocol delimiter injection.")
            client_socket.close()
            return

        # Task 5: Input Sanitization
        username_payload = sanitize_input(username_payload)
        
        if not is_valid_username(username_payload):
            client_socket.sendall("AUTH_FAIL:Username must be 3-15 characters (alphanumeric only).".encode('utf-8'))
            log_security_event("validation_failed", username_payload, ip, port, "Rejected invalid username format.")
            client_socket.close()
            return
            
        if not password_payload.strip():
            client_socket.sendall("AUTH_FAIL:Empty password submitted.".encode('utf-8'))
            log_security_event("validation_failed", username_payload, ip, port, "Rejected empty password attempt.")
            client_socket.close()
            return

        now = datetime.datetime.now()
        
        # Task 2: Lockout Protection Check
        if username_payload in lockouts:
            if now < lockouts[username_payload]:
                remaining_sec = int((lockouts[username_payload] - now).total_seconds())
                client_socket.sendall(f"AUTH_FAIL:Account locked. Please try again in {remaining_sec}s.".encode('utf-8'))
                log_security_event("lockout_blocked", username_payload, ip, port, "Attempt during an active lockout.")
                client_socket.close()
                return
            else:
                del lockouts[username_payload]
                failed_attempts[username_payload] = 0

        auth_status = authenticate_user(username_payload, password_payload)
        
        if auth_status == "AUTH_FAIL":
            failed_attempts[username_payload] = failed_attempts.get(username_payload, 0) + 1
            attempts_left = LOCKOUT_LIMIT - failed_attempts[username_payload]
            
            log_security_event("failed_login", username_payload, ip, port, f"Incorrect password (Attempt {failed_attempts[username_payload]}/{LOCKOUT_LIMIT}).")
            
            if failed_attempts[username_payload] >= LOCKOUT_LIMIT:
                lockouts[username_payload] = now + LOCKOUT_DURATION
                log_security_event("account_locked", username_payload, ip, port, f"Lockout state activated for {config['security']['lockout_duration_minutes']} minutes.")
                client_socket.sendall(f"AUTH_FAIL:Too many incorrect attempts. Locked out for {config['security']['lockout_duration_minutes']} minutes.".encode('utf-8'))
            else:
                client_socket.sendall(f"AUTH_FAIL:Incorrect credentials. {attempts_left} attempts remaining.".encode('utf-8'))
                
            client_socket.close()
            return
        
        elif auth_status == "AUTH_ERROR":
            client_socket.sendall("AUTH_FAIL:Server processing credentials error.".encode('utf-8'))
            client_socket.close()
            return
            
        # Task 3: Concurrent Duplicate Login Prevention
        with client_lock:
            if username_payload in clients and clients[username_payload]["status"] == "ONLINE":
                client_socket.sendall("AUTH_FAIL:User already logged in from another location.".encode('utf-8'))
                log_security_event("duplicate_login_blocked", username_payload, ip, port, "Prevented concurrent active session.")
                client_socket.close()
                return

        # Login Approved - Clear failure counts and register session
        username = username_payload
        failed_attempts[username] = 0 
        login_time = datetime.datetime.now().strftime("%H:%M:%S")
        log_security_event("successful_login", username, ip, port, f"Session established successfully ({auth_status}).")

        historical_payload = fetch_historical_catchup(username)
        
        with client_lock:
            clients[username] = {
                "socket": client_socket,
                "ip": ip,
                "port": port,
                "login_time": login_time,
                "status": "ONLINE",
                "last_activity": datetime.datetime.now()
            }
            
        welcome_banner = f"\n[SERVER] Secure connection established as '{username}' from {ip}:{port}\n"
        if historical_payload:
            welcome_banner += "--- Your Last 5 Sent Messages (State Recovered) ---\n" + "\n".join(historical_payload) + "\n-------------------------------------------------\n"
        client_socket.sendall(welcome_banner.encode('utf-8'))
        
        print(f"CONNECTED : {username}")
        broadcast_system_message(f"JOIN:{username}", exclude_user=username)
        
        with client_lock:
            online_users = [u for u, m in clients.items() if m["status"] == "ONLINE"]
        client_socket.sendall(f"USERLIST:{','.join(online_users)}".encode('utf-8'))
        
        update_and_display_dashboard()
        
        # Primary Socket Reception Loop
        while True:
            raw_data = client_socket.recv(4096)
            if not raw_data:
                break
                
            incoming_text = raw_data.decode('utf-8', errors='ignore').strip()
            if not incoming_text:
                continue
                
            # Task 5: Anti-Spam Rate Limiting Check
            if is_rate_limited(username):
                client_socket.sendall("SYSTEM:ERROR Rate limit exceeded. Slow down your messages!".encode('utf-8'))
                log_security_event("rate_limit_exceeded", username, ip, port, "Temporarily throttled due to message flooding.")
                continue

            # Task 5: Sanitize incoming message content
            incoming_text = sanitize_input(incoming_text)
            
            with client_lock:
                if username in clients:
                    clients[username]["last_activity"] = datetime.datetime.now()
                    
            if len(incoming_text) > MAX_MSG_LENGTH:
                client_socket.sendall(f"SYSTEM:ERROR Message rejected. Must not exceed {MAX_MSG_LENGTH} characters.".encode('utf-8'))
                log_security_event("oversized_message_rejected", username, ip, port, f"Rejected oversized message ({len(incoming_text)} characters).")
                continue
                
            if incoming_text.startswith('/'):
                parts = incoming_text.split()
                command = parts[0]
                if command not in ['/list', '/msg', '/logout']:
                    client_socket.sendall(f"SYSTEM:ERROR Unsupported command '{command}'.".encode('utf-8'))
                    log_security_event("unsupported_command", username, ip, port, f"Attempted execution of unsupported command: {command}")
                    continue

            with stats_lock:
                server_stats["messages_processed"] += 1
                
            if incoming_text == '/list':
                with client_lock:
                    active_list = [u for u, m in clients.items() if m["status"] == "ONLINE"]
                response = f"[Online System Users]: " + ", ".join(active_list)
                client_socket.sendall(response.encode('utf-8'))
                
            elif incoming_text == '/logout':
                client_socket.sendall("SYSTEM:LOGOUT:Logged out successfully.".encode('utf-8'))
                log_security_event("user_logout", username, ip, port, "User requested regular session termination.")
                break
                
            elif incoming_text.startswith('/msg '):
                parts = incoming_text.split(' ', 2)
                if len(parts) < 3:
                    client_socket.sendall("[System Error] Syntax: /msg <username> <message>".encode('utf-8'))
                    continue
                target, secret_msg = parts[1], parts[2]
                
                target_socket = None
                with client_lock:
                    if target in clients and clients[target]["status"] == "ONLINE":
                        target_socket = clients[target]["socket"]

                if target_socket:
                    try:
                        target_socket.sendall(f"[Private from {username}]: {secret_msg}".encode('utf-8'))
                        log_chat_event(username, target, "private", secret_msg)
                        with stats_lock:
                            server_stats["private_messages"] += 1
                    except Exception:
                        client_socket.sendall(f"[System Error] Message delivery to '{target}' failed.".encode('utf-8'))
                else:
                    client_socket.sendall(f"[System Error] User '{target}' does not exist or is offline.".encode('utf-8'))
            
            else:
                broadcast_system_message(f"[{username}]: {incoming_text}", exclude_user=username)
                log_chat_event(username, "ALL", "broadcast", incoming_text)
                with stats_lock:
                    server_stats["broadcast_messages"] += 1
                    
            update_and_display_dashboard()
            
    except ConnectionResetError:
        print(f"[-] Client {username if username else ip} forcefully disconnected.")
    except Exception as e:
        print(f"[-] Processing exception on user '{username if username else ip}': {e}")
    finally:
        # Task 1 & Task 5: Complete Resource Cleanup
        if username:
            with client_lock:
                if username in clients:
                    del clients[username]
            
            with rate_limit_lock:
                if username in rate_limit_tracker:
                    del rate_limit_tracker[username]
            
            print(f"DISCONNECTED : {username}")
            broadcast_system_message(f"LEAVE:{username}")
            log_chat_event(username, "Server", "system_leave", f"{username} disconnected.")
            update_and_display_dashboard()
            
        try:
            client_socket.close()
        except Exception:
            pass

def graceful_server_shutdown(engine):
    """Task 2: Gracefully notifies all clients and releases sockets on server shutdown."""
    print("\n[*] Initiating graceful server shutdown...")
    with client_lock:
        for user, metadata in list(clients.items()):
            try:
                metadata["socket"].sendall("SYSTEM:LOGOUT:Server is shutting down.".encode('utf-8'))
                metadata["socket"].close()
            except Exception:
                pass
        clients.clear()
    try:
        engine.close()
    except Exception:
        pass
    print("[*] Server shutdown complete.")

def main():
    init_csv_stores()
    
    monitor = threading.Thread(target=inactivity_monitor_thread, daemon=True)
    monitor.start()
    
    engine = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    engine.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    
    try:
        engine.bind((HOST, PORT))
        engine.listen(MAX_QUEUE_BACKLOG)
        print(f"[*] Server initialized with config.json limits.")
        print(f"[*] Listening on {HOST}:{PORT} | Workers: {MAX_WORKERS} | Lockout: {LOCKOUT_LIMIT} attempts")
        
        while True:
            try:
                sock, addr = engine.accept()
                sock.settimeout(SOCKET_TIMEOUT) 
                executor.submit(handle_client_worker, sock, addr)
            except socket.timeout:
                continue
            except Exception as e:
                break
            
    except KeyboardInterrupt:
        graceful_server_shutdown(engine)
    finally:
        executor.shutdown(wait=False)
        try:
            engine.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()