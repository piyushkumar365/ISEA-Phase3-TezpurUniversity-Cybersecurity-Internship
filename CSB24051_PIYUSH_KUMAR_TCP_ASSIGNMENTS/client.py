import socket
import time
import csv

SERVER_IP = "10.0.0.1"
PORT = 5000

MESSAGE_SIZES = [128, 512, 1024]
TOTAL_MESSAGES = 10

ROLL_NO = "CSB24051"
NAME = "Piyush Kumar"

result_rows = []
message_rows = []


# ======================================
# PERSISTENT MODE
# ======================================

print("\n========== PERSISTENT MODE ==========\n")

for size in MESSAGE_SIZES:

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    client.connect((SERVER_IP, PORT))

    total_time = 0
    total_bytes = 0

    print(f"\nMessage Size = {size}\n")

    for msg_id in range(1, TOTAL_MESSAGES + 1):

        payload = "P" + ("A" * (size - 1))

        message = f"{msg_id}|{size}|{payload}"

        start_time = time.time()

        client.send(message.encode())

        ack = client.recv(1024).decode()

        end_time = time.time()

        response_time = end_time - start_time

        total_time += response_time
        total_bytes += size

        print(
            f"{message}"
            f"RTT={response_time:.6f}"
        )

        message_rows.append([
            ROLL_NO,
            NAME,
            "persistent",
            size,
            msg_id,
            response_time
        ])

    client.close()

    average_time = total_time / TOTAL_MESSAGES

    throughput = total_bytes / total_time

    result_rows.append([
        ROLL_NO,
        NAME,
        "persistent",
        size,
        TOTAL_MESSAGES,
        average_time,
        throughput
    ])

    print(
        f"Average Response Time = {average_time:.6f}"
    )

    print(
        f"Throughput = {throughput:.2f} Bytes/sec"
    )


# ======================================
# NEW CONNECTION MODE
# ======================================

print("\n========== NEW CONNECTION MODE ==========\n")

for size in MESSAGE_SIZES:

    total_time = 0
    total_bytes = 0

    print(f"\nMessage Size = {size}\n")

    for msg_id in range(1, TOTAL_MESSAGES + 1):

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        client.connect((SERVER_IP, PORT))

        payload = "N" + ("A" * (size - 1))

        message = f"{msg_id}|{size}|{payload}"

        start_time = time.time()

        client.send(message.encode())

        ack = client.recv(1024).decode()

        end_time = time.time()

        client.close()

        response_time = end_time - start_time

        total_time += response_time
        total_bytes += size

        print(
            f"{message}"
            f"RTT={response_time:.6f}"
        )

        message_rows.append([
            ROLL_NO,
            NAME,
            "new_connection",
            size,
            msg_id,
            response_time
        ])

    average_time = total_time / TOTAL_MESSAGES

    throughput = total_bytes / total_time

    result_rows.append([
        ROLL_NO,
        NAME,
        "new_connection",
        size,
        TOTAL_MESSAGES,
        average_time,
        throughput
    ])

    print(
        f"Average Response Time = {average_time:.6f}"
    )

    print(
        f"Throughput = {throughput:.2f} Bytes/sec"
    )


# ======================================
# result_table.csv
# ======================================

with open("result_table.csv", "w", newline="") as file:

    writer = csv.writer(file)

    writer.writerow([
        "roll_no",
        "name",
        "mode",
        "message_size",
        "total_messages",
        "average_response_time",
        "throughput_bytes_per_sec"
    ])

    writer.writerows(result_rows)


# ======================================
# message_response_log.csv
# ======================================

with open("message_response_log.csv", "w", newline="") as file:

    writer = csv.writer(file)

    writer.writerow([
        "roll_no",
        "name",
        "mode",
        "message_size",
        "message_number",
        "response_time"
    ])

    writer.writerows(message_rows)

print("\nExperiment Completed\n")

