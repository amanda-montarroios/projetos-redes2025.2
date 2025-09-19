import socket
import json
import argparse

class Client:
    def __init__(self, server_addr='127.0.0.1', server_port=5005, protocol='gbn', max_chars=30):
        self.server_addr = server_addr
        self.server_port = server_port
        self.protocol = protocol
        self.max_chars = max_chars
        self.session_id = None

    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.server_addr, self.server_port))
        print(f"[CLIENTE] Conectado ao servidor {self.server_addr}:{self.server_port}")

        # Passo 1: enviar SYN
        syn = {'protocol': self.protocol, 'max_chars': self.max_chars}
        sock.sendall(json.dumps(syn).encode('utf-8'))
        print(f"[CLIENTE] SYN enviado: {syn}")

        # Passo 2: receber SYN-ACK
        data = sock.recv(1024)
        syn_ack = json.loads(data.decode('utf-8'))
        print(f"[CLIENTE] SYN-ACK recebido: {syn_ack}")
        self.session_id = syn_ack.get('session_id')

        # Passo 3: enviar ACK final
        ack = {'session_id': self.session_id, 'message': 'Handshake completo'}
        sock.sendall(json.dumps(ack).encode('utf-8'))
        print(f"[CLIENTE] ACK enviado. Handshake concluído. Session={self.session_id}")

        sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente Handshake TCP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5005)
    parser.add_argument("--protocol", choices=['gbn', 'sr'], default='gbn')
    parser.add_argument("--max-chars", type=int, default=30)
    args = parser.parse_args()

    client = Client(args.host, args.port, args.protocol, args.max_chars)
    client.connect()
