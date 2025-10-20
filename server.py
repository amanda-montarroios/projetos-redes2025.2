import socket
import json
import hashlib
import argparse
import time

class Server:
    def __init__(self, host='127.0.0.1', port=5005, protocol='gbn', min_chars=5):
        self.host = host
        self.port = port
        self.protocol = protocol
        self.min_chars = min(min_chars, 5)
        self.client_sessions = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def handle_syn(self, client_socket, client_addr, data):
        print(f"[SERVIDOR] SYN recebido de {client_addr}")
        print(f"           Protocolo solicitado: {data.get('protocol', 'N/A')}")
        print(f"           Min chars solicitado: {data.get('min_chars', 'N/A')}")
        
        client_protocol = data.get('protocol', self.protocol)
        requested_min = min(data.get('min_chars', self.min_chars), 5)

        session_id = hashlib.md5(f"{client_addr}".encode()).hexdigest()[:8]

        self.client_sessions[client_addr] = {
            'protocol': client_protocol,
            'min_chars': requested_min,
            'session_id': session_id,
            'handshake_complete': False,
            'messages_received': 0,
            'messages_sent': 0,
            'start_time': time.time()
        }

        syn_ack = {
            'status': 'ok',
            'protocol': client_protocol,
            'min_chars': requested_min,
            'session_id': session_id
        }

        client_socket.sendall(json.dumps(syn_ack).encode('utf-8'))
        print(f"[SERVIDOR] SYN-ACK enviado para {client_addr} (Session: {session_id})")
        return session_id

    def handle_ack(self, client_addr, data):
        print(f"[SERVIDOR] ACK recebido de {client_addr}")
        if client_addr in self.client_sessions:
            self.client_sessions[client_addr]['handshake_complete'] = True
            print(f"[SERVIDOR] ✓ Handshake concluído para {client_addr}")

    def handle_data_message(self, client_socket, client_addr, message_data):
        """Processa mensagem de dados do cliente"""
        session = self.client_sessions.get(client_addr, {})
        min_chars = session.get('min_chars', self.min_chars)
        
        sequence = message_data.get('sequence', 0)
        data = message_data.get('data', '')
        
        print(f"\n[SERVIDOR] Mensagem #{sequence} recebida de {client_addr}")
        print(f"           Conteúdo: '{data}'")
        print(f"           Tamanho: {len(data)} caracteres")
        
        # Validar tamanho mínimo
        if len(data) < min_chars:
            # Enviar NACK
            nack = {
                'type': 'ack',
                'status': 'error',
                'sequence': sequence,
                'message': f'Mensagem muito curta. Mínimo: {min_chars} caracteres',
                'timestamp': time.time()
            }
            client_socket.sendall(json.dumps(nack).encode('utf-8'))
            print(f"[SERVIDOR] ✗ NACK enviado para mensagem #{sequence}")
            return
        
        # Mensagem válida - enviar ACK
        session['messages_received'] += 1
        
        ack = {
            'type': 'ack',
            'status': 'ok',
            'sequence': sequence,
            'echo': data,
            'message': 'Mensagem recebida com sucesso',
            'timestamp': time.time()
        }
        
        client_socket.sendall(json.dumps(ack).encode('utf-8'))
        session['messages_sent'] += 1
        print(f"[SERVIDOR] ✓ ACK enviado para mensagem #{sequence}")

    def handle_close(self, client_addr, message_data):
        """Processa mensagem de encerramento"""
        print(f"\n[SERVIDOR] Cliente {client_addr} solicitou encerramento")
        
        if client_addr in self.client_sessions:
            session = self.client_sessions[client_addr]
            duration = time.time() - session.get('start_time', 0)
            
            print(f"\n{'='*60}")
            print(f"ESTATÍSTICAS DA SESSÃO {session.get('session_id', 'N/A')}:")
            print(f"  • Cliente: {client_addr}")
            print(f"  • Protocolo: {session.get('protocol', 'N/A')}")
            print(f"  • Duração: {duration:.2f} segundos")
            print(f"  • Mensagens recebidas: {session.get('messages_received', 0)}")
            print(f"  • ACKs enviados: {session.get('messages_sent', 0)}")
            print(f"{'='*60}\n")
            
            del self.client_sessions[client_addr]

    def start(self):
        print(f"\n{'='*60}")
        print("[SERVIDOR] Servidor iniciado")
        print(f"{'='*60}")
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"[SERVIDOR] Escutando em {self.host}:{self.port}")
        print(f"[SERVIDOR] Protocolo padrão: {self.protocol}")
        print(f"[SERVIDOR] Tamanho mínimo de mensagem: {self.min_chars} caracteres")
        print(f"{'='*60}\n")

        while True:
            try:
                client_socket, addr = self.sock.accept()
                client_addr = f"{addr[0]}:{addr[1]}"
                print(f"\n{'='*60}")
                print(f"[SERVIDOR] Nova conexão de {client_addr}")
                print(f"{'='*60}")

                # Passo 1: receber SYN
                data = client_socket.recv(1024)
                syn_data = json.loads(data.decode('utf-8'))
                self.handle_syn(client_socket, client_addr, syn_data)

                # Passo 2: receber ACK final
                data = client_socket.recv(1024)
                ack_data = json.loads(data.decode('utf-8'))
                self.handle_ack(client_addr, ack_data)

                print(f"\n[SERVIDOR] Aguardando mensagens de {client_addr}...\n")

                # Loop de recebimento de mensagens
                while True:
                    msg = client_socket.recv(2048)
                    if not msg:
                        print(f"[SERVIDOR] Conexão fechada por {client_addr}")
                        break
                    
                    try:
                        message_data = json.loads(msg.decode('utf-8'))
                        msg_type = message_data.get('type', 'unknown')
                        
                        if msg_type == 'data':
                            self.handle_data_message(client_socket, client_addr, message_data)
                        elif msg_type == 'close':
                            self.handle_close(client_addr, message_data)
                            break
                        else:
                            print(f"[SERVIDOR] Tipo de mensagem desconhecido: {msg_type}")
                    
                    except json.JSONDecodeError:
                        print(f"[SERVIDOR] Erro ao decodificar mensagem de {client_addr}")
                    except Exception as e:
                        print(f"[SERVIDOR] Erro ao processar mensagem: {e}")

                client_socket.close()
                print(f"[SERVIDOR] Conexão com {client_addr} encerrada\n")

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
