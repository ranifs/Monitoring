#!/bin/bash

# Скрипт для развертывания мониторинга камер на VPS
# Использование: ./deploy_vps.sh

echo "🚀 Начинаем развертывание мониторинга камер на VPS..."

# Обновляем систему
echo "📦 Обновляем систему..."
sudo apt update && sudo apt upgrade -y

# Устанавливаем Python и pip
echo "🐍 Устанавливаем Python и pip..."
sudo apt install python3 python3-pip python3-venv -y

# Создаем директорию для проекта
echo "📁 Создаем директорию проекта..."
sudo mkdir -p /opt/wotcher_monitoring
sudo chown $USER:$USER /opt/wotcher_monitoring
cd /opt/wotcher_monitoring

# Создаем виртуальное окружение
echo "🔧 Создаем виртуальное окружение..."
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
echo "📚 Устанавливаем зависимости..."
pip install --upgrade pip
pip install -r requirements.txt

# Создаем systemd сервис
echo "⚙️ Создаем systemd сервис..."
sudo tee /etc/systemd/system/wotcher-monitoring.service > /dev/null <<EOF
[Unit]
Description=Wotcher Camera Monitoring Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/wotcher_monitoring
Environment=PATH=/opt/wotcher_monitoring/venv/bin
ExecStart=/opt/wotcher_monitoring/venv/bin/python wotcher_monitoring.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Перезагружаем systemd
sudo systemctl daemon-reload

# Включаем сервис
sudo systemctl enable wotcher-monitoring.service

echo "✅ Развертывание завершено!"
echo ""
echo "📋 Полезные команды:"
echo "  Запуск: sudo systemctl start wotcher-monitoring"
echo "  Остановка: sudo systemctl stop wotcher-monitoring"
echo "  Статус: sudo systemctl status wotcher-monitoring"
echo "  Логи: sudo journalctl -u wotcher-monitoring -f"
echo "  Перезапуск: sudo systemctl restart wotcher-monitoring"
echo ""
echo "⚠️  Не забудьте:"
echo "  1. Настроить переменные окружения в .env файле"
echo "  2. Скопировать файлы проекта в /opt/wotcher_monitoring/"
echo "  3. Запустить сервис: sudo systemctl start wotcher-monitoring"