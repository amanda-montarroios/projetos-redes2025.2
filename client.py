#!/usr/bin/env python3
import socket
import json
import argparse
import time

def calcular_checksum(texto):
    """Calcula um checksum simples somando os bytes do texto."""
    return sum(texto.encode('utf-8')) % 256

class Client:
    PACKET_PAYLOAD_SIZE = 4  # Cada pacote envia no maximo 4 caracteres

    def __init__(self, server_addr='127.0.0.1', server_port=5005, protocol='gbn', max_chars=30):
        self.server_addr = server_addr
        self.server_port = server_port
        self.protocol = protocol
        self.max_chars = min(max_chars, 30)  # máaimo de 30 caracteres
        self.session_id = None
        self.sequence_number_base = 0
        self.messages_sent = 0
        self.packets_sent = 0
        self.packets_confirmed = 0
        self.window_size = 5 # TAMANHO MAXIMO  do servidor)
        # self.cwnd (janela atual) inicializado dentro de connect()

    def send_packet(self, sock, payload, seq_num, total_packets, is_last):
        """Envia um pacote de dados segmentado para o servidor"""
        checksum = calcular_checksum(payload)
        message_packet = {
            'type': 'data',
            'session_id': self.session_id,
            'sequence': seq_num,
            'total_packets': total_packets,
            'is_last': is_last,
            'data': payload,
            'protocol': self.protocol,
            'timestamp': time.time(),
            'checksum': checksum
        }
        # Use newline framing so the server can split JSON messages reliably
        sock.sendall((json.dumps(message_packet) + "\n").encode('utf-8'))
        self.packets_sent += 1
        print(f"[CLIENTE] Pacote #{seq_num} ({self.protocol}) enviado: '{payload}' | Checksum: {checksum}")

    def receive_ack(self, sock):
        """Recebe confirmação do servidor para um pacote (SR) ou mensagem completa (GBN)"""
        try:
            sock.settimeout(5.0)
            data = sock.recv(2048)
            sock.settimeout(None)
            if not data:
                print("[CLIENTE] Socket fechado pelo servidor ao aguardar ACK.")
                return False

            # Support newline-framed JSON: take the first line that contains JSON
            try:
                text = data.decode('utf-8')
            except Exception as e:
                print(f"[CLIENTE] Erro ao decodificar bytes do ACK: {e}")
                return False

            # Some recv() calls may include multiple JSON objects; split and parse the first non-empty line
            lines = [l for l in text.split('\n') if l.strip()]
            if not lines:
                print("[CLIENTE] ACK recebido vazio ou inválido.")
                return False

            try:
                ack = json.loads(lines[0])
            except json.JSONDecodeError as e:
                print(f"[CLIENTE] Erro ao decodificar JSON do ACK: {e}")
                return False
            if ack.get('type') == 'ack':
                seq = ack.get('sequence')
                status = ack.get('status')
                valid = (status == 'ok') # True se status for 'ok'

                if valid:
                    self.packets_confirmed += 1
                    print(f"[CLIENTE] ACK recebido para pacote/mensagem #{seq} | Status OK? {valid}")
                else:
                    print(f"[CLIENTE] NACK recebido para pacote/mensagem #{seq}: {ack.get('message', 'Erro desconhecido')} | Status OK? {valid}")

                return valid
        except socket.timeout:
            print("[CLIENTE] Timeout! Servidor não respondeu ao ACK.")
            return False
        except Exception as e:
            print(f"[CLIENTE] Erro ao receber ACK: {e}")
            return False

        return False

    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.server_addr, self.server_port))
        print(f"\n{'='*60}")
        print(f"[CLIENTE] Conectado ao servidor {self.server_addr}:{self.server_port}")
        print(f"{'='*60}\n")

        # Handshake
        syn = {'protocol': self.protocol, 'max_chars': self.max_chars}
        sock.sendall((json.dumps(syn) + "\n").encode('utf-8'))
        print(f"[CLIENTE] SYN enviado: protocolo={self.protocol}, max_chars={self.max_chars}")

        data = sock.recv(1024)
        syn_ack = json.loads(data.decode('utf-8'))
        print(f"[CLIENTE] SYN-ACK recebido do servidor")
        self.session_id = syn_ack.get('session_id')
        self.max_chars = syn_ack.get('max_chars', self.max_chars)
        self.window_size = syn_ack.get('window_size', self.window_size)
        
        server_protocol = syn_ack.get('protocol', self.protocol)
        if server_protocol != self.protocol:
            print(f"[CLIENTE] Aviso: Protocolo negociado mudou para {server_protocol}.")
            self.protocol = server_protocol

        print(f"[CLIENTE] Session ID: {self.session_id}")
        print(f"[CLIENTE] Protocolo: {self.protocol}")
        print(f"[CLIENTE] Máximo de caracteres por mensagem: {self.max_chars}")
        print(f"[CLIENTE] Tamanho da janela: {self.window_size}")

        ack = {'session_id': self.session_id, 'message': 'Handshake completo'}
        sock.sendall((json.dumps(ack) + "\n").encode('utf-8'))
        print(f"[CLIENTE] ACK enviado. Handshake concluído!\n")
        print(f"{'='*60}\nPronto para enviar mensagens!\n{'='*60}")
        
        # !!Inicializa a janela atual (cwnd) AQUI !!
        self.cwnd = 1        # JANELA ATUAL (Slow Start), como na imagem

        while True:
            # estatistica de 'Confirmacoes (ACKs)' agora reflete o numero de ACKs recebidos (pacotes em SR, ou mensagens em GBN)
            print(f"\n[INFO] Mensagens enviadas: {self.messages_sent} | Confirmações (ACKs): {self.packets_confirmed}")
            mensagem = input(f"Digite uma mensagem (máx. {self.max_chars} chars) ou 'sair': ")

            if mensagem.lower() == 'sair':
                print("\n[CLIENTE] Encerrando conexão...")
                close_packet = {
                    'type': 'close',
                    'session_id': self.session_id,
                    'message': 'Cliente desconectando'
                }
                sock.sendall((json.dumps(close_packet) + "\n").encode('utf-8'))
                break

            if len(mensagem) == 0:
                print(f"[CLIENTE] Erro: mensagem vazia.")
                continue

            # Trunca mensagem acima do limite
            if len(mensagem) > self.max_chars:
                print(f"[CLIENTE] Aviso: mensagem cortada para {self.max_chars} caracteres.")
                mensagem = mensagem[:self.max_chars]

            # Segmenta a mensagem em pacotes
            chunks = [mensagem[i:i+self.PACKET_PAYLOAD_SIZE] for i in range(0, len(mensagem), self.PACKET_PAYLOAD_SIZE)]
            total_packets = len(chunks)
            print(f"[CLIENTE] Mensagem dividida em {total_packets} pacotes de {self.PACKET_PAYLOAD_SIZE} chars.")
            
            # logica GBN (Go-Back-N): Envia TUDO, espera 1 ACK final
            if self.protocol == 'gbn':
                for i, chunk in enumerate(chunks):
                    seq_num_to_send = self.sequence_number_base + i
                    is_last_packet = (i == total_packets - 1)
                    self.send_packet(sock, chunk, seq_num_to_send, total_packets, is_last_packet)

                # Espera a confirmacao final da mensagem
                ack_valido = self.receive_ack(sock) 
                
                if ack_valido:
                    print(f"[CLIENTE] Mensagem completa confirmada com sucesso (GBN)!")
                    self.messages_sent += 1
                else:
                    print(f"[CLIENTE] Erro no ACK final (GBN). Mensagem rejeitada pelo servidor.")

            # Lógica SR (Selective Repeat): AGORA COM JANELA DESLIZANTE (SLOW START)
            elif self.protocol == 'sr':
                base = 0 # O início da nossa janela (índice do chunk)
                pacotes_confirmados_nesta_msg = 0
                
                print(f"[CLIENTE] Iniciando envio SR para {total_packets} pacotes. CWND inicial: {self.cwnd}")

                while base < total_packets:
                    # 1. Determina quantos pacotes enviar
                    # A janela efetiva é o MENOR entre a sua janela atual (cwnd) e o máximo do servidor (window_size)
                    effective_window = min(self.cwnd, self.window_size)
                    
                    # Calcula quantos pacotes podemos enviar nesta rajada (sem passar do fim da mensagem)
                    packets_to_send = min(effective_window, total_packets - base)
                    
                    print(f"[CLIENTE] Enviando rajada de {packets_to_send} pacotes (Base: {base}, CWND: {self.cwnd}, Max: {self.window_size})")

                    # 2. Envia a rajada de pacotes (pipelining)
                    sent_seq_nums = [] # Guarda os números de sequência que enviamos
                    for i in range(packets_to_send):
                        chunk_index = base + i
                        chunk = chunks[chunk_index]
                        seq_num_to_send = self.sequence_number_base + chunk_index
                        is_last_packet = (chunk_index == total_packets - 1)
                        
                        self.send_packet(sock, chunk, seq_num_to_send, total_packets, is_last_packet)
                        sent_seq_nums.append(seq_num_to_send)

                    # 3. Aguarda os ACKs para essa rajada
                    # O seu servidor SR envia 1 ACK por pacote, então esperamos 'packets_to_send' ACKs
                    all_acks_ok = True
                    for i in range(packets_to_send):
                        # O receive_ack() vai bloquear esperando o próximo ACK
                        ack_valido = self.receive_ack(sock) 
                        
                        if not ack_valido:
                            print(f"[CLIENTE] Erro (NACK ou Timeout) no pacote {sent_seq_nums[i]}.")
                            all_acks_ok = False
                            break # Sai do loop de espera de ACK

                    # 4. Atualiza a janela (Avançar e Aumentar)
                    if all_acks_ok:
                        # Avança a base e AUMENTA a janela (slow start)
                        base += packets_to_send # Avança a janela
                        pacotes_confirmados_nesta_msg += packets_to_send
                        
                        # Aumenta a janela de congestão, até o limite do servidor de max 5
                        self.cwnd = min(self.cwnd + 1, self.window_size) 
                        print(f"[CLIENTE] Rajada confirmada. Avançando base para {base}. Aumentando CWND para {self.cwnd}")
                    else:
                        
                        print(f"[CLIENTE] Falha na rajada. Resetando CWND para 1 (validação de confiabilidade).")
                        self.cwnd = 1 # reseta a janela
                        break # Sai do 'while base < total_packets' e aborta esta mensagem

                # Fim do while loop
                if pacotes_confirmados_nesta_msg == total_packets:
                    print(f"[CLIENTE] Mensagem completa enviada e confirmada com sucesso (SR)!")
                    self.messages_sent += 1
                else:
                    print(f"[CLIENTE] Mensagem abortada devido a erro (SR).")
                
            self.sequence_number_base += total_packets

        # Estatísticas finais
        taxa_sucesso = (self.packets_confirmed/self.packets_sent*100) if self.packets_sent > 0 else 0
        
        print(f"\n{'='*60}")
        print("ESTATÍSTICAS DA SESSÃO:")
        print(f"  • Total de mensagens completas enviadas: {self.messages_sent}")
        print(f"  • Total de pacotes individuais enviados: {self.packets_sent}")
        print(f"  • Total de confirmações (ACKs) recebidas: {self.packets_confirmed} (Pacotes para SR, Mensagens para GBN)")
        print(f"  • Taxa de sucesso (ACKs/Pacotes): {taxa_sucesso:.1f}%")
        print(f"{'='*60}\n")

        sock.close()
        print("[CLIENTE] Conexão encerrada.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente de Transporte Confiável")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5005) # parser.add_action
    parser.add_argument("--max_chars", type=int, default=30)
    args = parser.parse_args()

    chosen_protocol = ""
    while True:
        chosen_protocol = input("Digite o protocolo a ser utilizado (gbn ou sr): ").lower().strip()
        if chosen_protocol in ['gbn', 'sr']:
            break
        else:
            print("Opção inválida. Digite 'gbn' ou 'sr'.")

    client = Client(args.host, args.port, chosen_protocol, args.max_chars)
    client.connect()
