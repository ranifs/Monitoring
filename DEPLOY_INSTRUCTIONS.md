# 🚀 Инструкция по развертыванию мониторинга камер на VPS

## ✅ Преимущества VPS перед Render

- **Стабильность**: Работает 24/7 без ограничений по времени
- **Контроль**: Полный контроль над сервером и процессами  
- **Производительность**: Выделенные ресурсы, нет конкуренции
- **Гибкость**: Возможность настройки cron, логирования, мониторинга
- **Экономичность**: Дешевле для долгосрочного использования

## 📋 Что нужно для развертывания

1. **VPS сервер** (например, с https://ztv.su/store/vps-kvm-nvme-v-rf)
2. **Доступ по SSH** к серверу
3. **API токен** для системы камер
4. **Telegram бот** с токеном и chat_id

## 🔧 Быстрое развертывание

### Шаг 1: Подготовка файлов

Скачайте эти файлы на свой компьютер:
- `wotcher_monitoring_vps.py` - основной скрипт
- `requirements.txt` - зависимости
- `deploy_vps.sh` - скрипт автоматического развертывания
- `.env.example` - пример конфигурации

### Шаг 2: Загрузка на VPS

```bash
# Загрузите файлы на VPS (замените на ваши данные)
scp -r /path/to/project user@your-vps-ip:/home/user/

# Подключитесь к VPS
ssh user@your-vps-ip
```

### Шаг 3: Автоматическое развертывание

```bash
# Перейдите в папку с проектом
cd /home/user/project

# Сделайте скрипт исполняемым
chmod +x deploy_vps.sh

# Запустите развертывание
./deploy_vps.sh
```

### Шаг 4: Настройка конфигурации

```bash
# Скопируйте пример файла конфигурации
cp .env.example .env

# Отредактируйте конфигурацию
nano .env
```

Заполните `.env` файл:
```bash
# API ключи для доступа к системе камер
API_TOKEN=your_actual_api_token_here
API_URL=https://cameras.sputnik.systems/vsaas/api/v2

# Telegram настройки
TELEGRAM_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Исключенные организации (через запятую)
EXCLUDED_ORGS=ZZCameras,Test Organization
```

### Шаг 5: Запуск сервиса

```bash
# Запустите сервис
sudo systemctl start wotcher-monitoring

# Проверьте статус
sudo systemctl status wotcher-monitoring

# Включите автозапуск
sudo systemctl enable wotcher-monitoring

# Посмотрите логи
sudo journalctl -u wotcher-monitoring -f
```

## 🎛️ Управление сервисом

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

## 📊 Просмотр логов

```bash
# Последние логи
sudo journalctl -u wotcher-monitoring

# Логи в реальном времени
sudo journalctl -u wotcher-monitoring -f

# Логи за последний час
sudo journalctl -u wotcher-monitoring --since "1 hour ago"

# Логи за сегодня
sudo journalctl -u wotcher-monitoring --since today
```

## ⏰ Настройка автоматического запуска

### Вариант 1: Постоянная работа (рекомендуется)

Сервис уже настроен на постоянную работу. Он будет автоматически перезапускаться при сбоях.

### Вариант 2: Запуск по расписанию

Если нужно запускать по расписанию вместо постоянной работы:

```bash
# Остановите постоянный сервис
sudo systemctl stop wotcher-monitoring
sudo systemctl disable wotcher-monitoring

# Откройте crontab
crontab -e

# Добавьте строку для запуска каждые 5 минут
*/5 * * * * cd /opt/wotcher_monitoring && /opt/wotcher_monitoring/venv/bin/python wotcher_monitoring_vps.py
```

## 🔄 Обновление скрипта

```bash
# Остановите сервис
sudo systemctl stop wotcher-monitoring

# Скопируйте новые файлы
cp new_wotcher_monitoring_vps.py /opt/wotcher_monitoring/wotcher_monitoring_vps.py

# Запустите сервис
sudo systemctl start wotcher-monitoring
```

## 🛠️ Устранение неполадок

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

### Проблема: Telegram не работает
```bash
# Проверьте токен и chat_id
curl -X GET "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"

# Проверьте отправку сообщения
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
     -H "Content-Type: application/json" \
     -d '{"chat_id": "<YOUR_CHAT_ID>", "text": "Test message"}'
```

## 🔒 Рекомендации по безопасности

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

## 📈 Мониторинг ресурсов

```bash
# Использование CPU и памяти
htop

# Использование диска
df -h

# Сетевые соединения
netstat -tulpn

# Статус сервисов
systemctl status wotcher-monitoring
```

## 🎯 Результат работы

После успешного развертывания вы получите:

✅ **Автоматический мониторинг** всех камер в системе  
✅ **Уведомления в Telegram** о проблемах с камерами  
✅ **Московское время** во всех сообщениях  
✅ **Стабильную работу** 24/7  
✅ **Автоматический перезапуск** при сбоях  
✅ **Детальное логирование** всех операций  

## 📞 Поддержка

Если возникли проблемы:

1. Проверьте логи: `sudo journalctl -u wotcher-monitoring -f`
2. Проверьте статус сервиса: `sudo systemctl status wotcher-monitoring`
3. Проверьте конфигурацию: `cat /opt/wotcher_monitoring/.env`
4. Проверьте сетевое соединение: `curl -I https://cameras.sputnik.systems`

---

**Удачного развертывания! 🚀**