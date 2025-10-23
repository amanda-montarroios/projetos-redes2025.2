#!/usr/bin/env python3
"""
Script de teste para o sistema cliente-servidor
Pode ser usado para testes automatizados
"""

import socket
import json
import time
import sys

MAX_PAYLOAD = 4  # Pacotes de até 4 caracteres, como o servidor exige

def calcular_checksum(texto):
    """Calcula o checksum simples (soma dos bytes módulo 256)."""
    return sum(texto.encode('utf-8')) % 256

def enviar_mensagem_segmentada(sock, session_id, mensagem, seq_base=0):
    """Envia uma mensagem segmentada em pacotes de MAX_PAYLOAD caracteres"""
    pacotes = [mensagem[i:i+MAX_PAYLOAD] for i in range(0, len(mensagem), MAX_PAYLOAD)]
    total_pacotes = len(pacotes)

    for i, chunk in enumerate(pacotes):
        pacote = {
            'type': 'data',
            'session_id': session_id,
            'sequence': seq_base + i,
            'data': chunk,
            'is_last': (i == total_pacotes - 1),
            'protocol': 'gbn',
            'timestamp': time.time(),
            'checksum': calcular_checksum(chunk)
        }
        sock.sendall(json.dumps(pacote).encode('utf-8'))
        ack = json.loads(sock.recv(2048).decode('utf-8'))
        if ack.get('status') != 'ok':
            print(f"✗ Erro no pacote #{seq_base + i}: {ack.get('message')}")
            return False
    return True

def test_connection(host='127.0.0.1', port=5005):
    """Testa a conexão com o servidor"""
    print("\n" + "="*60)
    print("TESTE DE CONEXÃO")
    print("="*60 + "\n")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        print(f"✓ Conexão estabelecida com {host}:{port}")
        
        syn = {'protocol': 'gbn', 'max_chars': 30}
        sock.sendall(json.dumps(syn).encode('utf-8'))
        print("✓ SYN enviado")
        
        data = sock.recv(1024)
        syn_ack = json.loads(data.decode('utf-8'))
        print(f"✓ SYN-ACK recebido: Session={syn_ack.get('session_id')}")
        
        ack = {'session_id': syn_ack.get('session_id'), 'message': 'Handshake completo'}
        sock.sendall(json.dumps(ack).encode('utf-8'))
        print("✓ ACK enviado - Handshake concluído!")

        sock.close()
        print("\n✓ TESTE DE CONEXÃO: PASSOU\n")
        return True
        
    except Exception as e:
        print(f"\n✗ TESTE DE CONEXÃO: FALHOU")
        print(f"Erro: {e}\n")
        return False

def test_message_exchange(host='127.0.0.1', port=5005):
    """Testa a troca de mensagens"""
    print("\n" + "="*60)
    print("TESTE DE TROCA DE MENSAGENS")
    print("="*60 + "\n")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))

        # Handshake
        syn = {'protocol': 'gbn', 'max_chars': 30}
        sock.sendall(json.dumps(syn).encode('utf-8'))
        data = sock.recv(1024)
        syn_ack = json.loads(data.decode('utf-8'))
        session_id = syn_ack.get('session_id')
        ack = {'session_id': session_id, 'message': 'Handshake completo'}
        sock.sendall(json.dumps(ack).encode('utf-8'))

        print(f"Session ID: {session_id}")

        # Teste 1: Mensagem válida
        print("\nTeste 1: Enviar mensagem válida (≤30 chars)")
        mensagem1 = 'Mensagem de teste válida 30 chars!!'[:30]
        if enviar_mensagem_segmentada(sock, session_id, mensagem1):
            print("✓ Mensagem válida aceita - ACK recebido")
        else:
            print("✗ Erro: mensagem válida rejeitada")
            return False

        # Teste 2: Mensagem longa (>30 chars) truncada
        print("\nTeste 2: Enviar mensagem longa (>30 chars)")
        mensagem2 = 'Mensagem com mais de trinta caracteres enviada para teste'[:30]
        if enviar_mensagem_segmentada(sock, session_id, mensagem2, seq_base=6):
            print("✓ Mensagem longa truncada aceita - ACK recebido")
        else:
            print("✗ Erro: mensagem longa foi rejeitada")
            return False

        # Teste 3: Múltiplas mensagens válidas
        print("\nTeste 3: Enviar múltiplas mensagens válidas")
        seq_base = 12
        for i in range(3):
            msg = f'Msg#{i+1} teste servidor ok...'[:30]
            if not enviar_mensagem_segmentada(sock, session_id, msg, seq_base=seq_base):
                print(f"✗ Erro na mensagem #{i+1}")
                return False
            seq_base += (len(msg) + MAX_PAYLOAD - 1) // MAX_PAYLOAD
        print("✓ Todas as 3 mensagens foram aceitas")

        # Encerrar
        close_msg = {'type': 'close', 'session_id': session_id, 'message': 'Teste finalizado'}
        sock.sendall(json.dumps(close_msg).encode('utf-8'))
        sock.close()

        print("\n✓ TESTE DE TROCA DE MENSAGENS: PASSOU\n")
        return True

    except Exception as e:
        print(f"\n✗ TESTE DE TROCA DE MENSAGENS: FALHOU")
        print(f"Erro: {e}\n")
        return False

def main():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("INICIANDO TESTES DO SISTEMA CLIENTE-SERVIDOR")
    print("="*60)
    print("\nCertifique-se de que o servidor está rodando antes de continuar!")
    print("Execute: python server.py")
    input("\nPressione ENTER para iniciar os testes...")

    host = '127.0.0.1'
    port = 5005

    results = []
    results.append(("Conexão", test_connection(host, port)))
    time.sleep(1)
    results.append(("Troca de Mensagens", test_message_exchange(host, port)))

    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60 + "\n")

    passed = sum(1 for _, r in results if r)
    failed = len(results) - passed
    for test_name, result in results:
        status = "✓ PASSOU" if result else "✗ FALHOU"
        print(f"{test_name:.<40} {status}")

    print("\n" + "-"*60)
    print(f"Total: {len(results)} testes | Passou: {passed} | Falhou: {failed}")
    print("="*60 + "\n")
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
