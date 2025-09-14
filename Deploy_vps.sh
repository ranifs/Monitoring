echo '#!/bin/bash' > Deploy_vps.sh
echo '' >> Deploy_vps.sh
echo 'echo "🚀 Начинаем развертывание мониторинга камер на VPS..."' >> Deploy_vps.sh
echo '' >> Deploy_vps.sh
echo '# Обновляем систему' >> Deploy_vps.sh
echo 'echo "📦 Обновляем систему..."' >> Deploy_vps.sh
echo 'sudo apt update && sudo apt upgrade -y' >> Deploy_vps.sh
echo '' >> Deploy_vps.sh
echo '# Устанавливаем Python и pip' >> Deploy_vps.sh
echo 'echo "🐍 Устанавливаем Python и pip..."' >> Deploy_vps.sh
echo 'sudo apt install python3 python3-pip python3-venv -y' >> Deploy_vps.sh
echo '' >> Deploy_vps.sh
echo '# Создаем директорию для проекта' >> Deploy_vps.sh
echo 'echo "📁 Создаем директорию проекта..."' >> Deploy_vps.sh
echo 'sudo mkdir -p /opt/wotcher_monitoring' >> Deploy_vps.sh
echo 'sudo chown $USER:$USER /opt/wotcher_monitoring' >> Deploy_vps.sh
echo 'cd /opt/wotcher_monitoring' >> Deploy_vps.sh
echo '' >> Deploy_vps.sh
echo '# Создаем виртуальное окружение' >> Deploy_vps.sh
echo 'echo "🔧 Создаем виртуальное окружение..."' >> Deploy_vps.sh
echo 'python3 -m venv venv' >> Deploy_vps.sh
echo 'source venv/bin/activate' >> Deploy_vps.sh
echo '' >> Deploy_vps.sh
echo '# Устанавливаем зависимости' >> Deploy_vps.sh
echo 'echo "📚 Устанавливаем зависимости..."' >> Deploy_vps.sh
echo 'pip install --upgrade pip' >> Deploy_vps.sh
echo 'pip install -r requirements.txt' >> Deploy_vps.sh
echo '' >> Deploy_vps.sh
echo 'echo "✅ Развертывание завершено!"' >> Deploy_vps.sh
echo 'echo "📋 Полезные команды:"' >> Deploy_vps.sh
echo 'echo "  Запуск: sudo systemctl start wotcher-monitoring"' >> Deploy_vps.sh
echo 'echo "  Остановка: sudo systemctl stop wotcher-monitoring"' >> Deploy_vps.sh
echo 'echo "  Статус: sudo systemctl status wotcher-monitoring"' >> Deploy_vps.sh
echo 'echo "  Логи: sudo journalctl -u wotcher-monitoring -f"' >> Deploy_vps.sh
echo 'echo "  Перезапуск: sudo systemctl restart wotcher-monitoring"' >> Deploy_vps.sh