import socket
import json
import argparse
import time
import math

class Client:
    
    PACKET_PAYLOAD_SIZE = 4

    def __init__(self, server_addr='127.0.0.1', server_port=5005, protocol='gbn', max_text_size=30):
        self.server_addr = server_addr
        self.server_port = server_port
        self.protocol = protocol
        self.max_text_size = max(max_text_size, 30) 
        self.session_id = None
        self.sequence_number_base = 0 
        self.messages_sent = 0        
        self.packets_sent = 0         
        self.packets_confirmed = 0    
        self.window_size = 5         

    def send_packet(self, sock, payload, seq_num, total_packets, is_last):
        """Envia um pacote de dados segmentado para o servidor"""
        message_packet = {
            'type': 'data',
            'session_id': self.session_id,
            'sequence': seq_num,
            'total_packets': total_packets, 
            'is_last': is_last,            
            'data': payload,               
            'protocol': self.protocol,
            'timestamp': time.time()
        }
        
        sock.sendall(json.dumps(message_packet).encode('utf-8'))
        self.packets_sent += 1
        print(f"[CLIENTE] Pacote #{seq_num} (de {total_packets-1}) enviado: '{payload}'")

    def receive_ack(self, sock):
        """Recebe confirmação do servidor para um pacote"""
        try:
            sock.settimeout(5.0) 
            data = sock.recv(2048)
            sock.settimeout(None) 
            
            ack = json.loads(data.decode('utf-8'))
            
            if ack.get('type') == 'ack':
                seq = ack.get('sequence')
                status = ack.get('status')
                
                if status == 'ok':
                    self.packets_confirmed += 1
                    print(f"[CLIENTE] ACK recebido para pacote #{seq}")
                else:
                    print(f"[CLIENTE] NACK recebido para pacote #{seq}: {ack.get('message', 'Erro desconhecido')}")
                
                return ack
        except socket.timeout:
            print("[CLIENTE] Timeout! Servidor não respondeu ao ACK.")
            return None
        except Exception as e:
            print(f"[CLIENTE] Erro ao receber ACK: {e}")
            return None
        
        return None

    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.server_addr, self.server_port))
        print(f"\n{'='*60}")
        print(f"[CLIENTE] Conectado ao servidor {self.server_addr}:{self.server_port}")
        print(f"{'='*60}\n")

        syn = {'protocol': self.protocol, 'max_text_size': self.max_text_size}
        sock.sendall(json.dumps(syn).encode('utf-8'))
        print(f"[CLIENTE] SYN enviado: protocolo={self.protocol}, max_text_size={self.max_text_size}")

        data = sock.recv(1024)
        syn_ack = json.loads(data.decode('utf-8'))
        print(f"[CLIENTE] SYN-ACK recebido do servidor")
        self.session_id = syn_ack.get('session_id')
        self.max_text_size = syn_ack.get('max_text_size', self.max_text_size)
        self.window_size = syn_ack.get('window_size', self.window_size)
        
        print(f"[CLIENTE] Session ID: {self.session_id}")
        print(f"[CLIENTE] Tamanho máximo da mensagem: {self.max_text_size} caracteres")
        print(f"[CLIENTE] Tamanho da janela: {self.window_size}")


        ack = {'session_id': self.session_id, 'message': 'Handshake completo'}
        sock.sendall(json.dumps(ack).encode('utf-8'))
        print(f"[CLIENTE] ACK enviado. Handshake concluído!")
        print(f"\n{'='*60}")
        print("Pronto para enviar mensagens!")
        print(f"{'='*60}\n")

        while True:
            print(f"\n[INFO] Mensagens enviadas: {self.messages_sent} | Pacotes confirmados: {self.packets_confirmed}")
            mensagem = input(f"Digite uma mensagem (máx. {self.max_text_size} chars) ou 'sair': ")
            
            if mensagem.lower() == 'sair':
                print("\n[CLIENTE] Encerrando conexão...")
                close_packet = {
                    'type': 'close',
                    'session_id': self.session_id,
                    'message': 'Cliente desconectando'
                }
                sock.sendall(json.dumps(close_packet).encode('utf-8'))
                break
            
            if len(mensagem) > self.max_text_size:
                print(f"[CLIENTE] Erro: Mensagem muito longa! Máximo: {self.max_text_size} caracteres, atual: {len(mensagem)}")
                continue
            
            if len(mensagem) == 0:
                print(f"[CLIENTE] Erro: Mensagem vazia.")
                continue

            chunks = [mensagem[i:i+self.PACKET_PAYLOAD_SIZE] for i in range(0, len(mensagem), self.PACKET_PAYLOAD_SIZE)]
            total_packets = len(chunks)
            print(f"[CLIENTE] Mensagem dividida em {total_packets} pacotes de {self.PACKET_PAYLOAD_SIZE} chars.")
            
            pacotes_enviados_nesta_msg = 0
            
            for i, chunk in enumerate(chunks):
                seq_num_to_send = self.sequence_number_base + i
                is_last_packet = (i == total_packets - 1)
                
                self.send_packet(sock, chunk, seq_num_to_send, total_packets, is_last_packet)
                
                ack = self.receive_ack(sock)
                
                if ack and ack.get('status') == 'ok' and ack.get('sequence') == seq_num_to_send:
                    pacotes_enviados_nesta_msg += 1
                else:
                    print(f"[CLIENTE] Erro na sequência de ACK. Abortando mensagem.")
                    break 
            
            if pacotes_enviados_nesta_msg == total_packets:
                print(f"[CLIENTE] Mensagem completa enviada com sucesso!")
                self.messages_sent += 1
                self.sequence_number_base += total_packets 
            else:
                 print(f"[CLIENTE] Falha ao enviar mensagem completa.")
                 self.sequence_number_base += total_packets


        print(f"\n{'='*60}")
        print("ESTATÍSTICAS DA SESSÃO:")
        print(f"Total de mensagens completas enviadas: {self.messages_sent}")
        print(f"Total de pacotes individuais enviados: {self.packets_sent}")
        print(f"Total de pacotes individuais confirmados: {self.packets_confirmed}")
        print(f"Taxa de sucesso (pacotes): {(self.packets_confirmed/self.packets_sent*100) if self.packets_sent > 0 else 0:.1f}%")
        print(f"{'='*60}\n")
        
        sock.close()
        print("[CLIENTE] Conexão encerrada.")



if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Cliente de Transporte Confiável")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5005)
    parser.add_argument("--max-text-size", type=int, default=30) 
    
    args = parser.parse_args()

    chosen_protocol = ""
    
    while True:
        
        chosen_protocol = input("Digite o protocolo a ser utilizado (gbn ou sr): ")
        
        chosen_protocol = chosen_protocol.lower().strip()
        
        
        if chosen_protocol in ['gbn', 'sr']:
            break
        
        else:
            print("Opção inválida. Digite 'gbn' ou 'sr'.")

    
    client = Client(args.host, args.port, chosen_protocol, args.max_text_size)
    client.connect()