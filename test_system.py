#!/usr/bin/env python3
"""
Script de teste para o sistema cliente-servidor
Pode ser usado para testes automatizados
"""

import socket
import json
import time
import sys

def test_connection(host='127.0.0.1', port=5005):
    """Testa a conexão com o servidor"""
    print("\n" + "="*60)
    print("TESTE DE CONEXÃO")
    print("="*60 + "\n")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        print(f"✓ Conexão estabelecida com {host}:{port}")
        
        # Teste de handshake
        syn = {'protocol': 'gbn', 'min_chars': 30}
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
        sock.settimeout(5)
        sock.connect((host, port))
        
        # Handshake
        syn = {'protocol': 'gbn', 'min_chars': 30}
        sock.sendall(json.dumps(syn).encode('utf-8'))
        data = sock.recv(1024)
        syn_ack = json.loads(data.decode('utf-8'))
        session_id = syn_ack.get('session_id')
        
        ack = {'session_id': session_id, 'message': 'Handshake completo'}
        sock.sendall(json.dumps(ack).encode('utf-8'))
        
        print(f"Session ID: {session_id}")
        
        # Teste 1: Mensagem válida
        print("\nTeste 1: Enviar mensagem válida (>30 chars)")
        message1 = {
            'type': 'data',
            'session_id': session_id,
            'sequence': 0,
            'data': 'Esta é uma mensagem de teste com mais de trinta caracteres para validação',
            'protocol': 'gbn',
            'timestamp': time.time()
        }
        sock.sendall(json.dumps(message1).encode('utf-8'))
        ack1 = json.loads(sock.recv(2048).decode('utf-8'))
        if ack1.get('status') == 'ok':
            print("✓ Mensagem válida aceita - ACK recebido")
        else:
            print("✗ Erro: mensagem válida rejeitada")
            return False
        
        # Teste 2: Mensagem muito curta
        print("\nTeste 2: Enviar mensagem curta (<30 chars)")
        message2 = {
            'type': 'data',
            'session_id': session_id,
            'sequence': 1,
            'data': 'Mensagem curta',
            'protocol': 'gbn',
            'timestamp': time.time()
        }
        sock.sendall(json.dumps(message2).encode('utf-8'))
        nack = json.loads(sock.recv(2048).decode('utf-8'))
        if nack.get('status') == 'error':
            print("✓ Mensagem curta rejeitada - NACK recebido")
        else:
            print("✗ Erro: mensagem curta foi aceita incorretamente")
            return False
        
        # Teste 3: Múltiplas mensagens
        print("\nTeste 3: Enviar múltiplas mensagens válidas")
        for i in range(3):
            message = {
                'type': 'data',
                'session_id': session_id,
                'sequence': i + 2,
                'data': f'Mensagem número {i+1} com conteúdo suficiente para passar na validação do servidor',
                'protocol': 'gbn',
                'timestamp': time.time()
            }
            sock.sendall(json.dumps(message).encode('utf-8'))
            ack = json.loads(sock.recv(2048).decode('utf-8'))
            if ack.get('status') != 'ok':
                print(f"✗ Erro na mensagem #{i+2}")
                return False
        print("✓ Todas as 3 mensagens foram aceitas")
        
        # Encerrar
        close_msg = {
            'type': 'close',
            'session_id': session_id,
            'message': 'Teste finalizado'
        }
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
    
    # Teste 1: Conexão
    results.append(("Conexão", test_connection(host, port)))
    time.sleep(1)
    
    # Teste 2: Troca de mensagens
    results.append(("Troca de Mensagens", test_message_exchange(host, port)))
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60 + "\n")
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✓ PASSOU" if result else "✗ FALHOU"
        print(f"{test_name:.<40} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "-"*60)
    print(f"Total: {len(results)} testes | Passou: {passed} | Falhou: {failed}")
    print("="*60 + "\n")
    
    if failed == 0:
        print("🎉 Todos os testes passaram!")
        sys.exit(0)
    else:
        print("❌ Alguns testes falharam.")
        sys.exit(1)

if __name__ == "__main__":
    main()
