# Arquitetura do Sistema

## Diagrama de Sequência

```
CLIENTE                                    SERVIDOR
   |                                          |
   |----------- SYN ------------------------->|
   |  {protocol: 'gbn', min_chars: 30}       |
   |                                          |
   |<---------- SYN-ACK ---------------------|
   |  {status: 'ok', session_id: 'abc123'}   |
   |                                          |
   |----------- ACK ------------------------->|
   |  {session_id: 'abc123'}                 |
   |                                          |
   |  ===== HANDSHAKE COMPLETO =====         |
   |                                          |
   |----------- MENSAGEM #0 ---------------->|
   |  {type: 'data', sequence: 0, ...}       |
   |                                          |
   |                                      [VALIDA]
   |                                          |
   |<---------- ACK #0 -----------------------|
   |  {status: 'ok', sequence: 0}            |
   |                                          |
   |----------- MENSAGEM #1 ---------------->|
   |  {type: 'data', sequence: 1, ...}       |
   |                                          |
   |                                    [INVÁLIDA]
   |                                          |
   |<---------- NACK #1 ----------------------|
   |  {status: 'error', sequence: 1}         |
   |                                          |
   |----------- CLOSE ------------------------>|
   |  {type: 'close'}                        |
   |                                          |
   |                                   [ESTATÍSTICAS]
   |                                          |
   |<---------- FIM DA CONEXÃO ---------------|
   |                                          |
```

## Estrutura de Pacotes

### 1. SYN (Cliente → Servidor)
```json
{
    "protocol": "gbn",
    "min_chars": 30
}
```

### 2. SYN-ACK (Servidor → Cliente)
```json
{
    "status": "ok",
    "protocol": "gbn",
    "min_chars": 30,
    "session_id": "abc12345"
}
```

### 3. ACK Final (Cliente → Servidor)
```json
{
    "session_id": "abc12345",
    "message": "Handshake completo"
}
```

### 4. Mensagem de Dados (Cliente → Servidor)
```json
{
    "type": "data",
    "session_id": "abc12345",
    "sequence": 0,
    "data": "conteúdo da mensagem aqui",
    "protocol": "gbn",
    "timestamp": 1234567890.123
}
```

### 5. ACK de Mensagem (Servidor → Cliente)
```json
{
    "type": "ack",
    "status": "ok",
    "sequence": 0,
    "echo": "conteúdo da mensagem aqui",
    "message": "Mensagem recebida com sucesso",
    "timestamp": 1234567890.456
}
```

### 6. NACK de Mensagem (Servidor → Cliente)
```json
{
    "type": "ack",
    "status": "error",
    "sequence": 1,
    "message": "Mensagem muito curta. Mínimo: 30 caracteres",
    "timestamp": 1234567890.789
}
```

### 7. Mensagem de Encerramento (Cliente → Servidor)
```json
{
    "type": "close",
    "session_id": "abc12345",
    "message": "Cliente desconectando"
}
```

## Fluxograma do Servidor

```
[INÍCIO]
   |
   v
[Bind Socket]
   |
   v
[Listen]
   |
   v
[Accept Connection] <----------------+
   |                                 |
   v                                 |
[Recebe SYN]                         |
   |                                 |
   v                                 |
[Cria Sessão]                        |
   |                                 |
   v                                 |
[Envia SYN-ACK]                      |
   |                                 |
   v                                 |
[Recebe ACK Final]                   |
   |                                 |
   v                                 |
[Handshake Completo]                 |
   |                                 |
   v                                 |
[Aguarda Mensagem] <--------+        |
   |                        |        |
   v                        |        |
[Recebe Pacote]             |        |
   |                        |        |
   v                        |        |
[Tipo = ?]                  |        |
   |                        |        |
   +--[data]------> [Valida Tamanho] |
   |                      |           |
   |                      v           |
   |                [Tamanho OK?]     |
   |                   /    \         |
   |              [Sim]    [Não]      |
   |                 |        |       |
   |           [Envia ACK] [NACK]     |
   |                 |        |       |
   |                 +--------+       |
   |                      |           |
   +--[close]----> [Estatísticas]    |
   |                      |           |
   |                      v           |
   |              [Fecha Conexão]     |
   |                      |           |
   +----------------------+-----------+
   |
   v
[Ctrl+C?] --[Sim]--> [Fecha Socket] --> [FIM]
   |
  [Não]
   |
   +-----> [Accept Connection]
```

## Fluxograma do Cliente

```
[INÍCIO]
   |
   v
[Escolhe Protocolo]
   |
   v
[Connect ao Servidor]
   |
   v
[Envia SYN]
   |
   v
[Aguarda SYN-ACK]
   |
   v
[Recebe Session ID]
   |
   v
[Envia ACK Final]
   |
   v
[Handshake Completo]
   |
   v
[Pede Input] <--------------+
   |                        |
   v                        |
[Input = "sair"?]           |
   |                        |
   +--[Sim]---> [Envia CLOSE]
   |                 |
  [Não]              v
   |          [Estatísticas]
   v                 |
[Valida Tamanho]     v
   |            [Fecha Socket]
   v                 |
[Tamanho < min?]     v
   |              [FIM]
   +--[Sim]---> [Erro] ---+
   |                      |
  [Não]                   |
   |                      |
   v                      |
[Envia Mensagem]          |
   |                      |
   v                      |
[Aguarda ACK/NACK]        |
   |                      |
   v                      |
[Exibe Resultado]         |
   |                      |
   v                      |
[Incrementa Sequência]    |
   |                      |
   +----------------------+
```

## Classes e Métodos

### Classe `Server`

#### Atributos:
- `host`: Endereço IP do servidor
- `port`: Porta de escuta
- `protocol`: Protocolo padrão (gbn/sr)
- `min_chars`: Tamanho mínimo de mensagem
- `client_sessions`: Dicionário de sessões ativas
- `sock`: Socket TCP

#### Métodos:
- `__init__()`: Inicializa o servidor
- `handle_syn()`: Processa SYN e cria sessão
- `handle_ack()`: Confirma handshake
- `handle_data_message()`: Processa mensagens de dados
- `handle_close()`: Encerra sessão e exibe estatísticas
- `start()`: Loop principal do servidor

### Classe `Client`

#### Atributos:
- `server_addr`: Endereço do servidor
- `server_port`: Porta do servidor
- `protocol`: Protocolo escolhido
- `min_chars`: Tamanho mínimo de mensagem
- `session_id`: ID da sessão atual
- `sequence_number`: Número de sequência atual
- `messages_sent`: Total de mensagens enviadas
- `messages_confirmed`: Total de ACKs recebidos

#### Métodos:
- `__init__()`: Inicializa o cliente
- `send_message()`: Envia mensagem numerada
- `receive_ack()`: Recebe e processa ACK/NACK
- `connect()`: Conecta ao servidor e gerencia comunicação

## Conceitos de Redes Implementados

### 1. **Handshake de 3 Vias**
Estabelece conexão confiável entre cliente e servidor:
- SYN: Cliente solicita conexão
- SYN-ACK: Servidor confirma
- ACK: Cliente confirma recebimento

### 2. **Números de Sequência**
Cada mensagem tem um número único para:
- Identificação
- Ordenação
- Confirmação específica

### 3. **Confirmação Positiva (ACK)**
Servidor confirma recebimento de mensagens válidas

### 4. **Confirmação Negativa (NACK)**
Servidor rejeita mensagens inválidas com motivo

### 5. **Validação de Dados**
Verifica tamanho mínimo antes de processar

### 6. **Session Management**
Cada cliente tem uma sessão única identificada por hash MD5

### 7. **Estatísticas de Desempenho**
Coleta métricas durante a sessão:
- Mensagens enviadas/recebidas
- Tempo de conexão
- Taxa de sucesso

### 8. **Canal Confiável**
Assume que o TCP garante:
- Entrega ordenada
- Sem perda de pacotes
- Sem corrupção de dados

## Protocolo de Comunicação

### Estado da Conexão:
```
[CLOSED] --> SYN --> [SYN_SENT]
[SYN_SENT] --> SYN-ACK --> [SYN_RECEIVED]
[SYN_RECEIVED] --> ACK --> [ESTABLISHED]
[ESTABLISHED] --> DATA/ACK --> [ESTABLISHED]
[ESTABLISHED] --> CLOSE --> [CLOSED]
```

### Formato das Mensagens:
Todas as mensagens usam JSON sobre TCP
- Encoding: UTF-8
- Buffer: 2048 bytes
- Timeout: Configurável (padrão: sem timeout)
