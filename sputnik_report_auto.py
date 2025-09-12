import requests
import time
import re

TELEGRAM_BOT_TOKEN = "7557152702:AAEvMNfzLYWpkSdn7aXJp5qpPMR7aVySbE4"
TELEGRAM_CHAT_ID = 588116427
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl91dWlkIjoiIiwiZW50aXR5X3V1aWQiOiIyMjI5IiwiZW50aXR5X3R5cGUiOiJ1c2VyIiwiZW50aXR5X3JlZl91dWlkIjoiYWRlZmZiNDctMTcwNy00OTc2LWE0YTYtZTZlYWNmMTliMDUwIiwiZW50aXR5X25hbWUiOiIiLCJzYWx0IjoiN2VkZWVlOTUifQ.hcDDlG0kufBzzArjCsCD9-cVe5j9XtCfo_mAEYXajOE"


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

def fetch_devices():
    url = "https://api-control.sputnik.systems/api/v2/devices?search=&limit=1000&page=1&device_type=null&sort_by=address&order=desc"
    headers = {
        "Authorization": f"Bearer {JWT_TOKEN}",
        "Cookie": "_ym_uid=1747813105897663116; _ym_d=1750666768; _ym_isad=2; _ss_api_developers_session=0n8ckcTjPELAn13l0nYNyfV8tpQpFTlk8SVzpXyOBc1d0%2FRpkSlPMnm1FvLqxniBnyh06xl%2FwLw2D1g%2B9zsyrys0%2B%2FxamxoWYKFv13Iv%2BNqiOwZMpcWve9swFZ1qb4tSCMD%2BTq1Ch64yTkxqC7KAGCvW9XPJlZfL2KktR689k0oNvIjTrvimp2dkzuwGckvx3IsglNa%2BpraF6vCynjCQuRv1lYVN4n8P5qQrSKKoJl%2FKaOVurYosSG4%2BrgihwmCKmTG4vMWD3y02l3%2FIeey5Ju9bzKrtA8wixw%3D%3D--XiIb3%2F0ty7Ou5AsH--E6XVhe1gBsmxZOXa9COTxw%3D%3D; _ss_account_manager_session=wY7gnVc4RmbYWLf2i74aQriVYV9j7%2F1oMx075GDTugxctEsaOoBClp6zuvxBl%2FZa%2F6lM%2Fj41WvN4dMp4ieNCnEMLKNkdieplSmy7zBmR9H8P5eGVqfkz%2BC%2Bf5cZThyPfVc%2BaLEtMn5oehpamJNdva1q7fjg9v%2BgZ1IhjYSn75tn1NzIvyMgtfmn%2BAAJdj14%2F9596VvcXhVdT4NlzMFagXOYT64CwOhmGZsf8qFuOuq7ZqgBT1mxW%2FX9thpZ8dzKeXP%2FnlJ0YVJXLek23coyd8rsIDExrbCYxDDNCUfIAYGEWWGlVh9cefoMsQb3n6IqTwdWxyJ2P7LytW0xD1ks%2FhHm1msoSP6JKBw%2F%2FXvE%3D--clDctBcHLQEgSd6k--e0ZhzpERx2rjaldVgSGCCA%3D%3D; _ss_gorod_expert_session=q58G%2ByMMivSQq18yop5m4Cr%2FGUvbwohDz2pcCKlcya%2FGFhc1oULzsE7m5Cl9xFp90UuOsPngCTKwrY1yXVFBOqO8J4CVkpGtU4HSg4xT67fiIdfhYy3H3ZyUX77L5xB%2FCridbBTXXOgDp4xg1SgQUSa8cTLP5b2%2FkB%2BavBRDEm%2FoW%2FFqayf1BnI%2BONEYmwluieoantJA93JCcZBJCQRJ91sg0oXFGsfQivOBeFXSRkOsSAs3sTjT3a%2Bq1HIlNoAJWy7GvmUwE0N2uaLtxt5%2Bv0Hd0%2FVY%2FNC%2FIo5uU9HtmQ9FoKwq56PXcGHarEUJSmCB6Jd7Qaw6Oaz8K6DfabMw2qXkCX4bofkFkS8bOB%2Bd5wloCqogujauDsFBHE6Uq6kOCtTREEA%3D--8b2LzIRPjCNy%2BTDw--baw8kGjD947DJbpBnaknHw%3D%3D"
    }
    resp = requests.get(url, headers=headers)
            resp.raise_for_status()
    return resp.json()["devices"]

def extract_base_address(addr):
    # Убираем ", п. X" или ", подъезд X" из адреса
    if not addr:
        return "Без адреса"
    return re.sub(r",\s*п(одъезд)?\.\s*\d+", "", addr)

def extract_entrance(addr):
    # Извлекаем "п. X" или "подъезд X" из адреса
    if not addr:
        return ""
    m = re.search(r",\s*(п(одъезд)?\.\s*\d+)", addr)
    return m.group(1) if m else ""

def build_report(devices):
    # Группируем по базовому адресу дома
    house_map = {}
    for dev in devices:
        addr = dev.get("short_address") or "Без адреса"
        base_addr = extract_base_address(addr)
        house_map.setdefault(base_addr, []).append(dev)

    reports = []
    for base_addr, devs in house_map.items():
        domofon_lines = []
        camera_lines = []
        for dev in devs:
            name = dev.get("serial_number") or dev.get("short_serial") or dev.get("uuid")
            dev_type = dev.get("type")
            is_online = dev.get("is_online")
            services = dev.get("services") or []
            has_archive = any(s.startswith("archive") for s in services)
            entrance = extract_entrance(dev.get("short_address"))
            problems = []
            if dev_type == "intercom":
                if not is_online:
                    problems.append("❌ Не онлайн")
                if not has_archive:
                    problems.append("❌ Нет архива")
                if problems:
                    domofon_lines.append(f"{entrance or name}: {', '.join(problems)}")
            elif dev_type == "camera":
                if not has_archive:
                    problems.append("❌ Нет архива")
                if problems:
                    camera_lines.append(f"{name}: {', '.join(problems)}")
        if domofon_lines or camera_lines:
            report = f"====================\n🏢 {base_addr}\n====================\n"
            if domofon_lines:
                report += "Домофоны (подъезды):\n" + "\n".join(domofon_lines) + "\n"
            if camera_lines:
                report += "Камеры:\n" + "\n".join(camera_lines)
            reports.append(report)
    return reports

def main():
    devices = fetch_devices()
    reports = build_report(devices)
    if reports:
        send_telegram_message("✅ Большинство камер онлайн и с архивом.")
        for rep in reports:
            send_telegram_message(rep)
            else:
        send_telegram_message("✅ Все камеры онлайн и с архивом.")

if __name__ == "__main__":
    main()