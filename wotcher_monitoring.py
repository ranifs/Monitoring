import sys, io
import locale
import os
import signal
import atexit

# Настройка кодировки для стабильной работы
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
else:
    # Для Linux/Unix систем
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

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
    # Закрываем все открытые соединения
    import requests
    requests.Session().close()

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup)

# ✅ Твои токены
TELEGRAM_BOT_TOKEN = "7557152702:AAEvMNfzLYWpkSdn7aXJp5qpPMR7aVySbE4"
TELEGRAM_CHAT_ID = 588116427
SPUTNIK_API_TOKEN = "1IWIwoxDUbCGEEZR6Lj6ExOY51U"

EXCLUDED_ORG_NAMES = ["ZZCameras"]

# ======= Telegram =======
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    max_length = 4000
    parts = [text[i:i + max_length] for i in range(0, len(text), max_length)]
    for part in parts:
        try:
            print(f"📨 Отправляем сообщение длиной {len(part)} символов...")
            resp = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": part}, timeout=30)
            resp.raise_for_status()
            time.sleep(0.5)
        except Exception as e:
            print(f"⚠ Ошибка отправки в Telegram: {e}")

# ======= Универсальный GET =======
def get_json_with_retries(url, headers=None, retries=3, timeout=15):
    import ssl
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    from urllib3.poolmanager import PoolManager
    
    # Создаем сессию с более строгими настройками
    session = requests.Session()
    
    # Настройка пула соединений для предотвращения зависаний
    retry_strategy = Retry(
        total=retries,
        backoff_factor=0.5,  # Уменьшаем время ожидания
        status_forcelist=[429, 500, 502, 503, 504],
        connect=2,  # Максимум 2 попытки подключения
        read=2,     # Максимум 2 попытки чтения
    )
    
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,  # Ограничиваем количество соединений
        pool_maxsize=10,
        pool_block=False
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    for attempt in range(retries):
        try:
            print(f"🔄 Попытка {attempt+1}/{retries} для {url}")
            # Более короткий таймаут
            resp = session.get(
                url, 
                headers=headers, 
                timeout=(5, timeout),  # (connect_timeout, read_timeout)
                verify=True,
                stream=False  # Отключаем streaming для более быстрого ответа
            )
            resp.raise_for_status()
            result = resp.json()
            print(f"✅ Успешно получены данные с {url}")
            return result
            
        except (requests.exceptions.SSLError, ssl.SSLError) as e:
            print(f"⚠ SSL ошибка на попытке {attempt+1}/{retries}: {e}")
            if attempt < retries - 1:
                time.sleep(1)  # Уменьшаем время ожидания
            else:
                # Последняя попытка - пробуем без SSL проверки
                try:
                    print(f"🔄 Последняя попытка без SSL проверки для {url}")
                    resp = session.get(url, headers=headers, timeout=(5, timeout), verify=False)
                    resp.raise_for_status()
                    result = resp.json()
                    print(f"✅ Успешно получены данные без SSL проверки с {url}")
                    return result
                except Exception as final_e:
                    print(f"❌ Финальная попытка не удалась: {final_e}")
                    raise Exception(f"Не удалось получить данные с {url}")
                    
        except requests.exceptions.Timeout as e:
            print(f"⏰ Таймаут на попытке {attempt+1}/{retries}: {e}")
            if attempt < retries - 1:
                time.sleep(1)
            else:
                raise Exception(f"Таймаут при получении данных с {url}")
                
        except requests.exceptions.ConnectionError as e:
            print(f"🔌 Ошибка соединения на попытке {attempt+1}/{retries}: {e}")
            if attempt < retries - 1:
                time.sleep(2)
            else:
                raise Exception(f"Ошибка соединения с {url}")
                
        except Exception as e:
            print(f"⚠ Попытка {attempt+1}/{retries} не удалась: {e}")
            if attempt < retries - 1:
                time.sleep(1)
            else:
                raise Exception(f"Не удалось получить данные с {url}")
    
    # Закрываем сессию для освобождения ресурсов
    session.close()
    raise Exception(f"Не удалось получить данные с {url}")

# ======= Постраничная загрузка =======
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
            data = get_json_with_retries(url, headers=headers, timeout=10)  # Уменьшенный таймаут
        except Exception as e:
            print(f"❌ Ошибка загрузки страницы {page_count}: {e}")
            break
            
        if not isinstance(data, list):
            print(f"⚠ Неожиданный формат данных на странице {page_count}:", data)
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
        
        # Защита от бесконечного цикла
        if page_count > 100:  # Максимум 100 страниц
            print(f"⚠ Достигнут лимит страниц ({page_count}), прерываем загрузку")
            break
            
        # Небольшая пауза между страницами
        time.sleep(0.1)
        
    print(f"📊 Загружено {len(all_items)} элементов с {page_count} страниц")
    return all_items

# ======= Организации =======
def get_organizations():
    base_url = "https://cameras.sputnik.systems/vsaas/api/v2/organizations?dummy=1"
    headers = {"Authorization": f"Bearer {SPUTNIK_API_TOKEN}"}
    return fetch_all_items(base_url, headers, limit=100)

# ======= Камеры =======
def get_cameras_for_org(org_id):
    base_url = f"https://cameras.sputnik.systems/vsaas/api/v2/cameras?organization_id={org_id}"
    headers = {"Authorization": f"Bearer {SPUTNIK_API_TOKEN}"}
    return fetch_all_items(base_url, headers, limit=100)

def to_bool(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return val != 0
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes", "on")
    return False

# ======= Формируем отчёт =======
def build_report_for_org(org_name: str, cameras: list):
    if not cameras:
        return None
    problem_lines = []
    no_archive_count = 0
    no_archive_orgs = []
    
    for cam in cameras:
        cam_name = cam.get("name") or cam.get("title") or cam.get("label") or cam.get("id") or "(Без имени)"
        online = cam.get("stream_status", {}).get("alive", False)
        archive = cam.get("dvr_depth", 0) > 0
        problems = []
        if not online:
            problems.append("❌ Нет онлайн")
        if not archive:
            no_archive_count += 1
            problems.append("❌ Нет архива")
        if problems:
            problem_lines.append(f"📍 {cam_name} — {', '.join(problems)}")
    
    if not problem_lines:
        return None  # Нет проблемных камер — не выводим организацию
    
    report = f"====================\n🏢 {org_name}\n====================\n"
    
    # Проверяем, если нет архива на всех камерах
    if no_archive_count == len(cameras):
        return {"type": "no_archive_all", "org_name": org_name}
    else:
        report += "\n".join(problem_lines)
        return {"type": "normal", "content": report}

# ======= Основная функция =======
def main():
    global script_running, start_time
    start_time = time.time()
    
    print(f"🚀 Запуск скрипта мониторинга камер в {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Отправляем уведомление о начале мониторинга
    try:
        start_message = f"🚀 Начинаем мониторинг камер\n⏰ Время запуска: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        send_telegram_message(start_message)
        print("📨 Отправлено уведомление о начале мониторинга")
    except Exception as e:
        print(f"⚠ Не удалось отправить уведомление о начале: {e}")
    
    try:
        orgs = get_organizations()
        if not isinstance(orgs, list):
            raise Exception("Неожиданный формат данных организаций")

        problem_reports = []
        no_archive_orgs = []  # Список организаций без архива на всех камерах
        total_orgs = len(orgs)
        processed_orgs = 0
        
        print(f"📊 Начинаем обработку {total_orgs} организаций...")
        
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

                # Лог первой камеры (только если есть камеры)
                if cams_data:
                    print(f"🛠 Первая камера: {cams_data[0]}")

                report = build_report_for_org(org_name, cams_data)
                if report:
                    if report["type"] == "no_archive_all":
                        no_archive_orgs.append(report["org_name"])
                    else:
                        problem_reports.append(report["content"])

            except KeyboardInterrupt:
                print("❌ Прервано пользователем")
                break
            except Exception as e:
                print(f"⚠ Ошибка при обработке {org.get('name', 'Unknown')}: {e}")
                continue

        # 2. Отправляем отчеты в правильном порядке
        if no_archive_orgs:
            # Сначала отправляем сообщение о домах без архива
            no_archive_message = f"❗️ НЕТ АРХИВА НА ВСЕХ КАМЕРАХ:\n\n" + "\n".join([f"🏢 {org}" for org in no_archive_orgs])
            send_telegram_message(no_archive_message)
            print(f"📨 Отправлено сообщение о {len(no_archive_orgs)} домах без архива")
        
        if problem_reports:
            # Затем отправляем обычные отчеты
            send_telegram_message("✅ Большинство камер онлайн и с архивом.")
            for report in problem_reports:
                send_telegram_message(report)
        elif not no_archive_orgs:
            # Если нет проблем вообще
            send_telegram_message("✅ Все камеры онлайн и с архивом.")

        # Финальная статистика
        total_time = time.time() - start_time
        print(f"✅ Скрипт завершен успешно за {total_time:.1f} секунд")
        print(f"📊 Обработано организаций: {processed_orgs}/{total_orgs}")
        print(f"📨 Отправлено отчетов: {len(problem_reports)}")
        print(f"🏢 Домов без архива: {len(no_archive_orgs)}")

    except TimeoutError as e:
        total_time = time.time() - start_time
        error_message = f"❌ Мониторинг прерван по таймауту (прошло {total_time:.1f}с)"
        print(error_message)
        try:
            send_telegram_message(error_message)
        except:
            pass
    except KeyboardInterrupt:
        total_time = time.time() - start_time
        error_message = f"❌ Мониторинг прерван пользователем (прошло {total_time:.1f}с)"
        print(error_message)
        try:
            send_telegram_message(error_message)
        except:
            pass
    except Exception as e:
        total_time = time.time() - start_time
        error_message = f"❌ Ошибка мониторинга: {e} (прошло {total_time:.1f}с)"
        print(error_message)
        try:
            send_telegram_message(error_message)
        except:
            pass
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()