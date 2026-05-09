import os
import time
import requests
from seleniumbase import SB

# ================= 配置区域 =================
LOGIN_URL = "https://auth.zampto.net/sign-in?app_id=bmhk6c8qdqxphlyscztgl"

RENEW_URLS = [
    "https://dash.zampto.net/server?id=5329",
    "https://dash.zampto.net/server?id=5331"
]

# ================= 环境变量 =================
ZAMPTO_ACCOUNT = os.environ.get('ZAMPTO_ACCOUNT', '')
TG_BOT = os.environ.get('TG_BOT', '')
USE_PROXY = os.environ.get('USE_PROXY') == 'true'

# GitHub Actions + Xray 默认端口
LOCAL_PROXY = "socks5://127.0.0.1:10808" if USE_PROXY else None

def send_telegram_msg(message):
    """发送 Telegram 纯文本通知"""
    if not TG_BOT:
        return
    try:
        token, chat_id = TG_BOT.split('#')
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"TG 通知发送失败: {e}")

def send_telegram_photo(photo_path, caption=""):
    """发送 Telegram 图片通知"""
    if not TG_BOT:
        return
    try:
        token, chat_id = TG_BOT.split('#')
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with open(photo_path, 'rb') as f:
            payload = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
            requests.post(url, data=payload, files={"photo": f}, timeout=20)
    except Exception as e:
        print(f"TG 图片发送失败: {e}")

def solve_cf_captcha(sb, cf_selector):
    """过 Cloudflare 验证（GitHub Actions 稳定版）"""
    try:
        sb.execute_script("arguments[0].scrollIntoViewIfNeeded(true);", sb.find_element(cf_selector))
        time.sleep(1)
        sb.uc_gui_click_captcha()
        time.sleep(2)
        sb.uc_click(cf_selector)
        time.sleep(3)
    except:
        try:
            sb.uc_click('iframe')
            time.sleep(3)
        except:
            pass

def process_account(sb, username, password):
    """处理单个账号续期"""
    print(f"\n[+] 开始处理账号: {username}")
    account_report = [f"👤 账号: <b>{username}</b>"]

    cf_selector = 'iframe[title*="Cloudflare"], iframe[src*="challenge"], iframe[src*="turnstile"]'

    try:
        print(" -> 打开登录页面...")
        sb.uc_open_with_reconnect(LOGIN_URL, 4)

        print(" -> 等待登录框加载...")
        login_ready = False
        for _ in range(40):
            if sb.is_element_present('input[name="identifier"]'):
                print("    [+] 登录框已就绪")
                login_ready = True
                break

            if sb.is_element_present('iframe') or sb.is_text_visible("Verify you are human"):
                print("    [!] 发现 Cloudflare 拦截，处理中...")
                solve_cf_captcha(sb, cf_selector)
            else:
                time.sleep(1.5)

        if not login_ready:
            raise Exception("登录框加载超时")

        print(" -> 输入账号密码...")
        sb.type('input[name="identifier"]', username)
        sb.type('input[name="password"]', password)
        sb.click('button[type="submit"]')
        time.sleep(6)

        # 开始续期
        for url in RENEW_URLS:
            try:
                server_id = url.split('id=')[-1]
                print(f"\n -> [服务 {server_id}] 打开页面...")
                sb.uc_open_with_reconnect(url, 4)
                time.sleep(3)

                for _ in range(15):
                    if sb.is_element_present(cf_selector):
                        print(f"    [!] {server_id} 出现验证码")
                        solve_cf_captcha(sb, cf_selector)
                    else:
                        break
                    time.sleep(2)

                renew_btn = 'button:contains("Free Renew"), button:contains("Renew"), a:contains("Renew")'
                if sb.is_element_visible(renew_btn):
                    print(f" -> [服务 {server_id}] 点击续期...")
                    sb.uc_click(renew_btn)
                    time.sleep(8)

                    if sb.is_element_present(cf_selector):
                        solve_cf_captcha(sb, cf_selector)

                    print(f" -> [服务 {server_id}] 等待续期完成...")
                    time.sleep(25)

                    pic = f"{username}_server_{server_id}.png"
                    sb.save_screenshot(pic)
                    caption = f"✅ Zampto 续期成功\n账号: {username}\n服务ID: {server_id}"
                    send_telegram_photo(pic, caption)
                    account_report.append(f"✅ ID {server_id}: 续期成功")
                else:
                    print(f" -> [服务 {server_id}]: 无需续期")
                    account_report.append(f"ℹ️ ID {server_id}: 无需续期")

            except Exception as e:
                print(f" -> [服务 {server_id}] 异常: {str(e)[:60]}")
                account_report.append(f"❌ ID {server_id}: 处理失败")

        return True, "\n".join(account_report)

    except Exception as e:
        err_pic = f"{username}_error.png"
        sb.save_screenshot(err_pic)
        send_telegram_photo(err_pic, f"❌ Zampto 崩溃\n账号: {username}\n错误: {str(e)[:100]}")
        return False, f"❌ 账号 {username} 崩溃: {str(e)[:100]}"

def main():
    if not ZAMPTO_ACCOUNT:
        print("错误: 未配置 ZAMPTO_ACCOUNT")
        return

    accounts = [line.strip() for line in ZAMPTO_ACCOUNT.split('\n') if line.strip()]
    final_report = ["<b>✅ Zampto 自动续期完成</b>"]

    # GitHub Actions 专用模式
    with SB(
        uc=True,
        proxy=LOCAL_PROXY,
        headless=True,
        disable_csp=True,
        window_size="1920,1080"
    ) as sb:
        for acc in accounts:
            if ':' not in acc:
                continue
            user, pwd = acc.split(':', 1)
            success, msg = process_account(sb, user, pwd)
            final_report.append(msg)
            time.sleep(4)

    full_msg = "\n\n".join(final_report)
    print("\n" + full_msg.replace("<b>","").replace("</b>",""))
    send_telegram_msg(full_msg)

if __name__ == "__main__":
    main()
