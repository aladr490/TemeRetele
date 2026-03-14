import socket
import threading

HOST = "127.0.0.1"
PORT = 3333
BUFFER_SIZE = 1024


class State:
    def __init__(self):
        self.data = {}
        self.lock = threading.Lock()

    def add(self, key, value):
        with self.lock:
            self.data[key] = value
        return "OK record add"

    def get(self, key):
        with self.lock:
            if key in self.data:
                return f"DATA {self.data[key]}"
            return "ERROR invalid key"

    def remove(self, key):
        with self.lock:
            if key in self.data:
                del self.data[key]
                return "OK value deleted"
            return "ERROR invalid key"

    def list_all(self):
        with self.lock:
            if not self.data:
                return "DATA |"
            items = ",".join([f"{k}={v}" for k, v in self.data.items()])
            return f"DATA |{items}"

    def count(self):
        with self.lock:
            return f"DATA {len(self.data)}"

    def clear(self):
        with self.lock:
            self.data.clear()
        return "OK all data deleted"

    def update(self, key, value):
        with self.lock:
            if key in self.data:
                self.data[key] = value
                return "OK data updated"
            return "ERROR invalid key"

    def pop(self, key):
        with self.lock:
            if key in self.data:
                value = self.data.pop(key)
                return f"DATA {value}"
            return "ERROR invalid key"


state = State()


def process_command(command):

    parts = command.split()

    if not parts:
        return "ERROR empty command"

    cmd = parts[0].upper()

    if cmd == "ADD":
        if len(parts) < 3:
            return "ERROR invalid parameters"
        key = parts[1]
        value = " ".join(parts[2:])
        return state.add(key, value)

    elif cmd == "GET":
        if len(parts) != 2:
            return "ERROR invalid parameters"
        return state.get(parts[1])

    elif cmd == "REMOVE":
        if len(parts) != 2:
            return "ERROR invalid parameters"
        return state.remove(parts[1])

    elif cmd == "LIST":
        return state.list_all()

    elif cmd == "COUNT":
        return state.count()

    elif cmd == "CLEAR":
        return state.clear()

    elif cmd == "UPDATE":
        if len(parts) < 3:
            return "ERROR invalid parameters"
        key = parts[1]
        value = " ".join(parts[2:])
        return state.update(key, value)

    elif cmd == "POP":
        if len(parts) != 2:
            return "ERROR invalid parameters"
        return state.pop(parts[1])

    elif cmd == "QUIT":
        return "OK connection closed"

    else:
        return "ERROR unknown command"


def handle_client(client_socket):

    with client_socket:

        while True:

            try:

                data = client_socket.recv(BUFFER_SIZE)

                if not data:
                    break

                command = data.decode("utf-8").strip()

                response = process_command(command)

                response_data = f"{len(response)} {response}".encode("utf-8")

                client_socket.sendall(response_data)

                if command.upper() == "QUIT":
                    break

            except Exception as e:

                error_msg = f"ERROR {str(e)}"
                response_data = f"{len(error_msg)} {error_msg}".encode("utf-8")

                client_socket.sendall(response_data)

                break


def start_server():

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:

        server_socket.bind((HOST, PORT))

        server_socket.listen()

        print(f"[SERVER] Listening on {HOST}:{PORT}")

        while True:

            client_socket, addr = server_socket.accept()

            print(f"[SERVER] Connection from {addr}")

            thread = threading.Thread(
                target=handle_client,
                args=(client_socket,)
            )

            thread.start()


if __name__ == "__main__":
    start_server()