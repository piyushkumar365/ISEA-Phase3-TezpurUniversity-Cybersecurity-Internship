import socket
import datetime

HOST = "10.0.0.1"
PORT = 5000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(5)

print(f"Server listening on {HOST}:{PORT}")

while True:

    conn, addr = server.accept()

    print(f"Connected by {addr}")

    while True:

        try:
            data = conn.recv(4096)

            if not data:
                break

            message = data.decode()

            # MSG_ID|MESSAGE_SIZE|MESSAGE_DATA
            msg_id, msg_size, msg_data = message.split("|", 2)

            if msg_data.startswith("P"):
                mode = "persistent"
            else:
                mode = "new_connection"

            received_size = int(msg_size)

            ack = f"ACK|{msg_id}|{received_size}"

            conn.send(ack.encode())

            timestamp = datetime.datetime.now()

            with open("server_log.txt", "a") as log:

                log.write(
                    f"{timestamp},"
                    f"{addr[0]},"
                    f"{mode},"
                    f"{msg_id},"
                    f"{received_size},"
                    f"YES\n"
                )

            print(
                f"Mode={mode} "
                f"{ack}"
            )

        except:
            break

    conn.close()

