import socket
import json
import argparse

class Client:
 
    def __init__(self, server_addr='127.0.0.1', server_port=5005, protocol='gbn', min_chars=30):
        self.server_addr = server_addr
        self.server_port = server_port
        self.protocol = protocol
        self.min_chars = min(min_chars, 30)
        self.session_id = None

    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.server_addr, self.server_port))
        print(f"[CLIENTE] Conectado ao servidor {self.server_addr}:{self.server_port}")

       
        syn = {'protocol': self.protocol, 'min_chars': self.min_chars}
        sock.sendall(json.dumps(syn).encode('utf-8'))
        print(f"[CLIENTE] SYN enviado: {syn}")

        data = sock.recv(1024)
        syn_ack = json.loads(data.decode('utf-8'))
        print(f"[CLIENTE] SYN-ACK recebido: {syn_ack}")
        self.session_id = syn_ack.get('session_id')

        
        ack = {'session_id': self.session_id, 'message': 'Handshake completo'}
        sock.sendall(json.dumps(ack).encode('utf-8'))
        print(f"[CLIENTE] ACK enviado. Handshake concluído. Session={self.session_id}")

        while True:
            mensagem = input("Digite uma mensagem para o servidor (ou 'sair' para encerrar): ")
            if mensagem.lower() == 'sair':
                break
            sock.sendall(mensagem.encode('utf-8'))
            resposta = sock.recv(1024)
            print(f"[CLIENTE] Resposta do servidor: {resposta.decode('utf-8')}")

        sock.close()



if __name__ == "__main__":
   
    parser = argparse.ArgumentParser(description="Cliente Handshake TCP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5005)
    parser.add_argument("--max-chars", type=int, default=30)
   
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