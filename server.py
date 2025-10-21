import socket
import json
import hashlib
import argparse
import time

class Server:
    def __init__(self, host='127.0.0.1', port=5005, protocol='gbn', max_text_size=30):
        self.host = host
        self.port = port
        self.protocol = protocol
        self.max_text_size = max(max_text_size, 30)
        self.window_size = 5
        self.client_sessions = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def handle_syn(self, client_socket, client_addr, data):
        print(f"[SERVIDOR] SYN recebido de {client_addr}")
        print(f" Protocolo solicitado: {data.get('protocol', 'N/A')}")
        print(f"Tamanho máximo do texto: {data.get('max_text_size', 'N/A')}")
        
        client_protocol = data.get('protocol', self.protocol)
        requested_max = max(data.get('max_text_size', self.max_text_size), 30)

        session_id = hashlib.md5(f"{client_addr}{time.time()}".encode()).hexdigest()[:8]

        self.client_sessions[client_addr] = {
            'protocol': client_protocol,
            'max_text_size': requested_max,
            'session_id': session_id,
            'handshake_complete': False,
            'packets_received': 0,
            'acks_sent': 0,       
            'start_time': time.time(),
            'buffer': {} 
        }

        syn_ack = {
            'status': 'ok',
            'protocol': client_protocol,
            'max_text_size': requested_max, 
            'window_size': self.window_size, 
            'session_id': session_id
        }

        client_socket.sendall(json.dumps(syn_ack).encode('utf-8'))
        print(f"[SERVIDOR] SYN-ACK enviado para {client_addr} (Session: {session_id})")
        return session_id

    def handle_ack(self, client_addr, data):
        print(f"[SERVIDOR] ACK recebido de {client_addr}")
        if client_addr in self.client_sessions:
            self.client_sessions[client_addr]['handshake_complete'] = True
            print(f"[SERVIDOR] Handshake concluído para {client_addr}")

    def handle_data_message(self, client_socket, client_addr, message_data):
        """Processa um pacote de dados do cliente"""
        session = self.client_sessions.get(client_addr, {})
        
        sequence = message_data.get('sequence', 0)
        data = message_data.get('data', '')
        is_last = message_data.get('is_last', False)
        total_packets = message_data.get('total_packets', 0)
        
        print(f"\n[SERVIDOR] Pacote #{sequence} recebido de {client_addr}")
        print(f"Conteúdo: '{data}'")
        print(f"Total de pacotes: {total_packets}")
        print(f"É o último: {is_last}")

        session['buffer'][sequence] = data
        session['packets_received'] += 1
 
        ack = {
            'type': 'ack',
            'status': 'ok',
            'sequence': sequence, 
            'message': 'Pacote recebido com sucesso',
            'timestamp': time.time()
        }
        
        client_socket.sendall(json.dumps(ack).encode('utf-8'))
        session['acks_sent'] += 1
        print(f"[SERVIDOR] ACK enviado para pacote #{sequence}")
        
        if is_last:
            print(f"[SERVIDOR] Recebido último pacote (seq={sequence}). Tentando remontar...")
            
            full_message = ""
            missing = False
            base_seq_num = sequence - (total_packets - 1)
            
            for i in range(total_packets):
                current_seq_check = base_seq_num + i
                if current_seq_check not in session['buffer']:
                    print(f"[SERVIDOR] Erro! Faltando pacote #{current_seq_check} para remontar.")
                    missing = True
                    break
                full_message += session['buffer'][current_seq_check]
            
            if not missing:
                print(f"\n{'='*30} MENSAGEM COMPLETA RECEBIDA {'='*30}")
                print(f"Cliente: {client_addr}")
                print(f"Mensagem: {full_message}")
                print(f"Total de Pacotes: {total_packets}")
                print(f"{'='*80}\n")

                for i in range(total_packets):
                    del session['buffer'][base_seq_num + i]
                    
            else:
                print("[SERVIDOR] Não foi possível remontar a mensagem.")

    def handle_close(self, client_addr, message_data):
        """Processa mensagem de encerramento"""
        print(f"\n[SERVIDOR] Cliente {client_addr} solicitou encerramento")
        
        if client_addr in self.client_sessions:
            session = self.client_sessions[client_addr]
            duration = time.time() - session.get('start_time', 0)
            
            print(f"\n{'='*60}")
            print(f"ESTATÍSTICAS DA SESSÃO {session.get('session_id', 'N/A')}:")
            print(f" Cliente: {client_addr}")
            print(f" Protocolo: {session.get('protocol', 'N/A')}")
            print(f" Duração: {duration:.2f} segundos")
            print(f" Pacotes recebidos: {session.get('packets_received', 0)}")
            print(f" ACKs enviados: {session.get('acks_sent', 0)}")
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
        print(f"[SERVIDOR] Tamanho MÁXIMO de mensagem: {self.max_text_size} caracteres")
        print(f"[SERVIDOR] Tamanho da Janela: {self.window_size}")
        print(f"{'='*60}\n")

        while True:
            try:
                client_socket, addr = self.sock.accept()
                client_addr = f"{addr[0]}:{addr[1]}"
                print(f"\n{'='*60}")
                print(f"[SERVIDOR] Nova conexão de {client_addr}")
                print(f"{'='*60}")

                data = client_socket.recv(1024)
                syn_data = json.loads(data.decode('utf-8'))
                self.handle_syn(client_socket, client_addr, syn_data)

                data = client_socket.recv(1024)
                ack_data = json.loads(data.decode('utf-8'))
                self.handle_ack(client_addr, ack_data)

                print(f"\n[SERVIDOR] Aguardando pacotes de {client_addr}...\n")

                while True:
                    msg = client_socket.recv(2048)
                    if not msg:
                        print(f"[SERVIDOR] Conexão fechada por {client_addr}")
                        if client_addr in self.client_sessions:
                             del self.client_sessions[client_addr]
                        break
                    
                    try:
                        message_data = json.loads(msg.decode('utf-8'))
                        msg_type = message_data.get('type', 'unknown')
                        
                        if self.client_sessions.get(client_addr, {}).get('session_id') != message_data.get('session_id'):
                            print(f"[SERVIDOR] ID de sessão inválido de {client_addr}. Ignorando...")
                            continue

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
    parser = argparse.ArgumentParser(description="Servidor de Transporte Confiável")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5005)
    parser.add_argument("--protocol", choices=['gbn', 'sr'], default='gbn')
    parser.add_argument("--max-text-size", type=int, default=30)
    args = parser.parse_args()

    server = Server(args.host, args.port, args.protocol, args.max_text_size)
    server.start()