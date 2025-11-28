import socket
import json
import hashlib
import time
import argparse
import threading
import ssl
from cryptography.fernet import Fernet 
import base64

# =================================================================
# VARIÁVEIS DE SEGURANÇA E INTEGRIDADE
# =================================================================
# Chave simétrica de 32 bytes para Fernet (AES-128).
CHAVE_SIMETRICA_FERNET = b'9W24Lp_P9d51f2oM-rX3bE4uQ_G7hT8nS-yH0jK6mI4='

def calcular_checksum(texto):
    """Calcula um hash SHA-1 do texto para verificação de integridade."""
    return hashlib.sha1(texto.encode('utf-8')).hexdigest()

# =================================================================

class Server:
    def __init__(self, host='127.0.0.1', port=5005, protocol='gbn', max_chars=30, max_payload=4, use_ssl=True):
        self.host = host
        self.port = port
        self.protocol = protocol
        self.max_chars = min(max_chars, 30)  
        self.max_payload = max_payload       
        self.window_size = 5
        self.use_ssl = use_ssl
        self.client_sessions = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.fernet = Fernet(CHAVE_SIMETRICA_FERNET)

    def handle_syn(self, client_socket, client_addr, data):
        session_id = hashlib.md5(f"{client_addr}{time.time()}".encode()).hexdigest()[:8]
        self.client_sessions[client_addr] = {
            'session_id': session_id,
            'handshake_complete': False,
            'buffer': {},               # Buffer para GBN (em ordem)
            'buffer_sr': {},            # Buffer para SR (fora de ordem)
            'packets_received': 0,
            'acks_sent': 0,
            'start_time': time.time(),
            'protocol': data.get('protocol', self.protocol),
            'corrupted': False,         # Estado de corrupção da mensagem atual (GBN)
            'expected_seq_num': 0,      # Próxima sequência esperada (base da janela SR/GBN)
            'total_packets_msg': 0      # Total de pacotes esperados para a mensagem
        }
        syn_ack = {
            'status': 'ok', 'protocol': self.client_sessions[client_addr]['protocol'],
            'max_chars': self.max_chars, 'max_payload': self.max_payload,
            'window_size': self.window_size, 'session_id': session_id
        }
        client_socket.sendall((json.dumps(syn_ack) + "\n").encode('utf-8'))
        print(f"[SERVIDOR] SYN-ACK enviado para {client_addr} (Session: {session_id}, Protocolo: {self.client_sessions[client_addr]['protocol']})")
        return session_id

    def handle_ack(self, client_addr, data):
        if client_addr in self.client_sessions:
            self.client_sessions[client_addr]['handshake_complete'] = True
            print(f"[SERVIDOR] Handshake concluído para {client_addr}")

    def handle_data_message(self, client_socket, client_addr, message_data):
        session = self.client_sessions.get(client_addr)
        if not session: return False
        
        protocol = session.get('protocol', 'gbn')
        sequence = message_data.get('sequence', 0)
        total_packets = message_data.get('total_packets', 0)
        data_encriptada_str = message_data.get('data', '')
        checksum_recebido = message_data.get('checksum')
        is_last_packet = message_data.get('is_last', False)
        
        # Resetar o estado da mensagem no início de uma nova mensagem/retransmissão
        if sequence == session['expected_seq_num'] and protocol == 'sr' and not session['buffer_sr']:
             session['corrupted'] = False
             session['total_packets_msg'] = total_packets
             print(f"[SERVIDOR] → Status e Total de Pacotes (SR) resetados para nova rajada.")
        elif sequence == session['expected_seq_num'] and protocol == 'gbn' and not session['buffer']:
             session['corrupted'] = False
             session['total_packets_msg'] = total_packets
             print(f"[SERVIDOR] → Status e Total de Pacotes (GBN) resetados para nova rajada.")

        data_desencriptada = None
        
        # 1. Descriptografia Simétrica (Fernet)
        try:
            data_encriptada_bytes = data_encriptada_str.encode('utf-8')
            data_desencriptada_bytes = self.fernet.decrypt(data_encriptada_bytes)
            data_desencriptada = data_desencriptada_bytes.decode('utf-8')
        except Exception as e:
            print(f"[SERVIDOR] ERRO FATAL: Falha ao descriptografar dado de {client_addr}. {e}")
            data_desencriptada = ""

        # 2. Checagem de Integridade (Checksum SHA-1)
        checksum_calculado = calcular_checksum(data_desencriptada)
        data = data_desencriptada

        print(f"[SERVIDOR] Pacote #{sequence} ({protocol}) recebido de {client_addr}")
        print(f"Conteúdo Desencriptado: '{data}' | Tamanho: {len(data)}")
        print(f"Checksum enviado: {checksum_recebido} | Checksum calculado: {checksum_calculado}")
        
        # Validação de Checksum/Integridade e Tamanho de Carga Útil
        is_corrupt_packet = (checksum_recebido != checksum_calculado) or (len(data) > self.max_payload)

        # 3. Processamento de Pacote
        
        if is_corrupt_packet:
            nack_msg = 'Falha: Integridade (SHA-1) ou Criptografia ou Carga Útil inválida.'
            
            if protocol == 'sr': 
                # NACK seletivo para o pacote corrupto
                nack = {'type':'ack','status':'error','sequence':sequence, 'message': nack_msg, 'timestamp':time.time()}
                client_socket.sendall((json.dumps(nack) + "\n").encode('utf-8'))
                session['acks_sent'] += 1
                print(f"[SERVIDOR] Pacote #{sequence} INVÁLIDO! → NACK (SR) enviado.\n")
            elif protocol == 'gbn': 
                # No GBN, qualquer erro no pacote esperado invalida o lote e o servidor não avança expected_seq_num
                session['corrupted'] = True
                print(f"[SERVIDOR] Pacote #{sequence} INVÁLIDO! (GBN) - Marcado para NACK final.")

            return False
            
        # Se o pacote é íntegro
        else:
            if protocol == 'gbn':
                # GBN: Só aceita pacotes em ordem
                if sequence == session['expected_seq_num']:
                    session['buffer'][sequence] = data
                    session['packets_received'] += 1
                    session['expected_seq_num'] += 1
                    print(f"[SERVIDOR] Pacote #{sequence} íntegro (GBN) → Aceito em ordem.")
                else:
                    # Pacote fora de ordem (duplicado ou à frente) - Descartar silenciosamente
                    session['corrupted'] = True # Força NACK final, pois algo deu errado.
                    print(f"[SERVIDOR] Pacote #{sequence} íntegro, mas FORA DE ORDEM (GBN) → Descartado e marcado para NACK final.")


            elif protocol == 'sr':
                # SR: Aceita pacotes dentro da janela
                window_size = self.window_size 
                base = session['expected_seq_num']
                
                if base <= sequence < base + window_size:
                    # Pacote está dentro da janela (inclusive se for a base)
                    if sequence not in session['buffer_sr']:
                        session['buffer_sr'][sequence] = data
                        session['packets_received'] += 1
                        
                        ack = {'type': 'ack', 'status': 'ok', 'sequence': sequence, 'message': 'Pacote recebido com sucesso (SR)', 'timestamp': time.time()}
                        client_socket.sendall((json.dumps(ack) + "\n").encode('utf-8'))
                        session['acks_sent'] += 1
                        print(f"[SERVIDOR] Pacote #{sequence} íntegro (SR) → ACK SELETIVO enviado.")

                    # Tenta avançar a base da janela (coletando pacotes bufferizados)
                    while session['expected_seq_num'] in session['buffer_sr']:
                        session['expected_seq_num'] += 1

                elif sequence < base:
                    # ACK para um pacote já recebido (duplicado)
                    ack = {'type': 'ack', 'status': 'ok', 'sequence': sequence, 'message': 'ACK duplicado enviado (SR)', 'timestamp': time.time()}
                    client_socket.sendall((json.dumps(ack) + "\n").encode('utf-8'))
                    session['acks_sent'] += 1
                    print(f"[SERVIDOR] Pacote #{sequence} DUPLICADO (SR) → ACK reenviado.")
                else:
                    # Pacote muito à frente da janela (descartado)
                    print(f"[SERVIDOR] Pacote #{sequence} muito à frente da janela SR (base: {base}, janela: {window_size}) - Descartado.")
                    return False


        # 4. Final da Mensagem

        # Condição de término SR: A base da janela (expected_seq_num) alcança o total de pacotes da mensagem.
        if session['expected_seq_num'] == session['total_packets_msg'] and protocol == 'sr' and session['total_packets_msg'] > 0:
            
            # Montar a mensagem completa a partir do buffer SR
            full_message = ''.join(session['buffer_sr'][i] for i in sorted(session['buffer_sr']))
            
            print(f"\n{'='*30} MENSAGEM COMPLETA RECEBIDA (SR) {'='*30}")
            print(f"Mensagem: {full_message}")
            print(f"[SERVIDOR] Mensagem completa re-montada (SR). Confirmações já enviadas por pacote.")
            
            session['buffer_sr'].clear()
            session['total_packets_msg'] = 0
            print(f"{'='*80}\n")
            
        # Condição de término GBN: O último pacote da rajada foi processado (e aceito em ordem)
        elif is_last_packet and protocol == 'gbn':
            
            full_message = ''.join(session['buffer'][i] for i in sorted(session['buffer']))
            is_message_corrupted = session.pop('corrupted', False)

            print(f"\n{'='*30} MENSAGEM COMPLETA RECEBIDA (GBN) {'='*30}")
            print(f"Mensagem: {full_message}")

            # ************************************************
            # CORREÇÃO APLICADA AQUI: Removida a checagem 'len(full_message) < self.max_chars' 
            # para aceitar mensagens curtas no GBN.
            # ************************************************
            if is_message_corrupted:
                status = 'error'
                msg = 'Mensagem rejeitada (GBN): Falha de integridade/criptografia ou Pacote Fora de Ordem.'
                print(f"[SERVIDOR] Mensagem completa rejeitada (GBN). NACK final enviado.")
            else:
                status = 'ok'
                msg = 'Mensagem recebida com sucesso (GBN)'
                print(f"[SERVIDOR] Mensagem completa aceita (GBN). ACK final enviado.")
            
            final_ack = {'type':'ack','status':status,'sequence':sequence, 'message': msg, 'echo': full_message, 'timestamp':time.time()}
            client_socket.sendall((json.dumps(final_ack) + "\n").encode('utf-8'))
            session['acks_sent'] += 1

            session['buffer'].clear()
            session['total_packets_msg'] = 0
            print(f"{'='*80}\n")

        return True

    def handle_close(self, client_addr, message_data):
        """Remove a sessão do cliente e exibe estatísticas."""
        if client_addr in self.client_sessions:
            session = self.client_sessions.pop(client_addr)
            duration = time.time() - session['start_time']
            print(f"\n--- Estatísticas da Sessão {session['session_id']} ---")
            print(f"Protocolo: {session['protocol']}")
            print(f"Pacotes Recebidos: {session['packets_received']}")
            print(f"ACKs/NACKs Enviados: {session['acks_sent']}")
            print(f"Duração: {duration:.2f} segundos")
            print("-" * 40)

    def client_thread(self, client_socket, addr):
        client_addr = f"{addr[0]}:{addr[1]}"
        buffer = ''
        try:
            print(f"[SERVIDOR] Aguardando pacotes de {client_addr}...\n")
            while True:
                data = client_socket.recv(2048)
                if not data:
                    break
                buffer += data.decode('utf-8')

                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if not line.strip():
                        continue
                    try:
                        message_data = json.loads(line)
                    except json.JSONDecodeError as e:
                        print(f"[SERVIDOR] Erro ao decodificar JSON de {client_addr}: {e}")
                        continue

                    if 'protocol' in message_data and 'type' not in message_data: self.handle_syn(client_socket, client_addr, message_data)
                    elif 'session_id' in message_data and 'message' in message_data and message_data['message'] == 'Handshake completo': self.handle_ack(client_addr, message_data)
                    elif message_data.get('type') == 'data': self.handle_data_message(client_socket, client_addr, message_data)
                    elif message_data.get('type') == 'close':
                        self.handle_close(client_addr, message_data)
                        print(f"[SERVIDOR] Close recebido de {client_addr} — conexão encerrada.")
                        return # Encerra a thread
                    else:
                        print(f"[SERVIDOR] Tipo de mensagem desconhecido: {message_data.get('type')}")

        except Exception as e:
            print(f"[SERVIDOR] Erro na thread do cliente {client_addr}: {e}")
        finally:
            client_socket.close()
            if client_addr in self.client_sessions:
                 self.handle_close(client_addr, {'type': 'close', 'message': 'Conexão interrompida'})
            print(f"[SERVIDOR] Conexão com {client_addr} encerrada\n")

    def start(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        
        print(f"\n{'='*60}")
        print("[SERVIDOR] Servidor iniciado")
        
        # Lógica SSL/TLS
        if self.use_ssl:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            try:
                # Certificados devem existir no diretório de execução
                context.load_cert_chain('server.crt', 'server.key') 
                self.sock = context.wrap_socket(self.sock, server_side=True)
                print("[SERVIDOR] SSL/TLS ativado (Criptografia de Transporte)")
            except FileNotFoundError:
                print("[SERVIDOR] ERRO: Arquivos 'server.crt' ou 'server.key' não encontrados. SSL desativado.")
                self.use_ssl = False

        print(f"[SERVIDOR] Escutando em {self.host}:{self.port}")
        print(f"[SERVIDOR] Protocolo padrão: {self.protocol}")
        print(f"[SERVIDOR] Limite: {self.max_chars} chars (msg) / {self.max_payload} chars (pacote)")
        print(f"[SERVIDOR] Checksum: SHA-1 | Criptografia: Fernet (AES-128)")
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
    parser.add_argument("--no-ssl", action='store_true')
    args = parser.parse_args()

    use_ssl = not args.no_ssl
    server = Server(args.host, args.port, args.protocol, args.max_chars, args.max_payload, use_ssl)
    server.start()