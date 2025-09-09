import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import time

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
def get_json_with_retries(url, headers=None, retries=3, timeout=30):
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"⚠ Попытка {attempt+1}/{retries} не удалась: {e}")
            time.sleep(2)
    raise Exception(f"Не удалось получить данные с {url}")

# ======= Постраничная загрузка =======
def fetch_all_items(base_url, headers, limit=100):
    """Обходит все страницы и возвращает полный список"""
    offset = 0
    all_items = []
    while True:
        url = f"{base_url}&limit={limit}&offset={offset}"
        print(f"🔄 Загружаем {url}")
        data = get_json_with_retries(url, headers=headers)
        if not isinstance(data, list):
            print("⚠ Неожиданный формат данных:", data)
            break
        if not data:
            break
        all_items.extend(data)
        if len(data) < limit:
            break
        offset += limit
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
    if no_archive_count == len(cameras):
        report += "❗ Нет архива на всех камерах!\n"
    else:
        report += "\n".join(problem_lines)
    return report

# ======= Основная функция =======
def main():
    start_time = time.time()
    try:
        orgs = get_organizations()
        if not isinstance(orgs, list):
            raise Exception("Неожиданный формат данных организаций")

        problem_reports = []
        for org in orgs:
            if time.time() - start_time > 300: # 5 минут
                raise TimeoutError("Превышено время выполнения скрипта")
            try:
                org_name = org.get("name") or org.get("title") or org.get("label")
                org_id = org.get("id")

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

                # Лог первой камеры
                print(f"🛠 Первая камера: {cams_data[0]}")

                report = build_report_for_org(org_name, cams_data)
                if report:
                    problem_reports.append(report)

            except Exception as e:
                print(f"⚠ Ошибка при обработке {org.get('name')}: {e}")
                continue

        if problem_reports:
            send_telegram_message("✅ Большинство камер онлайн и с архивом.")
            for report in problem_reports:
                send_telegram_message(report)
        else:
            send_telegram_message("✅ Все камеры онлайн и с архивом.")

    except TimeoutError as e:
        print(f"❌ Время выполнения превысило лимит: {e}")
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")

if __name__ == "__main__":
    main()