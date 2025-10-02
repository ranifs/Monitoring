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

# ===== Конфигурация городов и групп =====
CITY_GROUPS = {
    "Альметьевск": {
        "chat_id": "@almetevsk_cameras",  # Замените на реальный никнейм группы
        "keywords": ["альметьевск", "алметьевск", "almetevsk"]
    },
    "Казань": {
        "chat_id": "@kazan_cameras",  # Замените на реальный никнейм группы
        "keywords": ["казань", "kazan", "казан"]
    },
    "Зеленодольск": {
        "chat_id": "@zelenodolsk_cameras",  # Замените на реальный никнейм группы
        "keywords": ["зеленодольск", "zelenodolsk", "зеленодольский"]
    },
    "Тюмень": {
        "chat_id": "@tyumen_cameras",  # Замените на реальный никнейм группы
        "keywords": ["тюмень", "tyumen", "тюмен"]
    }
}

# Дефолтная группа для неизвестных городов
DEFAULT_CHAT_ID = TELEGRAM_CHAT_ID

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

# ===== Определение города организации =====
def get_city_for_organization(org_name):
    """Определяет город организации по названию"""
    if not org_name:
        return None
    
    org_name_lower = org_name.lower()
    
    for city, config in CITY_GROUPS.items():
        for keyword in config["keywords"]:
            if keyword.lower() in org_name_lower:
                print(f"🏙️ Организация '{org_name}' относится к городу: {city}")
                return city
    
    print(f"❓ Город для организации '{org_name}' не определен")
    return None

def get_chat_id_for_city(city):
    """Получает chat_id для города"""
    if city and city in CITY_GROUPS:
        return CITY_GROUPS[city]["chat_id"]
    return DEFAULT_CHAT_ID

# ===== Telegram =====
async def send_telegram_message(text, chat_id=None):
    """Отправляет сообщение в указанную группу или по умолчанию"""
    if chat_id is None:
        chat_id = TELEGRAM_CHAT_ID
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    max_length = 4000
    parts = [text[i:i + max_length] for i in range(0, len(text), max_length)]
    for part in parts:
        try:
            print(f"📨 Отправляем сообщение длиной {len(part)} символов в {chat_id}...")
            requests.post(url, data={"chat_id": chat_id, "text": part}, timeout=30)
            time.sleep(0.5)
        except Exception as e:
            print(f"⚠ Ошибка отправки в Telegram ({chat_id}): {e}")

async def send_telegram_message_to_city(text, city):
    """Отправляет сообщение в группу города"""
    chat_id = get_chat_id_for_city(city)
    await send_telegram_message(text, chat_id)

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

def get_alternative_camera_name(cam):
    """Ищет альтернативное название для камер с UUID"""
    # Поля в порядке приоритета (title первым, так как содержит нужное название)
    alt_fields = [
        'title',  # Основное поле с нужным названием
        'label',
        'serial_number',
        'mac_address', 
        'device_id',
        'hardware_id',
        'model',
        'vendor',
        'location',
        'description',
        'alias',
        'nickname',
        'custom_name',
        'camera_name',
        'display_name',
        'friendly_name',
        'hostname',
        'ip_address',
        'port',
        'channel',
        'camera_id',
        'device_name'
    ]
    
    print(f"🔍 Ищем альтернативное название для UUID камеры. Доступные поля: {list(cam.keys())}")
    
    for field in alt_fields:
        if field in cam and cam[field]:
            alt_name = str(cam[field]).strip()
            if alt_name and len(alt_name) > 0:
                print(f"🔍 Найдено альтернативное название в поле '{field}': {alt_name}")
                return alt_name
    
    # Если не найдено, возвращаем None
    print(f"⚠️ Альтернативное название не найдено для UUID камеры")
    return None

def get_camera_display_name(cam):
    """Получает отображаемое название камеры"""
    # Приоритет: title, label, name, id
    # Если name - это UUID, используем title или другие поля
    
    main_name = cam.get("name")
    
    # Проверяем, является ли name UUID (формат: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
    if main_name and len(main_name) == 36 and main_name.count('-') == 4:
        # name - это UUID, ищем альтернативное название
        alt_name = get_alternative_camera_name(cam)
        if alt_name:
            return alt_name
        # Если альтернативное название не найдено, используем title
        title = cam.get("title")
        if title:
            return title
    
    # Если name не UUID или title не найден, используем стандартную логику
    display_name = cam.get("title") or cam.get("label") or cam.get("name") or cam.get("id") or "Unknown"
    return display_name

def analyze_recording_stability(cam_data):
    """Анализирует стабильность записи архива"""
    stability_issues = []
    
    # Проверяем различные поля, которые могут указывать на проблемы с записью
    recording_status = cam_data.get("recording_status", {})
    stream_status = cam_data.get("stream_status", {})
    
    # Проверяем статус записи
    if recording_status:
        if recording_status.get("active") == False:
            stability_issues.append("запись отключена")
        elif recording_status.get("paused") == True:
            stability_issues.append("запись приостановлена")
    
    # Проверяем качество потока
    if stream_status:
        if stream_status.get("quality", 100) < 80:
            stability_issues.append("плохое качество")
    
    # Проверяем размер архива (может указывать на перебои)
    archive_size = cam_data.get("archive_size", 0)
    dvr_depth = cam_data.get("dvr_depth", 0)
    
    # Если есть архив, но он очень маленький - возможны перебои
    if dvr_depth > 0 and archive_size > 0:
        # Предполагаем, что нормальный размер архива для 7 дней должен быть больше 1GB
        if archive_size < 1024 * 1024 * 1024:  # меньше 1GB
            stability_issues.append("маленький архив")
    
    # Проверяем наличие полей, указывающих на проблемы
    error_fields = ['error_count', 'connection_errors', 'recording_errors', 'stream_errors']
    for field in error_fields:
        if field in cam_data and cam_data[field] > 0:
            stability_issues.append(f"{field}: {cam_data[field]}")
    
    # Проверяем интервалы записи (если есть такие поля)
    recording_intervals = cam_data.get("recording_intervals", [])
    if recording_intervals:
        # Если есть много коротких интервалов - возможны перебои
        short_intervals = [i for i in recording_intervals if i < 60]  # меньше минуты
        if len(short_intervals) > len(recording_intervals) * 0.5:
            stability_issues.append("частые перебои записи")
    
    return stability_issues

def analyze_recent_recording_gaps(cam_data):
    """Анализирует перебои записи за последние 3 часа"""
    from datetime import datetime, timedelta
    
    # Ищем поля, которые могут содержать информацию о записи за последние 3 часа
    time_fields = [
        'last_activity',
        'last_seen', 
        'last_online',
        'last_connection',
        'last_ping',
        'last_update',
        'updated_at'
    ]
    
    # Проверяем, есть ли данные о последней активности
    last_activity = None
    for field in time_fields:
        if field in cam_data and cam_data[field]:
            last_activity = cam_data[field]
            break
    
    if not last_activity:
        # Если нет данных о времени, не показываем ложных проблем
        print(f"⚠️ Нет данных о времени для анализа перебоев записи")
        return None
    
    try:
        # Анализируем время последней активности
        if isinstance(last_activity, (int, float)):
            last_time = datetime.fromtimestamp(last_activity)
        else:
            last_time = datetime.fromisoformat(str(last_activity).replace('Z', '+00:00'))
        
        now = datetime.now()
        time_diff = now - last_time
        
        # Если последняя активность была больше 3 часов назад
        if time_diff > timedelta(hours=3):
            return f"нет активности {time_diff.days}д {time_diff.seconds//3600}ч"
        
        # Проверяем другие поля, которые могут указывать на перебои
        # Более строгие критерии для избежания ложных срабатываний
        gap_indicators = [
            'recording_gaps',
            'connection_gaps', 
            'stream_interruptions',
            'archive_gaps',
            'recording_intervals'
        ]
        
        for field in gap_indicators:
            if field in cam_data:
                value = cam_data[field]
                if isinstance(value, list) and len(value) > 0:
                    # Анализируем интервалы записи - только если много перерывов
                    recent_gaps = [gap for gap in value if gap > 120]  # перерывы больше 2 минут
                    if len(recent_gaps) > 5:  # больше 5 перерывов
                        return "частые перебои записи за 3ч"
                elif isinstance(value, (int, float)) and value > 10:  # больше 10 ошибок
                    return "есть перебои записи за 3ч"
        
        # Проверяем счетчики ошибок за последние часы
        error_fields = [
            'recent_errors',
            'connection_errors_3h',
            'recording_errors_3h',
            'stream_errors_3h'
        ]
        
        for field in error_fields:
            if field in cam_data and cam_data[field] > 10:  # больше 10 ошибок
                return "много ошибок за 3ч"
        
        return None
        
    except Exception as e:
        print(f"⚠️ Ошибка анализа перебоев записи: {e}")
        return None

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
        # Если нет данных о времени, не показываем ложное время
        print(f"⚠️ Нет данных о времени для определения offline статуса")
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
    cam_name = get_camera_display_name(cam)
    print(f"📹 Анализируем камеру: {cam_name}")
    
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
    else:
        offline_time = None
    
    # Анализируем стабильность записи
    stability_issues = analyze_recording_stability(cam)
    
    # Если есть проблемы со стабильностью, добавляем их
    if stability_issues:
        for issue in stability_issues:
            problems.append(f"⚠️ {issue}")
    
    # Проверяем перебои записи за последние 3 часа
    recording_gaps = analyze_recent_recording_gaps(cam)
    if recording_gaps:
        problems.append(f"⚠️ {recording_gaps}")
        print(f"🔍 Найдены перебои записи за последние 3 часа: {recording_gaps}")
        print(f"📋 Данные камеры {cam_name}: {list(cam.keys())}")
    
    return {
        "is_online": is_online,
        "has_archive": has_archive,
        "problems": problems,
        "dvr_depth": dvr_depth,
        "recording_enabled": recording_enabled,
        "archive_duration": format_archive_duration(dvr_depth),
        "offline_time": offline_time,
        "stability_issues": stability_issues
    }

def build_report_for_org(org_name, cameras):
    if not cameras:
        return None
    problem_lines = []
    no_archive_count = 0
    offline_count = 0
    archive_durations = []
    
    for cam in cameras:
        cam_name = get_camera_display_name(cam)
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

    # Отправляем сообщения по городам
    await send_reports_by_city(all_offline_orgs, no_archive_orgs, problem_reports)

async def send_reports_by_city(all_offline_orgs, no_archive_orgs, problem_reports):
    """Отправляет отчеты в соответствующие группы городов"""
    # Группируем организации по городам
    cities_data = {}
    
    # Обрабатываем организации без архива
    for org_data in no_archive_orgs:
        if isinstance(org_data, dict):
            org_name = org_data["org_name"]
            archive_duration = org_data.get("archive_duration", "0 дней")
        else:
            org_name = org_data
            archive_duration = "0 дней"
        
        city = get_city_for_organization(org_name)
        if city not in cities_data:
            cities_data[city] = {"no_archive": [], "offline": [], "problems": []}
        cities_data[city]["no_archive"].append(f"🏢 {org_name} - {archive_duration} архива")
    
    # Обрабатываем оффлайн организации
    for org_name in all_offline_orgs:
        city = get_city_for_organization(org_name)
        if city not in cities_data:
            cities_data[city] = {"no_archive": [], "offline": [], "problems": []}
        cities_data[city]["offline"].append(f"🏢 {org_name}")
    
    # Обрабатываем проблемные отчеты (пока отправляем в дефолтную группу)
    if problem_reports:
        if None not in cities_data:
            cities_data[None] = {"no_archive": [], "offline": [], "problems": []}
        cities_data[None]["problems"].extend(problem_reports)
    
    # Отправляем сообщения в соответствующие группы
    for city, data in cities_data.items():
        messages = []
        
        if data["offline"]:
            msg = f"🚨 ВСЕ КАМЕРЫ ОФФЛАЙН:\n\n" + "\n".join(data["offline"])
            messages.append(msg)
        
        if data["no_archive"]:
            msg = f"❗️ НЕТ АРХИВА НА ВСЕХ КАМЕРАХ:\n\n" + "\n".join(data["no_archive"])
            messages.append(msg)
        
        if data["problems"]:
            messages.append("⚠️ Некоторые камеры имеют проблемы:")
            messages.extend(data["problems"])
        
        # Если нет проблем, отправляем сообщение об успехе
        if not any([data["offline"], data["no_archive"], data["problems"]]):
            messages.append("✅ Все камеры онлайн и с архивом.")
        
        # Отправляем все сообщения в соответствующую группу
        for msg in messages:
            await send_telegram_message_to_city(msg, city)

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
