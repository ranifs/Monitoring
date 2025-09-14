import sys, io
import locale
import os
import signal
import atexit
from datetime import datetime
import pytz

# Настройка кодировки для стабильной работы
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
else:
    # Для Linux/Unix систем
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Настройка московского времени
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

def get_moscow_time():
    """Возвращает текущее время в московском часовом поясе"""
    return datetime.now(MOSCOW_TZ)

def format_moscow_time():
    """Возвращает отформатированное московское время"""
    return get_moscow_time().strftime('%Y-%m-%d %H:%M:%S')

import requests
import time

# Глобальная переменная для отслеживания состояния
script_running = True
start_time = None

def signal_handler(signum, frame):
    global script_running
    print(f"\n❌ Получен сигнал {signum}, завершаем работу...")
    script_running = False
    sys.exit(0)

def cleanup():
    print("🧹 Выполняем очистку ресурсов...")
    # Закрываем все соединения
    import requests
    requests.Session().close()

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup)

# ======= Конфигурация =======
API_TOKEN = os.getenv("API_TOKEN", "1IWIwoxDUbCGEEZR6Lj6ExOY51U")
API_URL = os.getenv("API_URL", "https://cameras.sputnik.systems/vsaas/api/v2")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7557152702:AAEvMNfzLYWpkSdn7aXJp5qpPMR7aVySbE4")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", 588116427)

# Организации, которые нужно исключить из проверки
EXCLUDED_ORG_NAMES = ["ZZCameras", "Test Organization"]

# ======= Функции для работы с API =======
def get_json_with_retries(url, headers=None, retries=3, timeout=(5, 15)):
    import ssl
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    # Создаем сессию с повторными попытками
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    for attempt in range(retries):
        try:
            # Добавляем SSL контекст для более стабильной работы
            resp = session.get(url, headers=headers, timeout=timeout, verify=True)
            resp.raise_for_status()
            return resp.json()
        except (requests.exceptions.SSLError, ssl.SSLError) as e:
            print(f"⚠ SSL ошибка на попытке {attempt+1}/{retries}: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Экспоненциальная задержка
                continue
            else:
                # Fallback на небезопасное соединение
                try:
                    resp = session.get(url, headers=headers, timeout=timeout, verify=False)
                    resp.raise_for_status()
                    return resp.json()
                except Exception as fallback_e:
                    print(f"❌ Fallback тоже не удался: {fallback_e}")
                    raise e
        except Exception as e:
            print(f"⚠ Попытка {attempt+1}/{retries} не удалась: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Экспоненциальная задержка
            else:
                raise e
    
    raise Exception(f"Не удалось получить данные с {url} после {retries} попыток")

def fetch_all_items(base_url, headers, limit=100):
    """Обходит все страницы и возвращает полный список"""
    offset = 0
    all_items = []
    page_count = 0
    
    while True:
        page_count += 1
        url = f"{base_url}&limit={limit}&offset={offset}"
        print(f"🔄 Страница {page_count}: {url}")
        
        try:
            data = get_json_with_retries(url, headers=headers, timeout=(5, 10))
            if not isinstance(data, list):
                print(f"⚠ Неожиданный формат данных на странице {page_count}: {data}")
                break
                
            if not data:
                print(f"✅ Страница {page_count} пуста, завершаем загрузку")
                break
                
            all_items.extend(data)
            print(f"📄 Страница {page_count}: получено {len(data)} элементов, всего: {len(all_items)}")
            
            if len(data) < limit:
                print(f"✅ Последняя страница {page_count} с {len(data)} элементами")
                break
                
            offset += limit
            
            # Небольшая пауза между запросами
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Ошибка на странице {page_count}: {e}")
            break
    
    print(f"📊 Загружено {len(all_items)} элементов с {page_count} страниц")
    return all_items

def get_organizations():
    """Получает список всех организаций"""
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    base_url = f"{API_URL}/organizations"
    return fetch_all_items(base_url, headers)

def get_cameras_for_org(org_id):
    """Получает список камер для организации"""
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    base_url = f"{API_URL}/cameras?organization_id={org_id}"
    return fetch_all_items(base_url, headers)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        resp = requests.post(url, data=data, timeout=(5, 10))
        resp.raise_for_status()
        print(f"✅ Отправлено в Telegram: {message[:50]}...")
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")

def check_cameras_for_org(org_name, org_id):
    """Проверяет камеры организации и возвращает список проблем"""
    try:
        cams_data = get_cameras_for_org(org_id)
        if not isinstance(cams_data, list):
            return [f"⚠ {org_name}: формат данных камер не список"]
        
        if not cams_data:
            return [f"ℹ {org_name}: нет камер"]
        
        print(f"🛠 Первая камера: {cams_data[0]}")
        
        problems = []
        offline_cams = []
        no_archive_cams = []
        
        for cam in cams_data:
            cam_name = cam.get("title", cam.get("name", "Без названия"))
            
            # Проверяем статус подключения
            stream_status = cam.get("stream_status", {})
            if not stream_status.get("alive", False):
                offline_cams.append(cam_name)
            
            # Проверяем архив
            archive = cam.get("dvr_depth", 0) > 0
            if not archive:
                no_archive_cams.append(cam_name)
        
        # Формируем отчеты
        if offline_cams:
            problems.append(f"❌ {org_name}: камеры офлайн - {', '.join(offline_cams)}")
        
        if no_archive_cams:
            problems.append(f"❗️ {org_name}: нет архива на камерах - {', '.join(no_archive_cams)}")
        
        return problems
        
    except Exception as e:
        return [f"❌ {org_name}: ошибка проверки - {e}"]

# ======= Основная функция =======
def main():
    global script_running, start_time
    start_time = time.time()
    
    print(f"🚀 Запуск скрипта мониторинга камер в {format_moscow_time()}")
    
    try:
        orgs = get_organizations()
        if not isinstance(orgs, list):
            raise Exception("Неожиданный формат данных организаций")

        problem_reports = []
        total_orgs = len(orgs)
        processed_orgs = 0
        
        print(f"📊 Начинаем обработку {total_orgs} организаций...")
        
        # Отправляем уведомление о начале мониторинга
        send_telegram_message(f"🚀 Начинаем мониторинг камер\n⏰ Время запуска: {format_moscow_time()}")
        
        for org in orgs:
            # Проверяем, не был ли скрипт остановлен
            if not script_running:
                print("❌ Скрипт был остановлен, завершаем работу")
                break
                
            processed_orgs += 1
            elapsed_time = time.time() - start_time
            
            # Heartbeat каждые 30 секунд
            if int(elapsed_time) % 30 == 0:
                print(f"⏱️ Прошло {elapsed_time:.1f}с, обработано {processed_orgs}/{total_orgs} организаций")
            
            if elapsed_time > 300: # 5 минут
                print(f"⏰ Превышено время выполнения скрипта ({elapsed_time:.1f}с)")
                raise TimeoutError("Превышено время выполнения скрипта")
            try:
                org_name = org.get("name") or org.get("title") or org.get("label")
                org_id = org.get("id")

                if not org_name or not org_id:
                    print(f"⚠ Пропускаем организацию без имени или ID: {org}")
                    continue

                if org_name in EXCLUDED_ORG_NAMES:
                    print(f"⏩ Пропускаем организацию: {org_name} (id={org_id})")
                    continue

                print(f"🔎 Обрабатываем организацию: {org_name} (id={org_id})")
                cams_data = get_cameras_for_org(org_id)
                if not isinstance(cams_data, list):
                    print(f"⚠ Пропуск {org_name}: формат данных камер не список")
                    continue
                if not cams_data:
                    print(f"ℹ В организации {org_name} нет камер.")
                    continue

                print(f"🛠 Первая камера: {cams_data[0]}")
                
                problems = []
                offline_cams = []
                no_archive_cams = []
                
                for cam in cams_data:
                    cam_name = cam.get("title", cam.get("name", "Без названия"))
                    
                    # Проверяем статус подключения
                    stream_status = cam.get("stream_status", {})
                    if not stream_status.get("alive", False):
                        offline_cams.append(cam_name)
                    
                    # Проверяем архив
                    archive = cam.get("dvr_depth", 0) > 0
                    if not archive:
                        no_archive_cams.append(cam_name)
                
                # Формируем отчеты
                if offline_cams:
                    problems.append(f"❌ {org_name}: камеры офлайн - {', '.join(offline_cams)}")
                
                if no_archive_cams:
                    problems.append(f"❗️ {org_name}: нет архива на камерах - {', '.join(no_archive_cams)}")
                
                problem_reports.extend(problems)
                
                # Отправляем проблемы в Telegram
                for problem in problems:
                    send_telegram_message(problem)
                    
            except Exception as e:
                error_msg = f"❌ Ошибка обработки организации {org_name}: {e}"
                print(error_msg)
                problem_reports.append(error_msg)
                send_telegram_message(error_msg)

        # Отправляем сводный отчет о проблемах с архивом
        no_archive_orgs = []
        for report in problem_reports:
            if "нет архива на камерах" in report:
                org_name = report.split(": ")[0].replace("❗️ ", "")
                no_archive_orgs.append(org_name)
        
        if no_archive_orgs:
            summary_message = f"📋 Сводка по домам без архива ({len(no_archive_orgs)} домов):\n" + "\n".join(no_archive_orgs)
            send_telegram_message(summary_message)

        # Отправляем финальное сообщение
        if problem_reports:
            send_telegram_message(f"📊 Мониторинг завершен. Найдено проблем: {len(problem_reports)}")
        else:
            send_telegram_message("✅ Все камеры онлайн и с архивом.")

        # Финальная статистика
        total_time = time.time() - start_time
        print(f"✅ Скрипт завершен успешно за {total_time:.1f} секунд")
        print(f"📊 Обработано организаций: {processed_orgs}/{total_orgs}")
        print(f"📨 Отправлено отчетов: {len(problem_reports)}")

    except TimeoutError as e:
        total_time = time.time() - start_time
        print(f"❌ Время выполнения превысило лимит: {e} (прошло {total_time:.1f}с)")
    except KeyboardInterrupt:
        total_time = time.time() - start_time
        print(f"❌ Прервано пользователем (прошло {total_time:.1f}с)")
    except Exception as e:
        total_time = time.time() - start_time
        print(f"❌ Общая ошибка: {e} (прошло {total_time:.1f}с)")
        send_telegram_message(f"❌ Критическая ошибка мониторинга: {e}")

if __name__ == "__main__":
    main()