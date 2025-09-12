# Развертывание мониторинга камер на VPS

## Преимущества VPS перед Render

✅ **Стабильность**: VPS работает 24/7 без ограничений по времени  
✅ **Контроль**: Полный контроль над сервером и процессами  
✅ **Производительность**: Выделенные ресурсы, нет конкуренции  
✅ **Гибкость**: Возможность настройки cron, логирования, мониторинга  
✅ **Экономичность**: Дешевле для долгосрочного использования  

## Быстрое развертывание

### 1. Подготовка VPS

```bash
# Загрузите файлы на VPS (например, через scp)
scp -r /path/to/project user@your-vps-ip:/home/user/

# Подключитесь к VPS
ssh user@your-vps-ip
```

### 2. Автоматическое развертывание

```bash
# Сделайте скрипт исполняемым
chmod +x deploy_vps.sh

# Запустите развертывание
./deploy_vps.sh
```

### 3. Настройка переменных окружения

```bash
# Скопируйте пример файла
cp .env.example .env

# Отредактируйте .env файл
nano .env
```

### 4. Запуск сервиса

```bash
# Запустите сервис
sudo systemctl start wotcher-monitoring

# Проверьте статус
sudo systemctl status wotcher-monitoring

# Посмотрите логи
sudo journalctl -u wotcher-monitoring -f
```

## Ручное развертывание

Если автоматический скрипт не работает:

```bash
# 1. Обновите систему
sudo apt update && sudo apt upgrade -y

# 2. Установите Python
sudo apt install python3 python3-pip python3-venv -y

# 3. Создайте директорию
sudo mkdir -p /opt/wotcher_monitoring
sudo chown $USER:$USER /opt/wotcher_monitoring

# 4. Скопируйте файлы
cp -r * /opt/wotcher_monitoring/
cd /opt/wotcher_monitoring

# 5. Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# 6. Установите зависимости
pip install -r requirements.txt

# 7. Создайте systemd сервис
sudo nano /etc/systemd/system/wotcher-monitoring.service
```

## Управление сервисом

```bash
# Запуск
sudo systemctl start wotcher-monitoring

# Остановка
sudo systemctl stop wotcher-monitoring

# Перезапуск
sudo systemctl restart wotcher-monitoring

# Статус
sudo systemctl status wotcher-monitoring

# Автозапуск
sudo systemctl enable wotcher-monitoring

# Отключить автозапуск
sudo systemctl disable wotcher-monitoring
```

## Просмотр логов

```bash
# Последние логи
sudo journalctl -u wotcher-monitoring

# Логи в реальном времени
sudo journalctl -u wotcher-monitoring -f

# Логи за последний час
sudo journalctl -u wotcher-monitoring --since "1 hour ago"
```

## Настройка автоматического запуска по расписанию

Если нужно запускать по расписанию вместо постоянной работы:

```bash
# Откройте crontab
crontab -e

# Добавьте строку для запуска каждые 5 минут
*/5 * * * * cd /opt/wotcher_monitoring && /opt/wotcher_monitoring/venv/bin/python wotcher_monitoring.py
```

## Мониторинг ресурсов

```bash
# Использование CPU и памяти
htop

# Использование диска
df -h

# Сетевые соединения
netstat -tulpn
```

## Обновление скрипта

```bash
# Остановите сервис
sudo systemctl stop wotcher-monitoring

# Скопируйте новые файлы
cp new_wotcher_monitoring.py /opt/wotcher_monitoring/wotcher_monitoring.py

# Запустите сервис
sudo systemctl start wotcher-monitoring
```

## Устранение неполадок

### Проблема: Сервис не запускается
```bash
# Проверьте статус
sudo systemctl status wotcher-monitoring

# Посмотрите логи
sudo journalctl -u wotcher-monitoring -n 50
```

### Проблема: Ошибки Python
```bash
# Проверьте виртуальное окружение
source /opt/wotcher_monitoring/venv/bin/activate
python --version
pip list
```

### Проблема: Нет доступа к API
```bash
# Проверьте сетевые соединения
curl -I https://cameras.sputnik.systems

# Проверьте переменные окружения
cat /opt/wotcher_monitoring/.env
```

## Рекомендации по безопасности

1. **Настройте файрвол**:
   ```bash
   sudo ufw enable
   sudo ufw allow ssh
   sudo ufw allow 80
   sudo ufw allow 443
   ```

2. **Используйте SSH ключи** вместо паролей

3. **Регулярно обновляйте систему**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

4. **Настройте мониторинг дискового пространства**

5. **Сделайте резервные копии** конфигурационных файлов