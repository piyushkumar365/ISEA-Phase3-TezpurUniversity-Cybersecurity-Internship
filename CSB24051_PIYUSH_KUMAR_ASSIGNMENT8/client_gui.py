import tkinter as tk
from tkinter import messagebox
import tkinter.scrolledtext as scrolledtext
import socket
import threading

class ChatClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure TCP Chat Client")
        self.root.geometry("750x600")
        
        # Networking Configuration
        self.server_ip = "10.0.0.1"  # Mininet Configuration Host IP
        self.port = 5000
        self.sock = None
        self.username = ""
        self.password = ""
        self.online_users = []
        self.is_reconnecting=False
        
        #Task2 assingment 08 : -> Intercept window exit event for graceful shutdown
        self.root.protocol("WM_DELETE_WINDOW",self.on_closing)
        # Render Login Interface initially
        self.create_login_window()

    def on_closing(self):
        """Task 2: Graceful GUI shutdown on window close button click."""
        if self.sock:
            try:
                self.sock.sendall("/logout".encode('utf-8'))
                self.sock.close()
            except Exception:
                pass
            self.root.destory()

    def create_login_window(self):
        """Task 1: Login panel containing username and hidden-input password."""
        self.login_frame = tk.Frame(self.root)
        self.login_frame.pack(expand=True, fill=tk.BOTH)
        
        # Title Header
        tk.Label(self.login_frame, text="Secure TCP Chat Application", font=("Helvetica", 16, "bold")).pack(pady=(100, 20))
        
        # Username Entry Setup
        tk.Label(self.login_frame, text="Enter Username:", font=("Helvetica", 12)).pack(pady=5)
        self.username_entry = tk.Entry(self.login_frame, font=("Helvetica", 12), width=25)
        self.username_entry.pack(pady=5)
        self.username_entry.focus()
        
        # Password Entry Setup (Task 1 & Task 2 Integration)
        tk.Label(self.login_frame, text="Enter Password:", font=("Helvetica", 12)).pack(pady=5)
        self.password_entry = tk.Entry(self.login_frame, font=("Helvetica", 12), width=25, show="*")
        self.password_entry.pack(pady=5)
        
        # Connect Button Trigger
        tk.Button(self.login_frame, text="Connect", command=self.connect_to_server, 
                  font=("Helvetica", 12), bg="#4CAF50", fg="white", width=15).pack(pady=20)
        
        # Bind the Enter key for swift submissions
        self.root.bind('<Return>', lambda event: self.connect_to_server())

    def connect_to_server(self):
        """Validates credentials before trying to bind to the server."""
        user = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        # Task 4 Input Validation: Block blank submissions before hitting socket resources
        if not user or not password:
            messagebox.showwarning("Validation Error", "Username and Password fields cannot be empty!")
            return
            
        try:
            # Setup Socket Parameters
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
           #task2: assignment08 : 5-second connection timeout to avoid GUI FREEZE
            self.sock.settimeout(5.0)
            self.sock.connect((self.server_ip, self.port))
            
            self.username = user
            self.password=password #saved for reconnect handling
            
            # Send securely serialized payload username||password
            auth_payload = f"{user}||{password}"
            self.sock.sendall(auth_payload.encode('utf-8'))
            
            # Wait for handshake response
            server_response = self.sock.recv(4096).decode('utf-8')
            
            # Handle authentications failures
            if server_response.startswith("AUTH_FAIL"):
                error_msg = server_response.split(":", 1)[1] if ":" in server_response else "Authentication failed."
                messagebox.showerror("Secure Authentication Error", error_msg)
                self.sock.close()
                self.sock = None
                return
            
            # Switch view frames
            self.login_frame.destroy()
            self.root.unbind('<Return>')
            self.create_chat_window()
            
            # Write initial connection info/history catches to log output
            self.append_message(server_response)
            #task2 :rest socket back to blocking mode with hight timeout for normal reads
            self.sock.settimeout(None)
            # Start communications receiving threads
            receiver_thread = threading.Thread(target=self.receive_messages, daemon=True)
            receiver_thread.start()

        except socket.timeout:
            messagebox.showerror("Timeout Error","Connection time out. Server might be down.")
            if self.sock:
                self.sock.close()
                self.sock = None
        except Exception as e:
            messagebox.showerror("Connection Error", f"Unable to establish TCP socket: {e}")
            if self.sock:
                self.sock.close()
                self.sock = None

    def create_chat_window(self):
        """Task 2: Interface layout config containing user status list."""
        self.chat_frame = tk.Frame(self.root)
        self.chat_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Top status bar controls
        top_frame = tk.Frame(self.chat_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(top_frame, text=f"Active User Account: {self.username}", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(top_frame, text="Logout/Disconnect", command=self.logout_user, bg="#f44336", fg="white").pack(side=tk.RIGHT)

        # Middle frame layout
        middle_frame = tk.Frame(self.chat_frame)
        middle_frame.pack(expand=True, fill=tk.BOTH, pady=(0, 10))

        # Main Text output Scroller
        self.chat_display = scrolledtext.ScrolledText(middle_frame, wrap=tk.WORD, state='disabled', font=("Helvetica", 10))
        self.chat_display.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 10))

        # Right side: Online User viewbox
        user_list_frame = tk.Frame(middle_frame, width=150)
        user_list_frame.pack(side=tk.RIGHT, fill=tk.Y)
        user_list_frame.pack_propagate(False)

        tk.Label(user_list_frame, text="Active Profiles", font=("Helvetica", 10, "bold"), bg="#ddd").pack(fill=tk.X)
        self.user_listbox = tk.Listbox(user_list_frame, font=("Helvetica", 10))
        self.user_listbox.pack(expand=True, fill=tk.BOTH)

        # Bottom Frame Setup
        bottom_frame = tk.Frame(self.chat_frame)
        bottom_frame.pack(fill=tk.X)

        self.msg_entry = tk.Entry(bottom_frame, font=("Helvetica", 12))
        self.msg_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))
        self.msg_entry.bind('<Return>', lambda event: self.send_message())

        tk.Button(bottom_frame, text="Send", command=self.send_message, bg="#2196F3", fg="white", width=10).pack(side=tk.RIGHT)

    def send_message(self):
        """Dispatches normal transmissions, custom commands, or private messages."""
        message = self.msg_entry.get().strip()
        if not message:
            return
            
        selected_indices = self.user_listbox.curselection()
        if selected_indices:
            target_user = self.user_listbox.get(selected_indices[0])
            self.user_listbox.selection_clear(0, tk.END)
            final_message = f"/msg {target_user} {message}"
            self.append_message(f"[Private to {target_user}]: {message}")
        else:
            final_message = message

        try:
            self.sock.sendall(final_message.encode('utf-8'))
            self.msg_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send packet to host: {e}")

    def append_message(self, message):
        """Thread-safe helper insertion method to append messages to the scrolling log."""
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)

    def add_user_to_list(self, user):
        """Saves active status list to GUI."""
        if user not in self.online_users:
            self.online_users.append(user)
            self.user_listbox.insert(tk.END, user)
    
    def remove_user_from_list(self, user):
        """Handles GUI list cleanup upon user disconnect."""
        if user in self.online_users:
            self.online_users.remove(user)
            self.user_listbox.delete(0, tk.END)
            for u in self.online_users:
                self.user_listbox.insert(tk.END, u)

    def logout_user(self):
        """Sends clean session exit signal to server."""
        if self.sock:
            try:
                self.sock.sendall("/logout".encode('utf-8'))
            except Exception:
                self.graceful_revert_to_login("Connection lost. Resetting session.")

    def graceful_revert_to_login(self, info_reason):
        """Task 6: Safely drops connection and resets to initial login screen."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        
        self.online_users = []
        self.username = ""
        
        # Reset GUI Window
        if hasattr(self, 'chat_frame') and self.chat_frame.winfo_exists():
            self.chat_frame.destroy()
            
        self.create_login_window()
        messagebox.showinfo("Session Status", info_reason)


    def attempt_reconnect(self):
        """Task 2: Automatic reconnection routine with exponential retry logic."""
        if self.is_reconnecting:
            return
        self.is_reconnecting = True
        
        self.append_message("[System Warning] Lost connection. Attempting automatic reconnection...")
        
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                import time
                time.sleep(2)  # Wait 2 seconds between retry attempts
                
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(4.0)
                self.sock.connect((self.server_ip, self.port))
                
                auth_payload = f"{self.username}||{self.password}"
                self.sock.sendall(auth_payload.encode('utf-8'))
                
                resp = self.sock.recv(4096).decode('utf-8')
                if not resp.startswith("AUTH_FAIL"):
                    self.sock.settimeout(None)
                    self.is_reconnecting = False
                    self.append_message("[System Success] Reconnected to server successfully!")
                    
                    # Restart receiver thread
                    threading.Thread(target=self.receive_messages, daemon=True).start()
                    return
            except Exception:
                self.append_message(f"[System] Reconnect attempt {attempt}/{max_retries} failed...")

        self.is_reconnecting = False
        self.graceful_revert_to_login("Reconnection failed after multiple attempts.")





    def receive_messages(self):
        """Primary active socket receiver thread loop with auto -reconnection integration."""
        while True:
            try:
                data = self.sock.recv(4096)
                if not data:
                    if not self.is_reconnecting:
                        self.root.after(0,self.attempt_reconnect)
                    break
                
                decoded_data = data.decode('utf-8')
                
                # Check for critical System Administration messages
                if decoded_data.startswith("SYSTEM:TIMEOUT"):
                    reason = decoded_data.split(":", 2)[2] if len(decoded_data.split(":")) > 2 else "Session idle timeout."
                    self.root.after(0, lambda: self.graceful_revert_to_login(reason))
                    break
                    
                elif decoded_data.startswith("SYSTEM:LOGOUT"):
                    reason = decoded_data.split(":", 2)[2] if len(decoded_data.split(":")) > 2 else "Logged out safely."
                    self.root.after(0, lambda: self.graceful_revert_to_login(reason))
                    break
                    
                elif decoded_data.startswith("SYSTEM:ERROR"):
                    error_msg = decoded_data.split(" ", 1)[1] if " " in decoded_data else "Request rejected."
                    self.root.after(0, lambda: messagebox.showwarning("Security Restriction", error_msg))
                
                # Normal chat events
                elif decoded_data.startswith("JOIN:"):
                    new_user = decoded_data.split(":", 1)[1].strip()
                    self.root.after(0, lambda u=new_user: self.add_user_to_list(u))
                    self.root.after(0, lambda u=new_user: self.append_message(f"[System] {u} has connected safely."))
                    
                elif decoded_data.startswith("LEAVE:"):
                    leaving_user = decoded_data.split(":", 1)[1].strip()
                    self.root.after(0, lambda u=leaving_user: self.remove_user_from_list(u))
                    self.root.after(0, lambda u=leaving_user: self.append_message(f"[System] {u} has disconnected."))
                    
                elif decoded_data.startswith("USERLIST:"):
                    raw_users = decoded_data.split(":", 1)[1].strip()
                    users = raw_users.split(",") if raw_users else []
                    for u in users:
                        if u:
                            self.root.after(0, lambda user=u: self.add_user_to_list(user))
                            
                else:
                    self.root.after(0, lambda msg=decoded_data: self.append_message(msg))
                    
            except (ConnectionResetError,ConnectionAbortedError,socket.error):
                if not self.is_reconnecting:
                    self.root.after(0,self.attempt_reconnect)
                break
            except Exception:
                self.root.after(0,lambda:self.graceful_revert_to_login("System Link lost unexpectedly."))
         



if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClientGUI(root)
    root.mainloop()