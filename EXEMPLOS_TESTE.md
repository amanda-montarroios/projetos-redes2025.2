# Exemplos de Mensagens para Teste

## Mensagens Válidas (≥30 caracteres)

Use estas mensagens para testar o funcionamento correto do sistema:

1. `Esta é uma mensagem de teste com mais de trinta caracteres para validação`
2. `O sistema de troca de mensagens está funcionando corretamente agora`
3. `Python é uma linguagem de programação muito poderosa e versátil`
4. `Redes de computadores permitem a comunicação entre dispositivos`
5. `O protocolo TCP garante a entrega confiável de dados na rede`
6. `Este projeto implementa handshake de três vias e confirmação ACK`
7. `A comunicação cliente-servidor funciona através de sockets TCP`
8. `Mensagens são numeradas sequencialmente para controle de fluxo`
9. `O servidor valida o tamanho mínimo antes de aceitar mensagens`
10. `Estatísticas são coletadas durante toda a sessão de comunicação`

## Mensagens Inválidas (<30 caracteres)

Use estas para testar o sistema de rejeição (NACK):

1. `Oi`
2. `Teste`
3. `Mensagem curta`
4. `Muito pequeno`
5. `Falha`
6. `ABC123`
7. `Python`
8. `Redes`
9. `TCP/IP`
10. `Socket`

## Cenários de Teste

### Teste 1: Conexão Básica
1. Inicie o servidor
2. Inicie o cliente
3. Escolha o protocolo (gbn ou sr)
4. Observe o handshake de 3 vias
5. Digite `sair` para encerrar

### Teste 2: Mensagens Válidas
1. Conecte o cliente ao servidor
2. Envie mensagem: `Esta é uma mensagem de teste com mais de trinta caracteres`
3. Verifique o ACK com número de sequência #0
4. Envie outra mensagem válida
5. Verifique o ACK com número de sequência #1

### Teste 3: Mensagens Inválidas
1. Conecte o cliente ao servidor
2. Envie mensagem: `Teste`
3. Observe o NACK com mensagem de erro
4. Envie mensagem válida para confirmar que sistema continua funcionando

### Teste 4: Múltiplas Mensagens
1. Conecte o cliente ao servidor
2. Envie 10 mensagens válidas consecutivas
3. Observe os números de sequência incrementando (0-9)
4. Verifique as estatísticas ao final

### Teste 5: Validação de Tamanho
1. Configure servidor com `--max-chars 20`
2. Configure cliente com `--max-chars 25`
3. Servidor usará o menor valor (20)
4. Teste mensagens com 15, 20, 25 caracteres

## Comandos Úteis

### Iniciar servidor padrão:
```bash
python server.py
```

### Iniciar servidor na porta 6000:
```bash
python server.py --port 6000
```

### Iniciar servidor com min 20 chars:
```bash
python server.py --max-chars 20
```

### Iniciar cliente:
```bash
python client.py
```

### Iniciar cliente conectando na porta 6000:
```bash
python client.py --port 6000
```

### Executar testes automáticos:
```bash
# Certifique-se de que o servidor está rodando primeiro!
python test_system.py
```

### Usar script auxiliar:
```bash
./run.sh
```

## Análise de Logs

### Log do Servidor - Conexão Bem-Sucedida:
```
============================================================
[SERVIDOR] Servidor iniciado
============================================================
[SERVIDOR] Escutando em 127.0.0.1:5005
[SERVIDOR] Protocolo padrão: gbn
[SERVIDOR] Tamanho mínimo de mensagem: 30 caracteres
============================================================

============================================================
[SERVIDOR] Nova conexão de 127.0.0.1:45678
============================================================
[SERVIDOR] SYN recebido de 127.0.0.1:45678
           Protocolo solicitado: gbn
           Min chars solicitado: 30
[SERVIDOR] SYN-ACK enviado para 127.0.0.1:45678 (Session: abc12345)
[SERVIDOR] ACK recebido de 127.0.0.1:45678
[SERVIDOR] ✓ Handshake concluído para 127.0.0.1:45678
```

### Log do Cliente - Mensagem Enviada:
```
[INFO] Mensagens enviadas: 0 | Confirmadas: 0
Digite uma mensagem (mín. 30 chars) ou 'sair': Esta é uma mensagem de teste com mais de trinta caracteres
[CLIENTE] Mensagem #0 enviada: 'Esta é uma mensagem de teste com mais de trinta caracteres' (62 chars)
[CLIENTE] ✓ ACK recebido para mensagem #0
[CLIENTE] Servidor confirmou: 'Esta é uma mensagem de teste com mais de trinta caracteres'
```

### Log do Servidor - Mensagem Rejeitada:
```
[SERVIDOR] Mensagem #1 recebida de 127.0.0.1:45678
           Conteúdo: 'Teste'
           Tamanho: 5 caracteres
[SERVIDOR] ✗ NACK enviado para mensagem #1
```

## Troubleshooting

### Erro: "Address already in use"
**Solução:** Espere alguns segundos ou use uma porta diferente:
```bash
python server.py --port 5006
python client.py --port 5006
```

### Erro: "Connection refused"
**Solução:** Certifique-se de que o servidor está rodando primeiro.

### Cliente não conecta
**Solução:** Verifique firewall e certifique-se de usar o mesmo host/port em ambos.

### Mensagens não são aceitas
**Solução:** Verifique se têm pelo menos 30 caracteres (ou o valor configurado).
