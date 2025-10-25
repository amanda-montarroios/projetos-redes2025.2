#!/usr/bin/env python3
import socket
import json
import hashlib
import time
import argparse
import threading

def calcular_checksum(texto):
    return sum(texto.encode('utf-8')) % 256

class Server:
    def __init__(self, host='127.0.0.1', port=5005, protocol='gbn', max_chars=30, max_payload=4):
        self.host = host
        self.port = port
        self.protocol = protocol
        self.max_chars = min(max_chars, 30)  # Máximo 30 caracteres
        self.max_payload = max_payload       # Pacotes de até 4 caracteres
        self.window_size = 5
        self.client_sessions = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def handle_syn(self, client_socket, client_addr, data):
        print(f"[SERVIDOR] SYN recebido de {client_addr}")
        session_id = hashlib.md5(f"{client_addr}{time.time()}".encode()).hexdigest()[:8]
        self.client_sessions[client_addr] = {
            'session_id': session_id,
            'handshake_complete': False,
            'buffer': {},
            'packets_received': 0,
            'acks_sent': 0,
            'start_time': time.time(),
        }
        syn_ack = {
            'status': 'ok',
            'protocol': self.protocol,
            'max_chars': self.max_chars,
            'max_payload': self.max_payload,
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
        session = self.client_sessions.get(client_addr)
        sequence = message_data.get('sequence', 0)
        data = message_data.get('data', '')
        checksum_recebido = message_data.get('checksum')
        checksum_calculado = calcular_checksum(data)

        if checksum_recebido != checksum_calculado:
            nack = {'type':'ack','status':'erro','sequence':sequence,
                    'message':'Erro de integridade detectado','timestamp':time.time()}
            client_socket.sendall(json.dumps(nack).encode('utf-8'))
            session['acks_sent'] += 1
            print(f"[SERVIDOR] Pacote #{sequence} corrompido!")
            return

        if len(data) > self.max_payload:
            nack = {'type':'ack','status':'erro','sequence':sequence,
                    'message':'Carga útil excede o máximo permitido','timestamp':time.time()}
            client_socket.sendall(json.dumps(nack).encode('utf-8'))
            session['acks_sent'] += 1
            print(f"[SERVIDOR] Pacote #{sequence} inválido! Tamanho {len(data)} > máximo {self.max_payload}.")
            return

        print(f"[SERVIDOR] Pacote #{sequence} recebido de {client_addr}")
        print(f"Conteúdo: '{data}' | Tamanho: {len(data)} | Timestamp: {message_data.get('timestamp')}")
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

        if message_data.get('is_last', False):
            full_message = ''.join(session['buffer'][i] for i in sorted(session['buffer']))
            print(f"\n{'='*30} MENSAGEM COMPLETA RECEBIDA {'='*30}")
            print(f"Cliente: {client_addr}")
            print(f"Mensagem: {full_message}")
            print(f"Total de pacotes: {len(session['buffer'])}")
            print(f"{'='*80}\n")
            session['buffer'].clear()

    def handle_close(self, client_addr, message_data):
        print(f"[SERVIDOR] Cliente {client_addr} solicitou encerramento ")
        if client_addr in self.client_sessions:
            session = self.client_sessions[client_addr]
            duration = time.time() - session['start_time']
            print(f"\n{'='*60}")
            print(f"ESTATÍSTICAS DA SESSÃO {session.get('session_id')}:")
            print(f" Cliente: {client_addr}")
            print(f" Duração: {duration:.2f}s")
            print(f" Pacotes recebidos: {session.get('packets_received')}")
            print(f" ACKs enviados: {session.get('acks_sent')}")
            print(f"{'='*60}\n")
    
    def client_thread(self, client_socket, addr):
        client_addr = f"{addr[0]}:{addr[1]}"
        try:
           
            data = client_socket.recv(1024)
            syn_data = json.loads(data.decode('utf-8'))
            self.handle_syn(client_socket, client_addr, syn_data)

            data = client_socket.recv(1024)
            ack_data = json.loads(data.decode('utf-8'))
            self.handle_ack(client_addr, ack_data)

            print(f"[SERVIDOR] Aguardando pacotes de {client_addr}...\n")

            while True:
                msg = client_socket.recv(2048)
                if not msg:
                    # Cliente parou de enviar dados, mas conexão permanece aberta
                    continue
                message_data = json.loads(msg.decode('utf-8'))
                msg_type = message_data.get('type')
                if msg_type == 'data':
                    self.handle_data_message(client_socket, client_addr, message_data)
                elif msg_type == 'close':
                    self.handle_close(client_addr, message_data)
                    print(f"[SERVIDOR] Close recebido de {client_addr} — sessão mantida.")
                    continue
                else:
                    print(f"[SERVIDOR] Tipo de mensagem desconhecido: {msg_type}")

        except Exception as e:
            print(f"[SERVIDOR] Erro na thread do cliente {client_addr}: {e}")
        finally:
            client_socket.close()
            print(f"[SERVIDOR] Conexão com {client_addr} encerrada\n")

    def start(self):
        print(f"\n{'='*60}")
        print("[SERVIDOR] Servidor iniciado")
        print(f"{'='*60}")
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"[SERVIDOR] Escutando em {self.host}:{self.port}")
        print(f"[SERVIDOR] Protocolo padrão: {self.protocol}")
        print(f"[SERVIDOR] Limite máximo da mensagem: {self.max_chars} caracteres")
        print(f"[SERVIDOR] Carga útil máxima por pacote: {self.max_payload} caracteres")
        print(f"[SERVIDOR] Tamanho da janela: {self.window_size}")
        print(f"{'='*60}\n")

        while True:
            try:
                client_socket, addr = self.sock.accept()
                thread = threading.Thread(target=self.client_thread, args=(client_socket, addr))
                thread.start()
                print(f"[SERVIDOR] Cliente {addr} atendido em uma nova thread.")
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
    parser.add_argument("--protocol", choices=['gbn','sr'], default='gbn')
    parser.add_argument("--max_chars", type=int, default=30)
    parser.add_argument("--max_payload", type=int, default=4)
    args = parser.parse_args()

    server = Server(args.host, args.port, args.protocol, args.max_chars, args.max_payload)
    server.start()
