import os
import signal
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# --- 配置 ---
SERVER_URL = "https://panel.lumixcore.com/server/69a49477"
LOGIN_URL = "https://panel.lumixcore.com/auth/login"
TASK_TIMEOUT_SECONDS = 300

# --- 超时机制 ---
class TaskTimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TaskTimeoutError(f"任务超过 {TASK_TIMEOUT_SECONDS} 秒")

if os.name != 'nt':
    signal.signal(signal.SIGALRM, timeout_handler)

# --- 登录函数 ---
def login_with_playwright(page, context):
    """邮箱密码登录 + 保存状态"""
    email = os.environ.get('SILLYDEV_EMAIL')
    password = os.environ.get('SILLYDEV_PASSWORD')

    if not email or not password:
        print("❌ 未设置 SILLYDEV_EMAIL / SILLYDEV_PASSWORD")
        return False

    print("🔐 开始登录...")

    try:
        page.goto(LOGIN_URL, wait_until="domcontentloaded")

        page.fill('input[name="username"]', email)
        page.fill('input[name="password"]', password)

        with page.expect_navigation(wait_until="domcontentloaded"):
            page.click('button[type="submit"]')

        if "auth/login" in page.url:
            print("❌ 登录失败")
            page.screenshot(path="login_fail.png")
            return False

        print("✅ 登录成功")

        # ⭐ 保存登录状态（核心）
        context.storage_state(path="state.json")
        print("💾 已保存 state.json")

        return True

    except Exception as e:
        print(f"❌ 登录异常: {e}")
        page.screenshot(path="login_error.png")
        return False


# --- 续期任务 ---
def renew_server_task(page):
    try:
        print(f"[{datetime.now()}] 开始续期任务")

        renew_btn = page.locator("text=Renew")
        renew_btn.wait_for(timeout=60000)
        renew_btn.click()

        okay = page.get_by_role("button", name="Okay")
        okay.click(timeout=30000)

        print("✅ 续期完成")
        page.screenshot(path="success.png")
        return True

    except PlaywrightTimeoutError:
        print("❌ 续期超时")
        page.screenshot(path="timeout.png")
        return False
    except Exception as e:
        print(f"❌ 续期失败: {e}")
        page.screenshot(path="error.png")
        return False


# --- 主函数 ---
def main():
    print("🚀 启动自动续期脚本")

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        # ⭐ 自动加载 state.json（如果存在）
        if os.path.exists("state.json"):
            print("📦 加载已保存登录状态")
            context = browser.new_context(storage_state="state.json")
        else:
            print("🆕 未发现 state.json，将首次登录")
            context = browser.new_context()

        page = context.new_page()

        try:
            # 如果没登录状态，则登录
            if "state.json" not in os.listdir("."):
                if not login_with_playwright(page, context):
                    print("❌ 登录失败，退出")
                    return

            # 访问服务器
            page.goto(SERVER_URL, wait_until="domcontentloaded")

            if "auth/login" in page.url:
                print("⚠️ 登录失效，重新登录")
                if not login_with_playwright(page, context):
                    return
                page.goto(SERVER_URL)

            print("------------------------------------------------")

            if os.name != 'nt':
                signal.alarm(TASK_TIMEOUT_SECONDS)

            success = renew_server_task(page)

            if os.name != 'nt':
                signal.alarm(0)

            if success:
                print("🎉 本次任务成功")
            else:
                print("❌ 本次任务失败")

        except TaskTimeoutError:
            print("🔥 任务强制超时")
            page.screenshot(path="force_timeout.png")

        except Exception as e:
            print(f"❌ 主程序错误: {e}")
            page.screenshot(path="main_error.png")

        finally:
            print("🔚 关闭浏览器")
            browser.close()


if __name__ == "__main__":
    main()
    print("脚本结束")
