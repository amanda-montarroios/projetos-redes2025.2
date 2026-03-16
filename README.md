# Sistema de Troca de Mensagens Cliente-Servidor

Sistema de comunicação cliente-servidor usando TCP com handshake de 3 vias e troca de mensagens com confirmação (ACK/NACK).

## 🎓 Trabalho I - Redes de Computadores
**Data de Entrega:** 30/11/2025  

---

## 📋 Características Implementadas

### ✅ Requisitos Obrigatórios
- [x] **Handshake de 3 vias** (SYN, SYN-ACK, ACK)
- [x] **Números de sequência** para controle de pacotes
- [x] **Soma de verificação** (Checksum SHA-1)
- [x] **Temporizador** para retransmissões (SR)
- [x] **Reconhecimento positivo** (ACK)
- [x] **Reconhecimento negativo** (NACK)
- [x] **Janela deslizante** (1 a 5 pacotes) - **NEGOCIADA**
- [x] **Paralelismo** (múltiplos pacotes em trânsito)
- [x] **Protocolos GBN e SR** implementados
- [x] **Simulação de erros e perdas**
- [x] **Segmentação** (máx 4 chars por pacote)

### ✅ Requisitos de Pontuação Extra
- [x] **Algoritmo de checagem de integridade** (SHA-1) 
- [x] **Criptografia simétrica** (Fernet/AES-128)

---

## 🚀 Instalação e Execução

### Pré-requisitos
```bash
# Python 3.6+
python --version

# Instalar biblioteca de criptografia
pip install cryptography --break-system-packages
```

### Iniciar o Servidor
```bash
# Servidor padrão (janela = 5, porta 5005)
python server.py

# Servidor customizado
python server.py --port 6000 --window_size 3 --protocol gbn

# Servidor sem SSL/TLS
python server.py --no-ssl
```

**Parâmetros do servidor:**
- `--host`: Endereço IP (padrão: 127.0.0.1)
- `--port`: Porta (padrão: 5005)
- `--protocol`: Protocolo padrão - `gbn` ou `sr` (padrão: gbn)
- `--max_chars`: Tamanho máximo de mensagem (padrão: 30)
- `--max_payload`: Tamanho máximo de pacote (padrão: 4)
- `--window_size`: Janela máxima aceita pelo servidor (padrão: 5)
- `--no-ssl`: Desabilita SSL/TLS

### Iniciar o Cliente
```bash
# Cliente padrão (janela = 5, porta 5005)
python client.py

# Cliente customizado
python client.py --host 127.0.0.1 --port 6000 --window_size 2

# Cliente sem SSL/TLS
python client.py --no-ssl
```

**Parâmetros do cliente:**
- `--host`: Endereço IP do servidor (padrão: 127.0.0.1)
- `--port`: Porta do servidor (padrão: 5005)
- `--max_chars`: Tamanho máximo desejado para mensagens (padrão: 30)
- `--window_size`: Janela proposta pelo cliente (padrão: 5)
- `--no-ssl`: Desabilita SSL/TLS

---

## 📊 Exemplo de Uso Completo

### Terminal 1 (Servidor):
```bash
$ python server.py --window_size 3

============================================================
[SERVIDOR] Servidor iniciado
============================================================
[SERVIDOR] Escutando em 127.0.0.1:5005
[SERVIDOR] Protocolo padrão: gbn
[SERVIDOR] Tamanho da janela (máximo): 3
[SERVIDOR] Limite: 30 chars (msg) / 4 chars (pacote)
[SERVIDOR] Checksum: SHA-1 | Criptografia: Fernet (AES-128)
============================================================

============================================================
[SERVIDOR] Nova conexão de 127.0.0.1:54321
============================================================
[SERVIDOR] SYN-ACK enviado para 127.0.0.1:54321
           Session: abc12345
           Protocolo: gbn
           Janela negociada: 3 (Cliente: 5, Servidor: 3)
[SERVIDOR] ✓ Handshake concluído para 127.0.0.1:54321

[SERVIDOR] Pacote #0 (gbn) recebido de 127.0.0.1:54321
           Conteúdo Desencriptado: 'Esta'
           Tamanho: 4
           Checksum enviado: 8b52b3e8... | Checksum calculado: 8b52b3e8...
[SERVIDOR] ✓ Pacote #0 íntegro (GBN) → Aceito em ordem.

[SERVIDOR] Pacote #1 (gbn) recebido de 127.0.0.1:54321
           Conteúdo Desencriptado: ' é u'
           Tamanho: 4
           Checksum enviado: 7a9c2f3d... | Checksum calculado: 7a9c2f3d...
[SERVIDOR] ✓ Pacote #1 íntegro (GBN) → Aceito em ordem.

[SERVIDOR] Pacote #2 (gbn) recebido de 127.0.0.1:54321
           Conteúdo Desencriptado: 'ma m'
           Tamanho: 4
           Checksum enviado: 3f8d9e2a... | Checksum calculado: 3f8d9e2a...
[SERVIDOR] ✓ Pacote #2 íntegro (GBN) → Aceito em ordem.

[SERVIDOR] Pacote #3 (gbn) recebido de 127.0.0.1:54321
           Conteúdo Desencriptado: 'ensa'
           Tamanho: 4
           Checksum enviado: 9d4e5f6a... | Checksum calculado: 9d4e5f6a...
[SERVIDOR] ✓ Pacote #3 íntegro (GBN) → Aceito em ordem.

[SERVIDOR] Pacote #4 (gbn) recebido de 127.0.0.1:54321
           Conteúdo Desencriptado: 'gem'
           Tamanho: 3
           Checksum enviado: 1c2d3e4f... | Checksum calculado: 1c2d3e4f...
[SERVIDOR] ✓ Pacote #4 íntegro (GBN) → Aceito em ordem.

======================================================================
                  MENSAGEM COMPLETA RECEBIDA (GBN)                   
======================================================================
De: 127.0.0.1:54321
Protocolo: GBN (Go-Back-N)
Total de pacotes: 5
----------------------------------------------------------------------
STATUS: ✓ ACEITA
CONTEÚDO DA MENSAGEM:
Esta é uma mensagem
----------------------------------------------------------------------
Tamanho: 19 caracteres
======================================================================
```

### Terminal 2 (Cliente):
```bash
$ python client.py --window_size 5

Digite o protocolo a ser utilizado (gbn ou sr): gbn

[CLIENTE] SYN enviado: protocolo=gbn, max_chars=30, window_size=5
[CLIENTE] SYN-ACK recebido do servidor
[CLIENTE] Session ID: abc12345
[CLIENTE] Tamanho máximo de mensagem: 30 caracteres
[CLIENTE] Tamanho da janela negociado: 3
[CLIENTE] ACK enviado. Handshake concluído!

============================================================
Pronto para enviar mensagens!
============================================================

[INFO] Mensagens enviadas: 0 | Confirmações (ACKs): 0
Deseja injetar falha na PRÓXIMA mensagem? ('c' - corromper / 'p' - perder / 'n' - normal): n
Digite uma mensagem (máx. 30 chars) ou 'sair': Esta é uma mensagem

[DEBUG] Mensagem FINAL antes da segmentação (19 chars): 'Esta é uma mensagem'

[CLIENTE] Pacote #0 (gbn) enviado: 'Esta' | Checksum Original: 8b52b3e8...
[CLIENTE] Pacote #1 (gbn) enviado: ' é u' | Checksum Original: 7a9c2f3d...
[CLIENTE] Pacote #2 (gbn) enviado: 'ma m' | Checksum Original: 3f8d9e2a...
[CLIENTE] Pacote #3 (gbn) enviado: 'ensa' | Checksum Original: 9d4e5f6a...
[CLIENTE] Pacote #4 (gbn) enviado: 'gem' | Checksum Original: 1c2d3e4f...

[CLIENTE] ACK recebido para pacote/mensagem #4 | Status OK.

[INFO] Mensagens enviadas: 1 | Confirmações (ACKs): 1
Deseja injetar falha na PRÓXIMA mensagem? ('c' - corromper / 'p' - perder / 'n' - normal): n
Digite uma mensagem (máx. 30 chars) ou 'sair': sair

============================================================
ESTATÍSTICAS DA SESSÃO:
  • Total de mensagens completas enviadas: 1
  • Total de pacotes individuais enviados: 5
  • Total de confirmações (ACKs) recebidas: 1
  • Taxa de sucesso (ACKs/Pacotes): 20.0%
============================================================

[CLIENTE] Conexão encerrada.
```

---

## 🔧 Funcionalidades Principais

### 1. Negociação da Janela
O tamanho da janela é **negociado** entre cliente e servidor durante o handshake:
- Cliente propõe um tamanho (1-5)
- Servidor tem um tamanho máximo (1-5)
- Janela final = **mínimo** entre os dois valores

```bash
# Exemplo: Cliente quer 5, Servidor aceita até 3 → Janela = 3
python server.py --window_size 3
python client.py --window_size 5
# Resultado: janela negociada = 3
```

### 2. Protocolos Suportados

#### Go-Back-N (GBN)
- Janela deslizante no emissor
- Receptor aceita **apenas pacotes em ordem**
- Pacote fora de ordem → descartado
- Erro/perda → **retransmite todos** os pacotes da janela

#### Selective Repeat (SR)
- Janela deslizante em ambos os lados
- Receptor aceita pacotes **fora de ordem** (dentro da janela)
- ACK seletivo para cada pacote
- Erro/perda → **retransmite apenas** o pacote problemático
- Temporizador individual por pacote (2 segundos)

### 3. Simulação de Erros e Perdas

Antes de cada mensagem, o cliente pergunta:
```
Deseja injetar falha na PRÓXIMA mensagem? ('c' - corromper / 'p' - perder / 'n' - normal):
```

- **`c` (corromper)**: Altera o checksum de um pacote específico
- **`p` (perder)**: Não envia um pacote específico
- **`n` (normal)**: Envia normalmente sem erros

Em seguida, escolhe o índice do pacote (0, 1, 2, ...):
```
Qual o ÍNDICE do pacote na mensagem a CORROMPER? (0, 1, 2...): 1
```

### 4. Segurança Implementada

#### Checksum (SHA-1)
- Calculado sobre o conteúdo **antes** da criptografia
- Verifica integridade dos dados
- Pacote com checksum inválido → NACK

#### Criptografia Simétrica (Fernet)
- AES-128 em modo CBC
- Chave compartilhada entre cliente e servidor
- Dados criptografados **antes** do envio

#### SSL/TLS (Opcional)
- Criptografia da camada de transporte
- Requer certificados `server.crt` e `server.key`
- Pode ser desabilitado com `--no-ssl`

---

## 📁 Estrutura do Projeto

```
trabalho-redes/
│
├── client.py              # Cliente (versão final corrigida)
├── server.py              # Servidor (versão final corrigida)
│
├── CORRECOES_APLICADAS.md      # Documentação das correções
├── EXEMPLOS_ANTES_DEPOIS.md    # Comparação visual
├── GUIA_DE_TESTES.md           # Testes de validação
├── README.md                   # Este arquivo
│
└── (opcionais)
    ├── server.crt         # Certificado SSL (se usar SSL)
    ├── server.key         # Chave SSL (se usar SSL)
    └── run.sh             # Script auxiliar
```

---

## 🧪 Testes Recomendados

### Teste Básico (GBN sem erros)
```bash
# Terminal 1
python server.py

# Terminal 2
python client.py
# Protocolo: gbn
# Falha: n
# Mensagem: Teste basico sem erros aqui
```

### Teste com Erro (GBN)
```bash
# Terminal 1
python server.py

# Terminal 2
python client.py
# Protocolo: gbn
# Falha: c (corromper)
# Índice: 2
# Mensagem: Mensagem com erro no meio
```

### Teste com Perda (SR)
```bash
# Terminal 1
python server.py

# Terminal 2
python client.py
# Protocolo: sr
# Falha: p (perder)
# Índice: 1
# Mensagem: Selective Repeat com perda
```

### Teste de Negociação
```bash
# Terminal 1
python server.py --window_size 2

# Terminal 2
python client.py --window_size 4
# Observe: "Janela negociada: 2"
```

---

## 📝 Conceitos de Redes Implementados

1. **Handshake de 3 Vias**: Estabelecimento de conexão confiável
2. **Números de Sequência**: Identificação e ordenação de pacotes
3. **ACK/NACK**: Confirmação positiva e negativa
4. **Checksum**: Detecção de erros de integridade
5. **Temporizador**: Retransmissão após timeout (SR)
6. **Janela Deslizante**: Controle de fluxo e paralelismo
7. **GBN vs SR**: Dois paradigmas de retransmissão
8. **Segmentação**: Divisão de mensagens em pacotes menores
9. **Criptografia**: Confidencialidade e autenticidade
10. **Session Management**: Gerenciamento de múltiplos clientes

---

## ✅ Checklist de Entrega

- [x] Código cliente (`client.py`)
- [x] Código servidor (`server.py`)
- [x] Documentação das correções
- [x] Guia de testes
- [x] README completo
- [x] Checksum (SHA-1) implementado → +0.5 prova
- [x] Criptografia (Fernet) implementada → +0.5 prova
- [x] Janela variável (1-5) negociada
- [x] Mensagens visíveis no servidor
- [x] Loop robusto sem travamento
- [x] Validação de entrada
- [x] Logs profissionais

**PROJETO 100% COMPLETO E PRONTO PARA APRESENTAÇÃO! 🎉**

---

## 👥 Informações do Trabalho

**Disciplina**: Redes de Computadores  
**Data de Entrega**: 30/11/2025  
**Pontuação**: 0 a 10 + até 1.0 extra (checksum + criptografia)

---

## 👩‍💻 Integrantes do Projeto

| Nome | E-mail |
| :--- | :--- |
| **Amanda Montarroios** | amo@cesar.school |
| **Fabiana Coelho** | fcsls@cesar.school |
| **Maria Júlia Dantas** | mjdma@cesar.school |
| **Maria Luiza Dantas** | mldt@cesar.school |
| **Rafael Barros** | ralb@cesar.school |
| **Julia Maria Teixeira** | jmst@cesar.school |


---



