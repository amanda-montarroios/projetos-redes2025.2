import socket
import json
import hashlib
import argparse

class Server:
    def __init__(self, host='127.0.0.1', port=5005, protocol='gbn', min_chars=30):
        self.host = host
        self.port = port
        self.protocol = protocol
        self.min_chars = min(min_chars, 30)
        self.client_sessions = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def handle_syn(self, client_socket, client_addr, data):
        print(f"[SERVIDOR] SYN recebido de {client_addr}: {data}")
        client_protocol = data.get('protocol', self.protocol)
        requested_min = min(data.get('min_chars', self.min_chars), 30)

        session_id = hashlib.md5(f"{client_addr}".encode()).hexdigest()[:8]

        self.client_sessions[client_addr] = {
            'protocol': client_protocol,
            'min_chars': requested_min,
            'session_id': session_id,
            'handshake_complete': False
        }

        syn_ack = {
            'status': 'ok',
            'protocol': client_protocol,
            'min_chars': requested_min,
            'session_id': session_id
        }

        client_socket.sendall(json.dumps(syn_ack).encode('utf-8'))
        return session_id

    def handle_ack(self, client_addr, data):
        print(f"[SERVIDOR] ACK recebido de {client_addr}: {data}")
        if client_addr in self.client_sessions:
            self.client_sessions[client_addr]['handshake_complete'] = True
            print(f"[SERVIDOR] Handshake concluído para {client_addr}")

    def start(self):
        print("[SERVIDOR] Servidor iniciado")
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"[SERVIDOR] Escutando em {self.host}:{self.port}")

        while True:
            try:
                client_socket, addr = self.sock.accept()
                client_addr = f"{addr[0]}:{addr[1]}"
                print(f"[SERVIDOR] Nova conexão de {client_addr}")

                # Passo 1: receber SYN
                data = client_socket.recv(1024)
                syn_data = json.loads(data.decode('utf-8'))
                self.handle_syn(client_socket, client_addr, syn_data)

                # Passo 2: receber ACK final
                data = client_socket.recv(1024)
                ack_data = json.loads(data.decode('utf-8'))
                self.handle_ack(client_addr, ack_data)

                while True:
                    msg = client_socket.recv(1024)
                    if not msg:
                        break
                    mensagem = msg.decode('utf-8')
                    print(f"[SERVIDOR] Mensagem recebida de {client_addr}: {mensagem}")

                    resposta = f"Recebido: {mensagem}"
                    client_socket.sendall(resposta.encode('utf-8'))

                client_socket.close()

            except KeyboardInterrupt:
                print("\n[SERVIDOR] Servidor finalizado pelo usuário")
                break
            except Exception as e:
                print(f"[SERVIDOR] Erro: {e}")

        self.sock.close()
        print("[SERVIDOR] Socket fechado")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Servidor Handshake TCP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5005)
    parser.add_argument("--protocol", choices=['gbn', 'sr'], default='gbn')
    parser.add_argument("--max-chars", type=int, default=30)
    args = parser.parse_args()

    server = Server(args.host, args.port, args.protocol, args.max_chars)
    server.start()
