import sys, io, locale, os, signal, atexit
import requests, time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ===== Настройка кодировки =====
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
else:
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# ===== Глобальные переменные =====
script_running = True
start_time = None

# ===== Твои токены =====
TELEGRAM_TOKEN = "7557152702:AAEvMNfzLYWpkSdn7aXJp5qpPMR7aVySbE4"
TELEGRAM_CHAT_ID = 588116427
SPUTNIK_API_TOKEN = "1IWIwoxDUbCGEEZR6Lj6ExOY51U"

EXCLUDED_ORG_NAMES = ["ZZCameras"]

# ===== Обработчики сигналов =====
def signal_handler(signum, frame):
    global script_running
    print(f"\n❌ Получен сигнал {signum}, завершаем работу...")
    script_running = False
    sys.exit(0)

def cleanup():
    print("🧹 Очистка ресурсов...")
    requests.Session().close()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup)

# ===== Telegram =====
async def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    max_length = 4000
    parts = [text[i:i + max_length] for i in range(0, len(text), max_length)]
    for part in parts:
        try:
            print(f"📨 Отправляем сообщение длиной {len(part)} символов...")
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": part}, timeout=30)
            time.sleep(0.5)
        except Exception as e:
            print(f"⚠ Ошибка отправки в Telegram: {e}")

# ===== Универсальный GET с retries =====
def get_json_with_retries(url, headers=None, retries=3, timeout=15):
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    session = requests.Session()
    retry_strategy = Retry(total=retries, backoff_factor=0.5,
                           status_forcelist=[429,500,502,503,504], connect=2, read=2)
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    for attempt in range(retries):
        try:
            resp = session.get(url, headers=headers, timeout=(5, timeout))
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"⚠ Попытка {attempt+1}/{retries} не удалась: {e}")
            if attempt < retries - 1:
                time.sleep(1)
            else:
                raise
    session.close()
    raise Exception(f"Не удалось получить данные с {url}")

# ===== Постраничная загрузка =====
def fetch_all_items(base_url, headers, limit=100):
    offset = 0
    all_items = []
    page_count = 0
    while True:
        page_count += 1
        url = f"{base_url}&limit={limit}&offset={offset}"
        data = get_json_with_retries(url, headers=headers, timeout=10)
        if not isinstance(data, list) or not data:
            break
        all_items.extend(data)
        if len(data) < limit:
            break
        offset += limit
        time.sleep(0.1)
    return all_items

# ===== Sputnik API =====
def get_organizations():
    url = "https://cameras.sputnik.systems/vsaas/api/v2/organizations?dummy=1"
    headers = {"Authorization": f"Bearer {SPUTNIK_API_TOKEN}"}
    return fetch_all_items(url, headers)

def get_cameras_for_org(org_id):
    url = f"https://cameras.sputnik.systems/vsaas/api/v2/cameras?organization_id={org_id}"
    headers = {"Authorization": f"Bearer {SPUTNIK_API_TOKEN}"}
    try:
        cameras = fetch_all_items(url, headers)
        print(f"📹 Получено {len(cameras)} камер для организации {org_id}")
        return cameras
    except Exception as e:
        print(f"⚠️ Ошибка получения камер для организации {org_id}: {e}")
        return []

def format_archive_duration(dvr_depth):
    """Форматирует количество дней архива в читаемый вид"""
    if dvr_depth == 0:
        return "0 дней"
    elif dvr_depth < 1:
        # Если меньше дня, показываем часы
        hours = int(dvr_depth * 24)
        return f"{hours}ч"
    elif dvr_depth == int(dvr_depth):
        # Если целое число дней
        return f"{int(dvr_depth)} дней"
    else:
        # Если дробное число дней
        days = int(dvr_depth)
        hours = int((dvr_depth - days) * 24)
        if hours == 0:
            return f"{days} дней"
        else:
            return f"{days}д {hours}ч"

def format_offline_time(cam_data):
    """Форматирует время, сколько камера не работает"""
    # Ищем различные поля времени в данных камеры
    time_fields = [
        'last_activity',
        'last_seen', 
        'last_online',
        'last_connection',
        'last_ping',
        'last_update',
        'updated_at',
        'created_at',
        'timestamp'
    ]
    
    last_activity = None
    found_field = None
    
    for field in time_fields:
        if field in cam_data and cam_data[field]:
            last_activity = cam_data[field]
            found_field = field
            print(f"🔍 Найдено поле времени: {field} = {last_activity}")
            break
    
    if not last_activity:
        print(f"⚠️ Поле времени не найдено для определения offline статуса")
        return "неизвестно"
    
    try:
        from datetime import datetime
        import time
        
        # Предполагаем, что last_activity в Unix timestamp
        if isinstance(last_activity, (int, float)):
            last_time = datetime.fromtimestamp(last_activity)
        else:
            # Если это строка, пытаемся парсить
            last_time = datetime.fromisoformat(str(last_activity).replace('Z', '+00:00'))
        
        now = datetime.now()
        time_diff = now - last_time
        
        total_seconds = int(time_diff.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}с"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes}м"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            if minutes == 0:
                return f"{hours}ч"
            else:
                return f"{hours}ч {minutes}м"
        else:
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            if hours == 0:
                return f"{days}д"
            else:
                return f"{days}д {hours}ч"
                
    except Exception as e:
        print(f"⚠️ Ошибка форматирования времени offline: {e}")
        return "неизвестно"

def check_camera_status(cam):
    """Улучшенная проверка статуса камеры"""
    problems = []
    
    # Получаем название камеры
    cam_name = cam.get("name") or cam.get("title") or cam.get("id") or "Unknown"
    
    # Проверяем различные статусы подключения
    stream_status = cam.get("stream_status", {})
    connection_status = cam.get("connection_status", {})
    recording_status = cam.get("recording_status", {})
    
    # Проверка онлайн статуса
    is_online = False
    if stream_status.get("alive", False):
        is_online = True
    elif connection_status.get("connected", False):
        is_online = True
    elif stream_status.get("status") == "active":
        is_online = True
    
    if not is_online:
        problems.append("❌ Не онлайн")
    
    # Проверка архива - более детальная
    has_archive = False
    archive_problems = []
    
    # Проверяем различные поля архива
    dvr_depth = cam.get("dvr_depth", 0)
    archive_size = cam.get("archive_size", 0)
    recording_enabled = cam.get("recording_enabled", False)
    
    if dvr_depth > 0:
        has_archive = True
    elif archive_size > 0:
        has_archive = True
    elif recording_enabled:
        has_archive = True
    elif recording_status.get("active", False):
        has_archive = True
    
    if not has_archive:
        archive_problems.append("❌ Не пишет")
        # Дополнительная диагностика
        if dvr_depth == 0:
            archive_problems.append("(dvr_depth=0)")
        if not recording_enabled:
            archive_problems.append("(запись отключена)")
    
    problems.extend(archive_problems)
    
    # Проверка качества сигнала
    signal_quality = cam.get("signal_quality", {})
    if signal_quality.get("level", 100) < 50:
        problems.append("⚠️ Слабое качество сигнала")
    
    # Проверка последней активности
    last_activity = cam.get("last_activity")
    offline_time = "неизвестно"
    
    if last_activity:
        try:
            from datetime import datetime, timedelta
            import time
            # Предполагаем, что last_activity в Unix timestamp
            last_time = datetime.fromtimestamp(last_activity)
            if datetime.now() - last_time > timedelta(hours=1):
                problems.append("⚠️ Нет активности >1ч")
        except:
            pass
    
    # Определяем время offline
    if not is_online:
        offline_time = format_offline_time(cam)
    
    return {
        "is_online": is_online,
        "has_archive": has_archive,
        "problems": problems,
        "dvr_depth": dvr_depth,
        "recording_enabled": recording_enabled,
        "archive_duration": format_archive_duration(dvr_depth),
        "offline_time": offline_time
    }

def build_report_for_org(org_name, cameras):
    if not cameras:
        return None
    problem_lines = []
    no_archive_count = 0
    offline_count = 0
    archive_durations = []
    
    for cam in cameras:
        cam_name = cam.get("name") or cam.get("title") or cam.get("label") or cam.get("id") or "(Без имени)"
        status = check_camera_status(cam)
        
        if not status["is_online"]:
            offline_count += 1
        if not status["has_archive"]:
            no_archive_count += 1
        
        # Собираем информацию о днях архива
        archive_durations.append(status["archive_duration"])
            
        if status["problems"]:
            # Добавляем информацию о днях архива к проблемам
            problems_with_archive = []
            for problem in status["problems"]:
                if "Не пишет" in problem:
                    problems_with_archive.append(f"{problem} {status['archive_duration']}")
                elif "Не онлайн" in problem:
                    # Для оффлайн камер показываем время offline
                    offline_info = f" {status['offline_time']}" if status['offline_time'] != "неизвестно" else ""
                    problems_with_archive.append(f"{problem}{offline_info}")
                else:
                    problems_with_archive.append(problem)
            
            # Добавляем информацию об архиве в конце, если есть проблемы
            archive_info = f" ({status['archive_duration']} архива)"
            problem_lines.append(f"📍 {cam_name} — {', '.join(problems_with_archive)}{archive_info}")
    
    if not problem_lines:
        return None
    
    # Определяем общую продолжительность архива для организации
    if archive_durations:
        # Берем минимальную продолжительность архива (самую проблемную)
        min_archive = min(archive_durations)
    else:
        min_archive = "0 дней"
    
    # Специальные случаи
    if no_archive_count == len(cameras):
        return {"type": "no_archive_all", "org_name": org_name, "archive_duration": min_archive}
    if offline_count == len(cameras):
        return {"type": "all_offline", "org_name": org_name}
    
    report = f"====================\n🏢 {org_name}\n====================\n"
    report += "\n".join(problem_lines)
    return {"type": "normal", "content": report}

# ===== Команда /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Начинаем мониторинг камер...")
    
    try:
        orgs = get_organizations()
        print(f"🏢 Получено {len(orgs)} организаций")
    except Exception as e:
        await send_telegram_message(f"❌ Ошибка получения организаций: {e}")
        return
    
    problem_reports = []
    no_archive_orgs = []

    # Обработка специальных случаев
    no_archive_orgs = []
    all_offline_orgs = []
    
    for org in orgs:
        org_name = org.get("name") or org.get("title") or org.get("label")
        org_id = org.get("id")
        if not org_name or not org_id or org_name in EXCLUDED_ORG_NAMES:
            continue
        cams_data = get_cameras_for_org(org_id)
        if not cams_data:
            continue
        report = build_report_for_org(org_name, cams_data)
        if report:
            if report["type"] == "no_archive_all":
                no_archive_orgs.append(report)
            elif report["type"] == "all_offline":
                all_offline_orgs.append(report["org_name"])
            else:
                problem_reports.append(report["content"])

    # Отправляем сообщения
    if all_offline_orgs:
        msg = f"🚨 ВСЕ КАМЕРЫ ОФФЛАЙН:\n\n" + "\n".join([f"🏢 {org}" for org in all_offline_orgs])
        await send_telegram_message(msg)
    
    if no_archive_orgs:
        # Собираем информацию о днях архива для каждой организации
        no_archive_lines = []
        for org_data in no_archive_orgs:
            if isinstance(org_data, dict):
                org_name = org_data["org_name"]
                archive_duration = org_data.get("archive_duration", "0 дней")
                no_archive_lines.append(f"🏢 {org_name} - {archive_duration} архива")
            else:
                no_archive_lines.append(f"🏢 {org_data}")
        
        msg = f"❗️ НЕТ АРХИВА НА ВСЕХ КАМЕРАХ:\n\n" + "\n".join(no_archive_lines)
        await send_telegram_message(msg)

    if problem_reports:
        await send_telegram_message("⚠️ Некоторые камеры имеют проблемы:")
        for report in problem_reports:
            await send_telegram_message(report)
    elif not no_archive_orgs and not all_offline_orgs:
        await send_telegram_message("✅ Все камеры онлайн и с архивом.")

# ===== Команда /test_org =====
async def test_org(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестирование конкретной организации"""
    if not context.args:
        await update.message.reply_text("❌ Укажите ID организации: /test_org <org_id>")
        return
    
    org_id = context.args[0]
    await update.message.reply_text(f"🔍 Тестируем организацию {org_id}...")
    
    try:
        cams_data = get_cameras_for_org(org_id)
        if not cams_data:
            await send_telegram_message(f"❌ Камеры не найдены для организации {org_id}")
            return
        
        # Получаем название организации
        orgs = get_organizations()
        org_name = "Неизвестная организация"
        for org in orgs:
            if org.get("id") == org_id:
                org_name = org.get("name") or org.get("title") or org.get("label")
                break
        
        report = build_report_for_org(org_name, cams_data)
        if report:
            if report["type"] == "no_archive_all":
                await send_telegram_message(f"❗️ В организации {org_name} НЕТ АРХИВА НА ВСЕХ КАМЕРАХ")
            elif report["type"] == "all_offline":
                await send_telegram_message(f"🚨 В организации {org_name} ВСЕ КАМЕРЫ ОФФЛАЙН")
            else:
                await send_telegram_message(f"⚠️ Проблемы в организации {org_name}:")
                await send_telegram_message(report["content"])
        else:
            await send_telegram_message(f"✅ В организации {org_name} все камеры работают нормально")
            
    except Exception as e:
        await send_telegram_message(f"❌ Ошибка тестирования организации {org_id}: {e}")

# ===== Main =====
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test_org", test_org))
    print("🤖 Бот запущен. Доступные команды:")
    print("  /start - полный мониторинг всех камер")
    print("  /test_org <org_id> - тестирование конкретной организации")
    app.run_polling()

if __name__ == "__main__":
    main()
