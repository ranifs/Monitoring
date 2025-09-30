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
    return fetch_all_items(url, headers)

def build_report_for_org(org_name, cameras):
    if not cameras:
        return None
    problem_lines = []
    no_archive_count = 0
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
        return None
    report = f"====================\n🏢 {org_name}\n====================\n"
    if no_archive_count == len(cameras):
        return {"type": "no_archive_all", "org_name": org_name}
    report += "\n".join(problem_lines)
    return {"type": "normal", "content": report}

# ===== Команда /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Начинаем мониторинг камер...")
    orgs = get_organizations()
    problem_reports = []
    no_archive_orgs = []

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
                no_archive_orgs.append(report["org_name"])
            else:
                problem_reports.append(report["content"])

    if no_archive_orgs:
        msg = f"❗️ НЕТ АРХИВА НА ВСЕХ КАМЕРАХ:\n\n" + "\n".join([f"🏢 {org}" for org in no_archive_orgs])
        await send_telegram_message(msg)

    if problem_reports:
        await send_telegram_message("✅ Некоторые камеры имеют проблемы:")
        for report in problem_reports:
            await send_telegram_message(report)
    elif not no_archive_orgs:
        await send_telegram_message("✅ Все камеры онлайн и с архивом.")

# ===== Main =====
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("🤖 Бот запущен. Ждем команду /start...")
    app.run_polling()

if __name__ == "__main__":
    main()
