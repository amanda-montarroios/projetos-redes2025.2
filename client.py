import socket
import json
import argparse
import time
import ssl
import hashlib
from cryptography.fernet import Fernet 
import base64

# =================================================================
# VARIÁVEIS DE SEGURANÇA E INTEGRIDADE
# =================================================================
# [REQUISITO: Criptografia simétrica] Chave simétrica de 32 bytes para Fernet (AES-128).
CHAVE_SIMETRICA_FERNET = b'9W24Lp_P9d51f2oM-rX3bE4uQ_G7hT8nS-yH0jK6mI4='

def calcular_checksum(texto):
    # [REQUISITO: Checksum] Calcula um hash SHA-1 do texto para verificação de integridade.
    return hashlib.sha1(texto.encode('utf-8')).hexdigest()

# =================================================================

class Client:
    # [REQUISITO: Segmentação] Define o tamanho máximo de carga útil do pacote.
    # PACKET_PAYLOAD_SIZE removido em favor de self.packet_size
    MAX_RETRIES = 3
    # [REQUISITO: Temporizador] Timeout para pacotes SR (2 segundos)
    SR_TIMEOUT = 2.0  

    def __init__(self, server_addr='127.0.0.1', server_port=5005, protocol='gbn', max_chars=30, window_size=5, use_ssl=False, packet_size=4):
        self.server_addr = server_addr
        self.server_port = server_port
        self.protocol = protocol
        self.max_chars = min(max_chars, 30)
        self.session_id = None
        # [REQUISITO: Número de sequência] Base para os números de sequência da mensagem atual.
        self.sequence_number_base = 0
        self.messages_sent = 0
        self.packets_sent = 0
        self.packets_confirmed = 0
        # [REQUISITO: Janela] Tamanho da janela de envio (para GBN e SR) - será negociado
        self.window_size = window_size
        self.packet_size = packet_size
        self.use_ssl = use_ssl
        # [REQUISITO: Simulação de erro/perda] Variáveis para injeção de falha.
        self.corrupt_packet_index = -1
        self.corrupt_message_seq = -1
        self.packet_loss_mode = False
        self.fernet = Fernet(CHAVE_SIMETRICA_FERNET)
        
        # Variáveis de Estado SR
        self.sr_window_base = 0           
        self.sr_next_seq_num = 0          
        self.sr_packet_states = {}        

    def send_packet(self, sock, payload, seq_num, total_packets, is_last):
        """Envia um pacote de dados segmentado, aplicando criptografia e injeção de erros."""
        
        # [REQUISITO: Checksum] Checksum sobre o dado ORIGINAL
        checksum = calcular_checksum(payload)
        
        # [REQUISITO: Simulação de erro/perda] Lógica de injeção de erro/perda/rejeição (lado do cliente)
        packet_index = seq_num - self.sequence_number_base 
        
        should_corrupt = (
            self.corrupt_message_seq == self.messages_sent and 
            packet_index == self.corrupt_packet_index and
            not self.packet_loss_mode
        )
        should_lose = (
            self.corrupt_message_seq == self.messages_sent and 
            packet_index == self.corrupt_packet_index and
            self.packet_loss_mode
        )

        if should_lose:
            print(f"[CLIENTE] !!! INJEÇÃO DE PERDA !!! Pacote #{seq_num} ({packet_index} na mensagem) NÃO ENVIADO.")
            # Desabilitar injeção após primeira perda para evitar loop infinito
            self.corrupt_message_seq = -2
            return True

        checksum_to_send = checksum
        if should_corrupt:
            checksum_to_send = hashlib.sha1(b'CORROMPIDO_Checksum_Invalido_' + str(seq_num).encode()).hexdigest()
            print(f"[CLIENTE] !!! INJEÇÃO DE ERRO !!! Pacote #{seq_num} ({packet_index} na mensagem) com Checksum alterado para {checksum_to_send}.")
            # Desabilitar injeção após primeira corrupção
            self.corrupt_message_seq = -2
        
        # [REQUISITO: Criptografia simétrica] Criptografia Simétrica (Fernet)
        payload_encriptado = self.fernet.encrypt(payload.encode('utf-8'))

        message_packet = {
            'type': 'data',
            'session_id': self.session_id,
            # [REQUISITO: Número de sequência] Inclui o número de sequência do pacote.
            'sequence': seq_num,
            'total_packets': total_packets,
            'is_last': is_last,
            'data': payload_encriptado.decode(),
            'protocol': self.protocol,
            # [REQUISITO: Checksum] Envia o checksum (corrompido ou original)
            'checksum': checksum_to_send 
        }

        sock.sendall((json.dumps(message_packet) + "\n").encode('utf-8'))
        self.packets_sent += 1
        print(f"[CLIENTE] Pacote #{seq_num} ({self.protocol}) enviado: '{payload}' | Checksum Original: {checksum}")

        # [REQUISITO: Temporizador] Inicia/reseta o temporizador ao enviar um pacote SR.
        if self.protocol == 'sr' and seq_num in self.sr_packet_states:
            self.sr_packet_states[seq_num]['sent'] = True
            self.sr_packet_states[seq_num]['timer'] = time.time()
            
        return True

    def receive_ack(self, sock):
        """Recebe ACK/NACK e gerencia timeouts."""
        # Configurar timeout baixo para checar se há ACKs pendentes
        try:
            sock.settimeout(0.1) 
            data = sock.recv(2048)
            sock.settimeout(None)
            if not data: return None

            text = data.decode('utf-8')
            lines = [l for l in text.split('\n') if l.strip()]
            if not lines: return None

            ack = json.loads(lines[0])
            if ack.get('type') == 'ack':
                seq = ack.get('sequence')
                status = ack.get('status')
                # [REQUISITO: ACK/NACK] Confirmação OK ou erro.
                if status == 'ok':
                    self.packets_confirmed += 1
                    print(f"[CLIENTE] ACK recebido para pacote/mensagem #{seq} | Status OK.")
                else:
                    print(f"[CLIENTE] NACK recebido para pacote/mensagem #{seq}: {ack.get('message', 'Erro desconhecido')}")
                return ack
        except socket.timeout:
            return {'status': 'timeout'}
        except Exception as e:
            print(f"[CLIENTE] Erro ao receber ACK: {e}")
            return None
        return None

    def connect(self):
        """Gerencia o handshake, o envio de mensagens e a retransmissão."""
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.use_ssl:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket(raw_sock, server_hostname=self.server_addr)
        else:
            sock = raw_sock
        
        sock.connect((self.server_addr, self.server_port))
        
        # [REQUISITO: Handshake] SYN - Cliente NÃO propõe janela, servidor decide
        syn = {
            'protocol': self.protocol, 
            'max_chars': self.max_chars,
            'packet_size': self.packet_size
            # window_size REMOVIDO - servidor decide sozinho
        }
        sock.sendall((json.dumps(syn) + "\n").encode('utf-8'))
        print(f"[CLIENTE] SYN enviado: protocolo={self.protocol}, max_chars={self.max_chars}, packet_size={self.packet_size}")
        
        data = sock.recv(1024)
        syn_ack = json.loads(data.decode('utf-8'))
        
        # [REQUISITO: Handshake] SYN-ACK Processamento
        self.session_id = syn_ack.get('session_id')
        self.max_chars = syn_ack.get('max_chars', self.max_chars)
        # [REQUISITO: Janela] Recebe o tamanho da janela NEGOCIADO pelo servidor (mínimo entre cliente e servidor)
        self.window_size = syn_ack.get('window_size', self.window_size)
        server_protocol = syn_ack.get('protocol', self.protocol)
        if server_protocol != self.protocol: self.protocol = server_protocol

        # [REQUISITO: Handshake] ACK final
        ack = {'session_id': self.session_id, 'message': 'Handshake completo'}
        sock.sendall((json.dumps(ack) + "\n").encode('utf-8'))
        print(f"[CLIENTE] SYN-ACK recebido do servidor")
        print(f"[CLIENTE] Session ID: {self.session_id}")
        print(f"[CLIENTE] Tamanho máximo de mensagem: {self.max_chars} caracteres")
        print(f"[CLIENTE] Tamanho da janela negociado: {self.window_size}")
        print(f"[CLIENTE] ACK enviado. Handshake concluído!")
        print(f"\n{'='*60}")
        print("Pronto para enviar mensagens!")
        print(f"{'='*60}\n")
        
        while True:
            print(f"\n[INFO] Mensagens enviadas: {self.messages_sent} | Confirmações (ACKs): {self.packets_confirmed}")
            
            # [REQUISITO: Simulação de erro/perda] Interação para definir a falha a ser injetada
            self.corrupt_packet_index = -1
            self.packet_loss_mode = False
            self.corrupt_message_seq = -1

            error_prompt = input("Deseja injetar falha na PRÓXIMA mensagem? ('c' - corromper / 'p' - perder / 'n' - normal): ").lower().strip()
            
            if error_prompt in ('c', 'p'):
                self.corrupt_message_seq = self.messages_sent 
                self.packet_loss_mode = (error_prompt == 'p')
                while True:
                    try:
                        idx = int(input(f"Qual o ÍNDICE do pacote na mensagem a {'PERDER' if self.packet_loss_mode else 'CORROMPER'}? (0, 1, 2...): "))
                        if idx >= 0:
                            self.corrupt_packet_index = idx
                            action = "Perda agendada" if self.packet_loss_mode else "Corrupção de Checksum agendada"
                            print(f"{action} para o pacote {idx} da próxima mensagem.")
                            break
                        else:
                            print("Índice deve ser >= 0.")
                    except ValueError:
                        print("Entrada inválida. Digite um número inteiro.")
            
            mensagem = input(f"Digite uma mensagem (máx. {self.max_chars} chars) ou 'sair': ")

            if mensagem.lower() == 'sair':
                close_packet = { 'type': 'close', 'session_id': self.session_id, 'message': 'Cliente desconectando' }
                sock.sendall((json.dumps(close_packet) + "\n").encode('utf-8'))
                break

            if len(mensagem) > self.max_chars:
                mensagem = mensagem[:self.max_chars]

            print(f"[DEBUG] Mensagem FINAL antes da segmentação ({len(mensagem)} chars): '{mensagem}'")
            # [REQUISITO: Segmentação] Divisão da mensagem em chunks (pacotes).
            chunks = [mensagem[i:i+self.packet_size] for i in range(0, len(mensagem), self.packet_size)]
            total_packets = len(chunks)
            
            # Inicialização para a mensagem atual (SR/GBN)
            self.sr_window_base = self.sequence_number_base
            self.sr_next_seq_num = self.sequence_number_base
            self.sr_packet_states.clear()
            
            # Preencher o estado inicial de todos os pacotes da mensagem (usado apenas por SR)
            for i, chunk in enumerate(chunks):
                seq_num = self.sequence_number_base + i
                self.sr_packet_states[seq_num] = {'sent': False, 'ack': False, 'data': chunk, 'timer': -1}

            # [REQUISITO: Retransmissão] Lógica de Retransmissão
            tentativas = 0
            mensagem_confirmada = False
            
            while tentativas < self.MAX_RETRIES and not mensagem_confirmada:
                
                if tentativas > 0:
                    print(f"\n[CLIENTE] >>> Tentativa de retransmissão #{tentativas + 1}...")
                    # Desativa a injeção de erro/perda nas retransmissões
                    self.corrupt_message_seq = -2 

                if self.protocol == 'gbn':
                    
                    # (Lógica GBN: Envia tudo na janela e espera ACK cumulativo)
                    for i, chunk in enumerate(chunks):
                        seq_num_to_send = self.sequence_number_base + i
                        is_last_packet = (i == total_packets - 1)
                        self.send_packet(sock, chunk, seq_num_to_send, total_packets, is_last_packet)

                    ack_response = self.receive_ack(sock) 
                    
                    if ack_response and ack_response.get('status') == 'ok':
                        mensagem_confirmada = True
                    else:
                        # [REQUISITO: Retransmissão] Se NACK ou Timeout em GBN, retransmite a mensagem inteira.
                        tentativas += 1

                elif self.protocol == 'sr':
                    
                    # CORREÇÃO: Loop baseado em tempo máximo ao invés de contagem fixa
                    max_sr_time = 30.0  # 30 segundos máximo para completar a mensagem
                    sr_start_time = time.time()
                    
                    while not mensagem_confirmada and (time.time() - sr_start_time) < max_sr_time:
                        packets_to_resend_now = False

                        # [REQUISITO: Temporizador] Reenviar pacotes expirados (SR)
                        current_time = time.time()
                        for seq, state in self.sr_packet_states.items():
                            if state['sent'] and not state['ack'] and state['timer'] != -1 and current_time - state['timer'] > self.SR_TIMEOUT:
                                packets_to_resend_now = True
                                state['sent'] = False # Marca para ser re-enviado

                        # [REQUISITO: Janela] Enviar novos e re-enviar pacotes dentro da janela
                        if packets_to_resend_now:
                            print(f"[CLIENTE] >>> Retransmitindo pacotes expirados/NACKed.")
                            
                        # Itera por todos os pacotes na janela que ainda não foram confirmados
                        for seq_num_to_send in range(self.sr_window_base, self.sequence_number_base + total_packets):
                            if seq_num_to_send in self.sr_packet_states:
                                packet_state = self.sr_packet_states[seq_num_to_send]
                                
                                # Se estiver na janela e não foi enviado (ou precisa ser re-enviado)
                                if seq_num_to_send < self.sr_window_base + self.window_size and not packet_state['sent']:
                                    
                                    is_last_packet = (seq_num_to_send == self.sequence_number_base + total_packets - 1)
                                    self.send_packet(sock, packet_state['data'], seq_num_to_send, total_packets, is_last_packet)
                                    
                                    if seq_num_to_send == self.sr_next_seq_num:
                                         self.sr_next_seq_num += 1


                        # [REQUISITO: ACK/NACK] Processar ACKs/NACKs recebidos
                        while True:
                            ack_response = self.receive_ack(sock) 
                            if not ack_response or ack_response.get('status') == 'timeout':
                                break 

                            seq = ack_response.get('sequence')
                            status = ack_response.get('status')
                            
                            if seq in self.sr_packet_states:
                                if status == 'ok':
                                    self.sr_packet_states[seq]['ack'] = True
                                    self.sr_packet_states[seq]['timer'] = -1 # Para o temporizador
                                elif status == 'error':
                                    # [REQUISITO: Retransmissão] NACK recebido (corrupção), forçar retransmissão seletiva imediata.
                                    self.sr_packet_states[seq]['timer'] = 0 
                                    self.sr_packet_states[seq]['sent'] = False
                                    print(f"[CLIENTE] NACK recebido para pacote #{seq}. Agendando retransmissão.")

                        # [REQUISITO: Janela] Avançar a base da janela (seletivamente)
                        while self.sr_window_base in self.sr_packet_states and self.sr_packet_states[self.sr_window_base]['ack']:
                            del self.sr_packet_states[self.sr_window_base]
                            self.sr_window_base += 1
                            
                        # 5. Checar se a mensagem foi completamente confirmada
                        if not self.sr_packet_states:
                            mensagem_confirmada = True
                            break 
                    
                    if not mensagem_confirmada:
                        tentativas += 1 
                        print(f"[CLIENTE] Timeout do SR (30s). Incrementando tentativas para {tentativas}.")

            if mensagem_confirmada:
                self.messages_sent += 1
                # [REQUISITO: Número de sequência] Atualiza a base para a próxima mensagem.
                self.sequence_number_base += total_packets
            else:
                print(f"[CLIENTE] Mensagem NÃO confirmada após {self.MAX_RETRIES} tentativas.")
                self.sequence_number_base += total_packets 

        taxa_sucesso = (self.packets_confirmed/self.packets_sent*100) if self.packets_sent > 0 else 0
        
        print(f"\n{'='*60}")
        print("ESTATÍSTICAS DA SESSÃO:")
        print(f"  • Total de mensagens completas enviadas: {self.messages_sent}")
        print(f"  • Total de pacotes individuais enviados: {self.packets_sent}")
        print(f"  • Total de confirmações (ACKs) recebidas: {self.packets_confirmed}")
        print(f"  • Taxa de sucesso (ACKs/Pacotes): {taxa_sucesso:.1f}%")
        print(f"{'='*60}\n")

        sock.close()
        print("[CLIENTE] Conexão encerrada.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente de Transporte Confiável")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5005) 
    parser.add_argument("--max_chars", type=int, default=30)
    parser.add_argument("--window_size", type=int, default=5, help="Tamanho da janela proposto (1-5)")
    parser.add_argument("--ssl", action='store_true', help="Ativar SSL/TLS (requer certificados)")
    args = parser.parse_args()

    # CORREÇÃO: Validação robusta da escolha do protocolo
    chosen_protocol = ""
    while chosen_protocol not in ['gbn', 'sr']:
        chosen_protocol = input("Digite o protocolo a ser utilizado (gbn ou sr): ").lower().strip()
        if chosen_protocol not in ['gbn', 'sr']:
            print("⚠️  Opção inválida. Digite 'gbn' ou 'sr'.")

    # Escolha do tamanho do pacote
    chosen_packet_size = 4
    while True:
        try:
            w_input = input("Qual o tamanho do pacote (4 a 8)? ").strip()
            val = int(w_input)
            if 4 <= val <= 8:
                chosen_packet_size = val
                break
            else:
                print("Tamanho inválido. Escolha um valor entre 4 e 8.")
        except ValueError:
            print("Entrada inválida. Digite um número inteiro.")

    use_ssl = args.ssl  # SSL desabilitado por padrão, use --ssl para ativar
    
    # Garantir que window_size esteja entre 1 e 5
    window_size = max(1, min(5, args.window_size))
    
    client = Client(args.host, args.port, chosen_protocol, args.max_chars, window_size, use_ssl, packet_size=chosen_packet_size)
    client.connect()
