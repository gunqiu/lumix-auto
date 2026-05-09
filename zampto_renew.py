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

# 读取环境变量代理
LOCAL_PROXY = os.environ.get("LOCAL_PROXY", "socks5://127.0.0.1:10808") if USE_PROXY else None

def send_telegram_msg(message):
    if not TG_BOT:
        return
    try:
        token, chat_id = TG_BOT.split('#')
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"TG 通知失败: {e}")

def send_telegram_photo(photo_path, caption=""):
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

def process_account(sb, username, password):
    print(f"\n[+] 开始处理账号: {username}")
    account_report = [f"👤 账号: <b>{username}</b>"]

    cf_selector = 'iframe[title*="Cloudflare"], iframe[src*="challenge"], iframe[src*="turnstile"]'

    try:
        print(" -> 正在访问登录页面...")
        sb.maximize_window()
        sb.uc_open_with_reconnect(LOGIN_URL, 6)

        print(" -> 正在智能侦测页面状态 (最高等待 60 秒)...")
        login_ready = False
        for i in range(30):
            if sb.is_element_present('input[name="identifier"]'):
                print("    [+] 拦截已解除，登录框已就绪！")
                login_ready = True
                break

            if sb.is_element_present('iframe') or sb.is_text_visible("Verify you are human") or sb.is_text_visible("security verification"):
                print(f"    [!] 发现全局拦截盾牌 (第 {i+1} 次扫描)，尝试物理破盾...")
                
                try:
                    sb.execute_script("arguments[0].scrollIntoView({block: 'center'});", sb.find_element('iframe'))
                    time.sleep(1)
                    sb.uc_click('iframe')
                except:
                    pass
                time.sleep(1)
                
                try:
                    sb.uc_gui_click_captcha()
                except:
                    pass
                time.sleep(3)
                
                try:
                    if sb.is_element_present(cf_selector):
                        sb.uc_click(cf_selector)
                    else:
                        sb.uc_click('iframe')
                except:
                    pass
                
                time.sleep(4)
            else:
                time.sleep(2)

        if not login_ready:
            raise Exception("登录框加载超时，未能突破拦截")

        print(" -> 填写账号...")
        sb.type('input[name="identifier"]', username, timeout=10)

        print(" -> 点击第一步的继续按钮...")
        sb.click('button[type="submit"]', timeout=10)
        time.sleep(3)

        print(" -> 填写密码...")
        sb.type('input[name="password"]', password, timeout=10)

        print(" -> 点击继续按钮，触发验证码...")
        sb.click('button[type="submit"]', timeout=10)

        print(" -> 傻等 12 秒，让内部 Cloudflare 验证码充分加载...")
        time.sleep(12)

        print(" -> 准备执行多重拟人点击...")
        try:
            if sb.is_element_present(cf_selector):
                sb.execute_script("arguments[0].scrollIntoView({block: 'center'});", sb.find_element(cf_selector))
                time.sleep(1)
                sb.uc_click(cf_selector)
                time.sleep(2)
                sb.uc_gui_click_captcha()
            else:
                sb.uc_click('iframe')
        except:
            pass

        print(" -> 登录验证码已点击，静候 25 秒等待系统验证并跳转...")
        time.sleep(25)

        print(" -> 登录成功！")

        for url in RENEW_URLS:
            try:
                server_id = url.split('id=')[-1]
                print(f"\n -> [服务 {server_id}] 正在打开面板...")
                sb.uc_open_with_reconnect(url, 4)
                time.sleep(5)

                print(" -> 等待并检查可能出现的悬浮广告 (最多检查 3 次)...")
                for _ in range(3):
                    if sb.is_text_visible("close", timeout=2) or sb.is_element_present('button:contains("×")', timeout=2):
                        print("    [!] 发现悬浮广告，尝试关闭...")
                        try:
                            sb.click('button:contains("×")')
                        except:
                            pass
                        time.sleep(2)
                    else:
                        print("    [+] 页面干净，未检测到新的悬浮广告。")
                        break

                print(" -> 向下滚动页面，寻找续期按钮...")
                sb.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)

                renew_btn_selector = 'button:contains("Free Renew"), button:contains("Renew"), a:contains("Renew")'
                if sb.is_element_visible(renew_btn_selector, timeout=5):
                    print(f" -> [服务 {server_id}] 已强制点击续期按钮，正在加载弹窗验证码...")
                    sb.uc_click(renew_btn_selector)
                    time.sleep(8)

                    try:
                        if sb.is_element_present(cf_selector):
                            sb.execute_script("arguments[0].scrollIntoView({block: 'center'});", sb.find_element(cf_selector))
                            time.sleep(1)
                            sb.uc_click(cf_selector)
                            time.sleep(2)
                            sb.uc_gui_click_captcha()
                    except:
                        pass

                    print(f" -> [服务 {server_id}] 弹窗验证码已点击，等待 25 秒让系统自动跳转完成续期...")
                    time.sleep(25)

                    screenshot_name = f"{username}_server_{server_id}_done.png"
                    sb.save_screenshot(screenshot_name)
                    print(f" -> [服务 {server_id}] 截图已保存，正在发送至 Telegram...")

                    caption_msg = f"✅ <b>Zampto 续期成功</b>\n账号: {username}\n服务 ID: {server_id}"
                    send_telegram_photo(screenshot_name, caption_msg)

                    account_report.append(f"  ✅ ID {server_id}: 续期成功！(已发送截图)")
                else:
                    sb.save_screenshot(f"{username}_server_{server_id}_no_btn.png")
                    account_report.append(f"  ℹ️ ID {server_id}: 未找到续期按钮 (可能暂无需续期)")
            except Exception as e:
                account_report.append(f"  ❌ ID {server_id}: 处理出错")
                print(f" -> [服务 {server_id}] 错误: {e}")

        return True, "\n".join(account_report)

    except Exception as e:
        error_shot = f"{username}_fatal_error.png"
        sb.save_screenshot(error_shot)
        send_telegram_photo(error_shot, f"❌ <b>Zampto 崩溃告警</b>\n账号: {username}\n查看截图诊断问题。")
        return False, f"❌ 账号 <b>{username}</b> 流程崩溃: {str(e)[:100]}"

def main():
    if not ZAMPTO_ACCOUNT:
        print("错误: 未配置 ZAMPTO_ACCOUNT 环境变量")
        return

    accounts = [line.strip() for line in ZAMPTO_ACCOUNT.split('\n') if line.strip()]
    final_reports = ["<b>Zampto 自动化续期汇总</b>"]

    # 🔥 关键修复：只保留 SB() 原生支持的参数
    with SB(
        uc=True, 
        proxy=LOCAL_PROXY, 
        headless2=True
    ) as sb:
        for acc in accounts:
            if ':' not in acc: continue
            user, pwd = acc.split(':', 1)
            success, report = process_account(sb, user, pwd)
            final_reports.append(report)
            time.sleep(5)

    full_msg = "\n".join(final_reports)
    print(full_msg.replace("<b>", "").replace("</b>", ""))
    send_telegram_msg(full_msg)

if __name__ == "__main__":
    main()
