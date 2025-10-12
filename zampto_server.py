import os
import sys
from DrissionPage import Chromium
from DrissionPage.common import Settings
from DrissionPage import ChromiumPage, ChromiumOptions
import asyncio
import logging
import random
import requests
from datetime import datetime

# 定义两个候选路径
chrome_candidates = [
    "/usr/bin/chromium",
    "/usr/lib/chromium/chromium",
    "/usr/bin/chromium-browser",
    "/snap/bin/chromium",
    "/app/bin/chromium",
    "/opt/chromium/chrome",
    "/usr/local/bin/chromium",
    "/run/host/usr/bin/chromium",
    "/run/host/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/opt/google/chrome/chrome",
    "/run/host/usr/bin/microsoft-edge-stable"
]

chromepath = next((path for path in chrome_candidates if os.path.exists(path)), None)

if chromepath:
    print(f"✅ 使用浏览器路径：{chromepath}")
else:
    print("❌ 未找到可用的浏览器路径")
    exit(1)

# 配置标准 logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
std_logger = logging.getLogger(__name__)

# 设置语言
Settings.set_language('en')
# 浏览器参数
options: ChromiumOptions
page: ChromiumPage

binpath = os.environ.get('CHROME_PATH', chromepath)
# 登录信息
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

if not username or not password:
    std_logger.error("❌ 缺少必要的环境变量 USERNAME 或 PASSWORD。")
    std_logger.warning("💡 请使用 Docker 的 -e 参数传入，例如：")
    std_logger.warning("docker run -itd -e USERNAME=your_username -e PASSWORD=your_password mingli2038/zam_ser:alpine")
    sys.exit(1)

# tg通知
tgbot_token = os.getenv("TG_TOKEN")
user_id = os.getenv("TG_USERID")
if not tgbot_token:
    print("⚠️ 环境变量 TG_TOKEN 未设置，Telegram 通知功能将无法使用。")
    print("💡 请使用 Docker 的 -e TG_TOKEN=your_bot_token 传入。")

if not user_id:
    print("⚠️ 环境变量 TG_USERID 未设置，Telegram 通知功能将无法使用。")
    print("💡 请使用 Docker 的 -e TG_USERID=your_user_id 传入。")

info = ""
def capture_screenshot( file_name=None,save_dir='screenshots'):
    global page
    import os
    os.makedirs(save_dir, exist_ok=True)
    if not file_name:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f'screenshot_{timestamp}.png'
    full_path = os.path.join(save_dir, file_name)
    page.get_screenshot(path=save_dir, name=file_name, full_page=True)
    print(f"📸 截图已保存：{full_path}")

def tg_notifacation(meg):
    url = f"https://api.telegram.org/bot{tgbot_token}/sendMessage"
    payload = {
        "chat_id": user_id,
        "text": meg
    }
    response = requests.post(url, data=payload)
    print(response.json())


def setup(user_agent: str, user_data_path: str = None):
    global options
    global page
    options = (
        ChromiumOptions()
        .auto_port()
        .headless()
        .incognito(True)
        .set_user_agent(user_agent)
        # .set_argument('--guest')
        .set_argument('--no-sandbox')
        .set_argument('--disable-gpu')
        .set_argument('--window-size=1280,800')
        .set_browser_path(binpath)
    )
    if user_data_path:
        options.set_user_data_path(user_data_path)
    page = ChromiumPage(options)


def inputauth(inpage):
    u = inpage.ele('x://*[@id="email"]')
    u.input(username)
    p = inpage.ele('x://*[@id="password"]')
    p.input(password)


def clickloginin(inpage):
    c = inpage.ele('x://*[@id="loginButton"]', timeout=15)
    xof = random.randint(1, 20)
    yof = random.randint(1, 10)
    c.offset(x=xof, y=yof).click(by_js=False)


def check_element(desc, element, exit_on_fail=True):
    global std_logger
    if element:
        std_logger.debug(f'✓ {desc}: {element}')
        return True
    else:
        std_logger.debug(f'✗ {desc}: 获取失败')
        if exit_on_fail:
            std_logger.error('cloudflare认证失败，退出')
            exit(1)
        return False


async def solve_turnstile(logger: logging.Logger, url: str):
    global options
    global page
    page.get(url)
    logger.debug('waiting for turnstile')
    inputauth(page)
    await asyncio.sleep(10)
    div = page.ele('xpath://*[@id="loginForm"]/div[3]/div/div', timeout=15)
    check_element('id=loginform', div)

    iframe1 = div.shadow_root.get_frame(1)
    check_element('iframe1', iframe1)

    body = iframe1.ele('@tag()=body', timeout=15)
    check_element('iframe-body', body)

    checkbox = body.shadow_root.ele('x://label/input', timeout=30)
    check_element('iframe1-body-checkbox', checkbox)

    checkbox.click(by_js=False)

def dev_setup():
    global page
    page = Chromium(18518).latest_tab


def click_if_cookie_option(tab):
    deny = tab.ele("x://button[@class='fc-button fc-cta-do-not-consent fc-secondary-button']", timeout=15)
    if deny:
        deny.click()
        print('发现出现cookie使用协议，跳过')

def renew_server(tab):
    renewbutton = tab.ele("x://a[contains(@onclick, 'handleServerRenewal')]", timeout=15)
    if renewbutton:
        print(f"找到{renewbutton}")
        renewbutton.click(by_js=False)
    else:
        print("没找到renew按钮，无事发生")

def check_renew_result(tab):
    global info
    renew_notifacation = tab.ele('x:// *[ @ id = "renewalSuccess"] / div', timeout=15)
    server_name_span = page.ele('x://*[@id="js-check"]/div[2]/div/div[1]/h1/span[2]', timeout=15)
    if not server_name_span:
        info += f'❌ [严重错误] 无法检查服务器存活时间状态，已终止程序执行！\n'
        print("❌ [严重错误] 无法检查服务器存活时间状态，已终止程序执行！")
        exit(1)
    server_name = server_name_span.inner_html
    if renew_notifacation:
        info += f'✅ 服务器 [{server_name}] 续期成功\n'
        print(f'✅ 服务器 [{server_name}] 续期成功')
        report_left_time(server_name)
    else:
        info += f'❌ [服务器: {server_name}] 续期失败\n'
        print(f'❌ [服务器: {server_name}] 续期失败')


def report_left_time(server_name):
    global info
    left_time = page.ele('x://*[@id="nextRenewalTime"]', timeout=15)
    if left_time:
        info += f'🕒 [服务器: {server_name}] 存活期限：{left_time.inner_html}\n'
        print(f'🕒 [服务器: {server_name}] 存活期限：{left_time.inner_html}')


def check_google():
    try:
        response = requests.get("https://www.google.com", timeout=5)
        if response.status_code == 200:
            return True
        else:
            print(f"⚠️ 无法访问 Google，tg通知将不起作用，状态码：{response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ ⚠️ 无法访问 Google，tg通知将不起作用：{e}")
        return False


async def open_server_tab():
    global std_logger
    manage_server = page.eles("x://a[contains(@href, '?page=server')]", timeout=15)
    std_logger.info(manage_server)
    std_logger.debug(f"url_now:{page.url}")
    server_list = []
    for a in manage_server:
        server_list.append(a.attr('href'))
    if not server_list:
        error_exit("⚠️ server_list 为空，跳过服务器续期流程")
    for s in server_list:
        page.get(s)
        await asyncio.sleep(5)
        renew_server(page)
        check_renew_result(page)
        capture_screenshot(f"{s}.png")

def error_exit(msg):
    global std_logger
    std_logger.debug(f"[ERROR] {msg}")
    exit_process()
def exit_process():
    # page.quit()
    exit(1)

async def open_server_overview_page():
    global std_logger
    if page.url.startswith("https://accounts.zampto.net/"):
        hosting = page.ele('x://button[contains(@onclick, "redirectTo(\'https://hosting.zampto.net/\')")]')
        if hosting:
            std_logger.info(f"找到hosting入口点击{hosting}")
            hosting.click(by_js=False)
    else:
        std_logger.error("没有在帐户主页找到hosting入口，回退到直接访问")
        url = 'https://hosting.zampto.net/'
        page.get(url)
    await asyncio.sleep(random.randint(7, 10))
    if page.url.endswith("/auth") or page.url.endswith("/auth/"):
        login_hosting= page.ele('x://*[@class="login-btn pulse"]', timeout=15)
        if login_hosting:
            std_logger.info(f"找到login_or_sign_with_zampto点击{login_hosting}")
            xof = random.randint(20, 60)
            yof = random.randint(5, 30)
            login_hosting.offset(x=xof, y=yof).click(by_js=False)
            await asyncio.sleep(random.randint(4, 6))
        else:
            std_logger.error("不能找到login_or_sign_with_zampto按钮,跳过")
    else:
        std_logger.info("你居然直接跳过hosting二阶段登录，这不可能发生")

    url = 'https://hosting.zampto.net/?page=overview'
    page.get(url)
    await asyncio.sleep(random.randint(3, 6))
    click_if_cookie_option(page)


async def login():
    global info
    url = "https://accounts.zampto.net/auth"
    await solve_turnstile(std_logger, url)  # , user_data_path=user_data_path)
    await asyncio.sleep(10)
    clickloginin(page)
    await asyncio.sleep(random.randint(7, 9))
    if "/auth" in page.url:
        info+=f"⚠️ {username}登录失败，请检查认证信息是否正确，若正确，可能是CF盾阻止了此IP访问，请尝试换一个的网络环境下执行\n"
        error_exit(f"{username}登录失败，请检查认证信息是否正确，若正确，可能是CF盾阻止了此IP访问，请尝试换一个的网络环境下执行")
    else:
        std_logger.info(f"{username}登录成功")
async def main():
    global info
    global std_logger
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    setup(user_agent)
    # dev_setup()
    try:
        await login()
        std_logger.debug(f"url_now:{page.url}")
        capture_screenshot("login.png")
        await open_server_overview_page()
        std_logger.debug(f"url_now:{page.url}")
        capture_screenshot("server_overview.png")
        await asyncio.sleep(2)

        await open_server_tab()
        std_logger.debug(f"url_now:{page.url}")
        if check_google() and info and tgbot_token and user_id :
            tg_notifacation(info)
    except Exception as e:
        print(f"执行过程中出现错误: {e}")
        # 可以选择记录日志或发送错误通知
    finally:
        # page.quit()
        std_logger.info("浏览器已关闭，避免进程驻留")

# 在脚本入口点运行
if __name__ == "__main__":
    asyncio.run(main())
