import os
import time
import requests
from seleniumbase import SB

# ================= 配置 =================
LOGIN_URL = "https://auth.zampto.net/sign-in?app_id=bmhk6c8qdqxphlyscztgl"
RENEW_URLS = [
    "https://dash.zampto.net/server?id=5329",
    "https://dash.zampto.net/server?id=5331"
]

# ================= 环境变量 =================
ZAMPTO_ACCOUNT = os.environ.get('ZAMPTO_ACCOUNT', '')
TG_BOT = os.environ.get('TG_BOT', '')
USE_PROXY = os.environ.get('USE_PROXY') == 'true'
LOCAL_PROXY = os.environ.get("LOCAL_PROXY", "socks5://127.0.0.1:10808") if USE_PROXY else None

def send_telegram_msg(message):
    if not TG_BOT:
        return
    try:
        token, chat_id = TG_BOT.split('#')
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)
    except:
        pass

def send_telegram_photo(photo_path, caption=""):
    if not TG_BOT:
        return
    try:
        token, chat_id = TG_BOT.split('#')
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with open(photo_path, 'rb') as f:
            requests.post(url, data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}, files={"photo": f}, timeout=20)
    except:
        pass

def process_account(sb, username, password):
    print(f"\n[+] 开始处理账号: {username}")
    report = [f"👤 账号: <b>{username}</b>"]

    try:
        # 🔥 关键：直接访问，让 uc=True 自动过 CF
        print(" -> 正在访问登录页面...")
        sb.maximize_window()
        sb.uc_open_with_reconnect(LOGIN_URL, 10)

        # 🔥 关键：不再循环检测，直接等待登录框出现（seleniumbase 会自动处理验证）
        print(" -> 等待登录框加载...")
        sb.wait_for_element('input[name="identifier"]', timeout=90)

        print(" -> 输入账号...")
        sb.type('input[name="identifier"]', username)
        sb.click('button[type="submit"]')

        print(" -> 输入密码...")
        sb.wait_for_element('input[name="password"]', timeout=30)
        sb.type('input[name="password"]', password)
        sb.click('button[type="submit"]')

        print(" -> 等待登录完成...")
        sb.wait_for_element_absent('input[name="password"]', timeout=60)
        print("✅ 登录成功！")

        # 处理续期
        for url in RENEW_URLS:
            server_id = url.split('id=')[-1]
            print(f"\n -> [服务 {server_id}] 正在打开面板...")
            sb.uc_open_with_reconnect(url, 4)
            time.sleep(5)

            # 处理广告
            for _ in range(3):
                if sb.is_element_present('button:contains("×")'):
                    sb.click('button:contains("×")')
                    time.sleep(2)
                else:
                    break

            sb.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            renew_btn = 'button:contains("Free Renew"), button:contains("Renew"), a:contains("Renew")'
            if sb.is_element_visible(renew_btn, timeout=5):
                sb.click(renew_btn)
                time.sleep(10)
                screenshot = f"{username}_server_{server_id}_done.png"
                sb.save_screenshot(screenshot)
                send_telegram_photo(screenshot, f"✅ Zampto 续期成功\n账号: {username}\n服务ID: {server_id}")
                report.append(f"  ✅ ID {server_id}: 续期成功")
            else:
                report.append(f"  ℹ️ ID {server_id}: 无需续期或未找到按钮")

        return True, "\n".join(report)

    except Exception as e:
        screenshot = f"{username}_error.png"
        sb.save_screenshot(screenshot)
        send_telegram_photo(screenshot, f"❌ 账号 {username} 崩溃: {str(e)[:100]}")
        return False, f"❌ 账号 {username} 流程崩溃: {str(e)[:100]}"

def main():
    if not ZAMPTO_ACCOUNT:
        print("未配置账号")
        return

    accounts = [line.strip() for line in ZAMPTO_ACCOUNT.splitlines() if line.strip()]
    reports = ["<b>Zampto 自动化续期汇总</b>"]

    # 只保留最稳定的参数
    with SB(uc=True, proxy=LOCAL_PROXY, headless2=True) as sb:
        for acc in accounts:
            user, pwd = acc.split(":", 1)
            success, report = process_account(sb, user, pwd)
            reports.append(report)
            time.sleep(5)

    full_report = "\n".join(reports)
    print(full_report)
    send_telegram_msg(full_report)

if __name__ == "__main__":
    main()
