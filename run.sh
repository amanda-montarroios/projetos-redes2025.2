#!/bin/bash

# Script para iniciar o sistema cliente-servidor facilmente

echo "============================================================"
echo "  Sistema de Troca de Mensagens Cliente-Servidor"
echo "============================================================"
echo ""
echo "Escolha uma opção:"
echo ""
echo "  1) Iniciar Servidor"
echo "  2) Iniciar Cliente"
echo "  3) Executar Testes Automáticos"
echo "  4) Iniciar Servidor E Cliente (2 terminais)"
echo "  5) Sair"
echo ""
read -p "Opção: " opcao

case $opcao in
    1)
        echo ""
        echo "Iniciando servidor..."
        echo ""
        python3 server.py
        ;;
    2)
        echo ""
        echo "Iniciando cliente..."
        echo ""
        python3 client.py
        ;;
    3)
        echo ""
        echo "Executando testes automáticos..."
        echo "IMPORTANTE: O servidor deve estar rodando!"
        echo ""
        read -p "O servidor está rodando? (s/n): " servidor_ok
        if [ "$servidor_ok" = "s" ] || [ "$servidor_ok" = "S" ]; then
            python3 test_system.py
        else
            echo "Inicie o servidor primeiro em outro terminal!"
        fi
        ;;
    4)
        echo ""
        echo "Abrindo servidor e cliente em terminais separados..."
        echo ""
        # Tenta abrir em terminais diferentes dependendo do ambiente
        if command -v gnome-terminal &> /dev/null; then
            gnome-terminal -- bash -c "python3 server.py; exec bash"
            sleep 2
            gnome-terminal -- bash -c "python3 client.py; exec bash"
        elif command -v xterm &> /dev/null; then
            xterm -e "python3 server.py" &
            sleep 2
            xterm -e "python3 client.py" &
        else
            echo "Não foi possível detectar um emulador de terminal."
            echo "Execute manualmente em terminais separados:"
            echo "  Terminal 1: python3 server.py"
            echo "  Terminal 2: python3 client.py"
        fi
        ;;
    5)
        echo "Saindo..."
        exit 0
        ;;
    *)
        echo "Opção inválida!"
        exit 1
        ;;
esac
