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
        self.max_chars = min(max_chars, 30)  
        self.max_payload = max_payload       
        self.window_size = 5
        self.client_sessions = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def handle_syn(self, client_socket, client_addr, data):
        print(f"[SERVIDOR] SYN recebido de {client_addr}")
        protocol_requested = data.get('protocol', self.protocol) # Pega protocolo do cliente
        session_id = hashlib.md5(f"{client_addr}{time.time()}".encode()).hexdigest()[:8]
        self.client_sessions[client_addr] = {
            'session_id': session_id,
            'handshake_complete': False,
            'buffer': {},
            'packets_received': 0,
            'acks_sent': 0,
            'start_time': time.time(),
            'protocol': protocol_requested,  # Armazena o protocolo escolhido
            'corrupted': False              # Flag para rastrear corrupção na mensagem (para GBN)
        }
        syn_ack = {
            'status': 'ok',
            'protocol': protocol_requested,
            'max_chars': self.max_chars,
            'max_payload': self.max_payload,
            'window_size': self.window_size,
            'session_id': session_id
        }
        client_socket.sendall((json.dumps(syn_ack) + "\n").encode('utf-8'))
        print(f"[SERVIDOR] SYN-ACK enviado para {client_addr} (Session: {session_id}, Protocolo: {protocol_requested})")
        return session_id

    def handle_ack(self, client_addr, data):
        print(f"[SERVIDOR] ACK recebido de {client_addr}")
        if client_addr in self.client_sessions:
            self.client_sessions[client_addr]['handshake_complete'] = True
            print(f"[SERVIDOR] Handshake concluído para {client_addr}")

    def handle_data_message(self, client_socket, client_addr, message_data):
        session = self.client_sessions.get(client_addr)
        if not session:
            print(f"[SERVIDOR] Sessão não encontrada para {client_addr}")
            return False
        
        protocol = session.get('protocol', 'gbn')
        sequence = message_data.get('sequence', 0)
        data = message_data.get('data', '')
        checksum_recebido = message_data.get('checksum')
        checksum_calculado = calcular_checksum(data)
        is_last_packet = message_data.get('is_last', False)

        print(f"[SERVIDOR] Pacote #{sequence} ({protocol}) recebido de {client_addr}")
        print(f"Conteúdo: '{data}' | Tamanho: {len(data)}")
        print(f"Checksum enviado: {checksum_recebido} | Checksum calculado: {checksum_calculado}")

        # 1. Validação de Integridade (Checksum)
        if checksum_recebido != checksum_calculado:
            if protocol == 'sr': 
                nack = {'type':'ack','status':'error','sequence':sequence,
                        'message':'Erro de integridade detectado (SR)','timestamp':time.time()}
                client_socket.sendall((json.dumps(nack) + "\n").encode('utf-8'))
                session['acks_sent'] += 1
                print(f"[SERVIDOR] Pacote #{sequence} corrompido! → NACK (SR) enviado.\n")
                return False
            elif protocol == 'gbn':
                session['corrupted'] = True 
                print(f"[SERVIDOR] Pacote #{sequence} corrompido! (GBN) - Não enviando NACK imediato.\n")

        # 2. Validação de Tamanho de Carga Útil
        if len(data) > self.max_payload:
            if protocol == 'sr': 
                nack = {'type':'ack','status':'error','sequence':sequence,
                        'message':'Carga útil excede o máximo permitido (SR)','timestamp':time.time()}
                client_socket.sendall((json.dumps(nack) + "\n").encode('utf-8'))
                session['acks_sent'] += 1
                print(f"[SERVIDOR] Pacote #{sequence} inválido! Tamanho {len(data)} > máximo {self.max_payload} → NACK (SR) enviado.\n")
                return False
            elif protocol == 'gbn': 
                session['corrupted'] = True
                print(f"[SERVIDOR] Pacote #{sequence} inválido! (GBN) - Não enviando NACK imediato.\n")

        # 3. Processamento de Pacote Válido
        session['buffer'][sequence] = data
        session['packets_received'] += 1
        
        # SR: ACK por Pacote. GBN: Sem ACK
        if protocol == 'sr' and not session.get('corrupted', False):
            ack = {
                'type': 'ack',
                'status': 'ok',
                'sequence': sequence, 
                'message': 'Pacote recebido com sucesso (SR)',
                'timestamp': time.time()
            }
            client_socket.sendall((json.dumps(ack) + "\n").encode('utf-8'))
            session['acks_sent'] += 1
            print(f"[SERVIDOR] Pacote #{sequence} íntegro (SR) → ACK enviado.\n")
        elif protocol == 'gbn' and not session.get('corrupted', False):
            # No ACK for intermediate packets in GBN
            print(f"[SERVIDOR] Pacote #{sequence} íntegro (GBN) → NENHUM ACK enviado (aguardando final da mensagem).\n")

        # 4. Final da Mensagem
        if is_last_packet:
            full_message = ''.join(session['buffer'][i] for i in sorted(session['buffer']))
            is_message_corrupted = session.pop('corrupted', False) # Pega e remove a flag de corrupção
            
            print(f"\n{'='*30} MENSAGEM COMPLETA RECEBIDA {'='*30}")
            print(f"Cliente: {client_addr}")
            print(f"Mensagem: {full_message}")
            print(f"Total de pacotes: {len(session['buffer'])}")

            if protocol == 'gbn':
                # GBN: Envia ACK/NACK final
                if is_message_corrupted:
                    final_ack = {'type':'ack','status':'error','sequence':sequence,
                                 'message':'Mensagem rejeitada (GBN): Um ou mais pacotes estavam corrompidos/inválidos.',
                                 'echo': full_message, 'timestamp':time.time()}
                    print(f"[SERVIDOR] Mensagem completa rejeitada (GBN). NACK final enviado.")
                else:
                    final_ack = {'type':'ack','status':'ok','sequence':sequence, 
                                 'message':'Mensagem recebida com sucesso (GBN)','echo': full_message, 
                                 'timestamp':time.time()}
                    print(f"[SERVIDOR] Mensagem completa aceita (GBN). ACK final enviado.")
                
                client_socket.sendall((json.dumps(final_ack) + "\n").encode('utf-8'))
                session['acks_sent'] += 1
            
            elif protocol == 'sr':
                # SR: A confirmação de todos os pacotes já foi feita individualmente.
                # Apenas exibimos a mensagem completa.
                print(f"[SERVIDOR] Mensagem completa re-montada (SR). Confirmações já enviadas por pacote.")

            session['buffer'].clear()
            print(f"{'='*80}\n")

        return True


    def handle_close(self, client_addr, message_data):
        print(f"[SERVIDOR] Cliente {client_addr} solicitou encerramento ")
        if client_addr in self.client_sessions:
            session = self.client_sessions[client_addr]
            duration = time.time() - session['start_time']
            print(f"\n{'='*60}")
            print(f"ESTATÍSTICAS DA SESSÃO {session.get('session_id')}:")
            print(f" Cliente: {client_addr}")
            print(f" Protocolo: {session.get('protocol')}")
            print(f" Duração: {duration:.2f}s")
            print(f" Pacotes recebidos: {session.get('packets_received')}")
            print(f" ACKs enviados: {session.get('acks_sent')}")
            print(f"{'='*60}\n")
            del self.client_sessions[client_addr]
    
    def client_thread(self, client_socket, addr):
        client_addr = f"{addr[0]}:{addr[1]}"
        buffer = ''
        try:
            print(f"[SERVIDOR] Aguardando pacotes de {client_addr}...\n")
            while True:
                data = client_socket.recv(2048)
                if not data:
                    # conexão fechada pelo cliente
                    break
                buffer += data.decode('utf-8')

                # processar mensagens separadas por newline
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if not line.strip():
                        continue
                    try:
                        message_data = json.loads(line)
                    except json.JSONDecodeError as e:
                        print(f"[SERVIDOR] Erro ao decodificar JSON de {client_addr}: {e}")
                        continue

                    # Handshake SYN (cliente envia 'protocol' sem 'type')
                    if 'protocol' in message_data and 'type' not in message_data:
                        self.handle_syn(client_socket, client_addr, message_data)
                        continue

                    # Handshake ACK (cliente confirma handshake)
                    if 'session_id' in message_data and 'type' not in message_data:
                        self.handle_ack(client_addr, message_data)
                        continue

                    msg_type = message_data.get('type')
                    if msg_type == 'data':
                        self.handle_data_message(client_socket, client_addr, message_data)
                    elif msg_type == 'close':
                        self.handle_close(client_addr, message_data)
                        print(f"[SERVIDOR] Close recebido de {client_addr} — conexão encerrada.")
                        break
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