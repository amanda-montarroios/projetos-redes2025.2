import socket
import json
import argparse
import time

class Client:
 
    def __init__(self, server_addr='127.0.0.1', server_port=5005, protocol='gbn', min_chars=5):
        self.server_addr = server_addr
        self.server_port = server_port
        self.protocol = protocol
        self.min_chars = min(min_chars, 5)
        self.session_id = None
        self.sequence_number = 0
        self.messages_sent = 0
        self.messages_confirmed = 0

    def send_message(self, sock, message_text):
        """Envia uma mensagem numerada para o servidor"""
        message_packet = {
            'type': 'data',
            'session_id': self.session_id,
            'sequence': self.sequence_number,
            'data': message_text,
            'protocol': self.protocol,
            'timestamp': time.time()
        }
        
        sock.sendall(json.dumps(message_packet).encode('utf-8'))
        self.messages_sent += 1
        print(f"[CLIENTE] Mensagem #{self.sequence_number} enviada: '{message_text}' ({len(message_text)} chars)")
        return self.sequence_number

    def receive_ack(self, sock):
        """Recebe confirmação do servidor"""
        data = sock.recv(2048)
        ack = json.loads(data.decode('utf-8'))
        
        if ack.get('type') == 'ack':
            seq = ack.get('sequence')
            status = ack.get('status')
            
            if status == 'ok':
                self.messages_confirmed += 1
                print(f"[CLIENTE] ✓ ACK recebido para mensagem #{seq}")
                if 'echo' in ack:
                    print(f"[CLIENTE] Servidor confirmou: '{ack['echo']}'")
            else:
                print(f"[CLIENTE] ✗ NACK recebido para mensagem #{seq}: {ack.get('message', 'Erro desconhecido')}")
            
            return ack
        return None

    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.server_addr, self.server_port))
        print(f"\n{'='*60}")
        print(f"[CLIENTE] Conectado ao servidor {self.server_addr}:{self.server_port}")
        print(f"{'='*60}\n")

        # Handshake - Passo 1: SYN
        syn = {'protocol': self.protocol, 'min_chars': self.min_chars}
        sock.sendall(json.dumps(syn).encode('utf-8'))
        print(f"[CLIENTE] SYN enviado: protocolo={self.protocol}, min_chars={self.min_chars}")

        # Handshake - Passo 2: SYN-ACK
        data = sock.recv(1024)
        syn_ack = json.loads(data.decode('utf-8'))
        print(f"[CLIENTE] SYN-ACK recebido do servidor")
        self.session_id = syn_ack.get('session_id')
        self.min_chars = syn_ack.get('min_chars', self.min_chars)
        print(f"[CLIENTE] Session ID: {self.session_id}")
        print(f"[CLIENTE] Tamanho mínimo de mensagem: {self.min_chars} caracteres")

        # Handshake - Passo 3: ACK
        ack = {'session_id': self.session_id, 'message': 'Handshake completo'}
        sock.sendall(json.dumps(ack).encode('utf-8'))
        print(f"[CLIENTE] ACK enviado. Handshake concluído!")
        print(f"\n{'='*60}")
        print("Pronto para enviar mensagens!")
        print(f"{'='*60}\n")

        # Loop de envio de mensagens
        while True:
            print(f"\n[INFO] Mensagens enviadas: {self.messages_sent} | Confirmadas: {self.messages_confirmed}")
            mensagem = input(f"Digite uma mensagem (mín. {self.min_chars} chars) ou 'sair': ")
            
            if mensagem.lower() == 'sair':
                print("\n[CLIENTE] Encerrando conexão...")
                # Enviar mensagem de encerramento
                close_packet = {
                    'type': 'close',
                    'session_id': self.session_id,
                    'message': 'Cliente desconectando'
                }
                sock.sendall(json.dumps(close_packet).encode('utf-8'))
                break
            
            # Validar tamanho mínimo
            if len(mensagem) < self.min_chars:
                print(f"[CLIENTE] ✗ Erro: Mensagem muito curta! Mínimo: {self.min_chars} caracteres, atual: {len(mensagem)}")
                continue
            
            # Enviar mensagem
            seq = self.send_message(sock, mensagem)
            
            # Receber ACK
            self.receive_ack(sock)
            
            # Incrementar número de sequência
            self.sequence_number += 1

        # Estatísticas finais
        print(f"\n{'='*60}")
        print("ESTATÍSTICAS DA SESSÃO:")
        print(f"  • Total de mensagens enviadas: {self.messages_sent}")
        print(f"  • Total de mensagens confirmadas: {self.messages_confirmed}")
        print(f"  • Taxa de sucesso: {(self.messages_confirmed/self.messages_sent*100) if self.messages_sent > 0 else 0:.1f}%")
        print(f"{'='*60}\n")
        
        sock.close()
        print("[CLIENTE] Conexão encerrada.")



if __name__ == "__main__":
   
    parser = argparse.ArgumentParser(description="Cliente Handshake TCP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5005)
    parser.add_argument("--max-chars", type=int, default=5)
   
    args = parser.parse_args()

    chosen_protocol = ""
    
    while True:
        
        chosen_protocol = input("Digite o protocolo a ser utilizado (gbn ou sr): ")
        
        chosen_protocol = chosen_protocol.lower().strip()
        
        
        if chosen_protocol in ['gbn', 'sr']:
            break
        
        else:
            print("Opção inválida. Por favor, digite 'gbn' ou 'sr'.")

   
    client = Client(args.host, args.port, chosen_protocol, args.max_chars)
    client.connect()