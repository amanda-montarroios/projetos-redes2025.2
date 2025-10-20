# Sistema de Troca de Mensagens Cliente-Servidor

Sistema de comunicação cliente-servidor usando TCP com handshake de 3 vias e troca de mensagens com confirmação (ACK/NACK).

## 📋 Características

- **Handshake de 3 vias** (SYN, SYN-ACK, ACK)
- **Mensagens numeradas** com número de sequência
- **Validação de tamanho mínimo** de mensagens
- **Sistema ACK/NACK** para confirmação
- **Estatísticas de sessão** (mensagens enviadas, confirmadas, tempo de conexão)
- **Canal sem erros**: assume comunicação confiável (sem perda de pacotes)
- Suporte para protocolos **GBN** (Go-Back-N) e **SR** (Selective Repeat)

## 🚀 Como Usar

### 1. Iniciar o Servidor

Em um terminal, execute:

```bash
python server.py
```

Ou com parâmetros personalizados:

```bash
python server.py --host 127.0.0.1 --port 5005 --protocol gbn --max-chars 30
```

**Parâmetros do servidor:**
- `--host`: Endereço IP do servidor (padrão: 127.0.0.1)
- `--port`: Porta do servidor (padrão: 5005)
- `--protocol`: Protocolo padrão - `gbn` ou `sr` (padrão: gbn)
- `--max-chars`: Tamanho mínimo de mensagem (padrão: 30)

### 2. Iniciar o Cliente

Em outro terminal, execute:

```bash
python client.py
```

O cliente solicitará que você escolha o protocolo (gbn ou sr).

Ou com parâmetros:

```bash
python client.py --host 127.0.0.1 --port 5005 --max-chars 30
```

**Parâmetros do cliente:**
- `--host`: Endereço IP do servidor
- `--port`: Porta do servidor
- `--max-chars`: Tamanho mínimo desejado para mensagens

### 3. Enviar Mensagens

Após a conexão, digite mensagens no cliente:
- Mensagens devem ter **pelo menos 30 caracteres** (ou o valor configurado) Aqui mudei para 5 para facilitar e não ter que ficar escrevendo 30 sempre
- Digite `sair` para encerrar
- O servidor responde com ACK para cada mensagem válida

## 📊 Exemplo de Execução

### Terminal do Servidor:
```
============================================================
[SERVIDOR] Servidor iniciado
============================================================
[SERVIDOR] Escutando em 127.0.0.1:5005
[SERVIDOR] Protocolo padrão: gbn
[SERVIDOR] Tamanho mínimo de mensagem: 30 caracteres
============================================================

============================================================
[SERVIDOR] Nova conexão de 127.0.0.1:56789
============================================================
[SERVIDOR] SYN recebido de 127.0.0.1:56789
           Protocolo solicitado: gbn
           Min chars solicitado: 30
[SERVIDOR] SYN-ACK enviado para 127.0.0.1:56789 (Session: abc12345)
[SERVIDOR] ACK recebido de 127.0.0.1:56789
[SERVIDOR] ✓ Handshake concluído para 127.0.0.1:56789

[SERVIDOR] Aguardando mensagens de 127.0.0.1:56789...

[SERVIDOR] Mensagem #0 recebida de 127.0.0.1:56789
           Conteúdo: 'Esta é uma mensagem de teste com mais de 30 caracteres'
           Tamanho: 56 caracteres
[SERVIDOR] ✓ ACK enviado para mensagem #0
```

### Terminal do Cliente:
```
============================================================
[CLIENTE] Conectado ao servidor 127.0.0.1:5005
============================================================

[CLIENTE] SYN enviado: protocolo=gbn, min_chars=30
[CLIENTE] SYN-ACK recebido do servidor
[CLIENTE] Session ID: abc12345
[CLIENTE] Tamanho mínimo de mensagem: 30 caracteres
[CLIENTE] ACK enviado. Handshake concluído!

============================================================
Pronto para enviar mensagens!
============================================================

[INFO] Mensagens enviadas: 0 | Confirmadas: 0
Digite uma mensagem (mín. 30 chars) ou 'sair': Esta é uma mensagem de teste com mais de 30 caracteres
[CLIENTE] Mensagem #0 enviada: 'Esta é uma mensagem de teste com mais de 30 caracteres' (56 chars)
[CLIENTE] ✓ ACK recebido para mensagem #0
[CLIENTE] Servidor confirmou: 'Esta é uma mensagem de teste com mais de 30 caracteres'

[INFO] Mensagens enviadas: 1 | Confirmadas: 1
Digite uma mensagem (mín. 30 chars) ou 'sair': sair

============================================================
ESTATÍSTICAS DA SESSÃO:
  • Total de mensagens enviadas: 1
  • Total de mensagens confirmadas: 1
  • Taxa de sucesso: 100.0%
============================================================

[CLIENTE] Conexão encerrada.
```

## 🏗️ Arquitetura

### Fluxo de Comunicação

1. **Handshake (3 vias)**:
   - Cliente → Servidor: SYN (solicita conexão)
   - Servidor → Cliente: SYN-ACK (confirma e envia Session ID)
   - Cliente → Servidor: ACK (confirma handshake)

2. **Troca de Mensagens**:
   - Cliente → Servidor: Mensagem com número de sequência
   - Servidor valida tamanho mínimo
   - Servidor → Cliente: ACK (sucesso) ou NACK (erro)

3. **Encerramento**:
   - Cliente → Servidor: Mensagem de CLOSE
   - Servidor exibe estatísticas da sessão

### Estrutura das Mensagens

**Mensagem de Dados:**
```json
{
    "type": "data",
    "session_id": "abc12345",
    "sequence": 0,
    "data": "conteúdo da mensagem",
    "protocol": "gbn",
    "timestamp": 1234567890.123
}
```

**ACK/NACK:**
```json
{
    "type": "ack",
    "status": "ok",  // ou "error"
    "sequence": 0,
    "echo": "conteúdo da mensagem",
    "message": "Mensagem recebida com sucesso",
    "timestamp": 1234567890.123
}
```

## 🔧 Requisitos

- Python 3.6+
- Bibliotecas padrão: `socket`, `json`, `hashlib`, `argparse`, `time`

## 📝 Observações

- **Canal sem erros**: O sistema assume que não há perda de pacotes ou corrupção de dados
- **Validação de tamanho**: Mensagens menores que o mínimo são rejeitadas com NACK
- **Protocolo GBN/SR**: Suportado na negociação, mas não implementa janela deslizante (canal confiável)
- **Session ID**: Gerado automaticamente pelo servidor usando hash MD5
