import os
import sys
from DrissionPage import Chromium
from DrissionPage.common import Settings
from DrissionPage import ChromiumPage, ChromiumOptions
import asyncio
import logging
import random
import requests

# 定义两个候选路径
chrome_candidates = [
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/snap/bin/chromium",
    "/app/bin/chromium",
    "/opt/chromium/chrome", 
    "/usr/local/bin/chromium",
    "/run/host/usr/bin/chromium",
    "/run/host/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/opt/google/chrome/chrome"
]

chromepath = next((path for path in chrome_candidates if os.path.exists(path)), None)

if chromepath:
    print(f"✅ 使用浏览器路径：{chromepath}")
else:
    print("❌ 未找到可用的浏览器路径")
    sys.exit(1)

# 配置标准 logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
std_logger = logging.getLogger(__name__)

# 设置语言
Settings.set_language('en')
# 浏览器参数
options:ChromiumOptions
page:ChromiumPage

binpath=os.environ.get('CHROME_PATH',chromepath)
# 登录信息
username=os.getenv("USERNAME")
password=os.getenv("PASSWORD")


if not username or not password:
    print("❌ 缺少必要的环境变量 USERNAME 或 PASSWORD。")
    print("💡 请使用 Docker 的 -e 参数传入，例如：")
    print("   docker run -itd -e USERNAME=your_username -e PASSWORD=your_password mingli2038/zam_ser:alpine")
    sys.exit(1)

# tg通知
tgbot_token=os.getenv("TG_TOKEN")
user_id=os.getenv("TG_USERID")
if not tgbot_token:
    print("⚠️ 环境变量 TG_TOKEN 未设置，Telegram 通知功能将无法使用。")
    print("💡 请使用 Docker 的 -e TG_TOKEN=your_bot_token 传入。")

if not user_id:
    print("⚠️ 环境变量 TG_USERID 未设置，Telegram 通知功能将无法使用。")
    print("💡 请使用 Docker 的 -e TG_USERID=your_user_id 传入。")

info=""

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
        .set_argument('--remote-debugging-port=9333')
        .set_browser_path(binpath)
    )
    if user_data_path:
        options.set_user_data_path(user_data_path)
    page = ChromiumPage(options)
def inputauth(inpage):
    u=inpage.ele('x://*[@id="email"]')
    u.input(username)
    p=inpage.ele('x://*[@id="password"]')
    p.input(password)
def clickloginin(inpage):
    c=inpage.ele('x://*[@id="loginButton"]', timeout=15)
    xof = random.randint(1, 20)
    yof = random.randint(1, 10)
    c.offset(x=xof,y=yof).click(by_js=False)
def check_element(desc, element, exit_on_fail=True):
    if element:
        print(f'✓ {desc}: {element}')
        return True
    else:
        print(f'✗ {desc}: 获取失败')
        if exit_on_fail:
            print('cloudflare认证失败，退出')
            exit(1)
        return False

async def solve_turnstile(logger:logging.Logger, url: str):
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
    page = Chromium(35912).latest_tab
def click_if_cookie_option(tab):
    allow=tab.ele('x:/html/body/div[4]/div[2]/div[2]/div[2]/div[2]/button[1]', timeout=15)
    # print(allow)
    if allow:
        allow.click()
        print('发现出现cookie使用协议，跳过')
def renew_server(tab):
    renewbutton=tab.ele('x://*[@id="js-check"]/div[2]/div/div[3]/div[2]/div/a', timeout=15)
    if renewbutton:
        renewbutton.click(by_js=False)
def check_renew_result(tab):
    global info
    renew_notifacation = tab.ele('x:// *[ @ id = "renewalSuccess"] / div', timeout=15)
    server_name_span=page.ele('x://*[@id="js-check"]/div[2]/div/div[1]/h1/span[2]', timeout=15)
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
        info+=f'🕒 [服务器: {server_name}] 存活期限：{left_time.inner_html}\n'
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
    manage_server=page.eles('x://*[@id="servers-container"]/div/div/div[2]/a', timeout=15)
    print(manage_server)
    print(f"url_now:{page.url}")
    server_list=[]
    for a in manage_server:
       server_list.append(a.attr('href'))
    for s in server_list:
        page.get(s)
        await asyncio.sleep(5)
        renew_server(page)
        check_renew_result(page)
async def open_server_overview_page():
    if not page.url.startswith("https://hosting.zampto.net"):
        url = 'https://hosting.zampto.net/'
        page.get(url)
        await asyncio.sleep(random.randint(5, 7))
    if page.url.endswith("auth/"):
        login_or_sign_with_zampto=page.ele('x://*[@id="login-btn"]/div[1]', timeout=15)
        if login_or_sign_with_zampto:
            print(login_or_sign_with_zampto)
            xof = random.randint(20, 150)
            yof = random.randint(5, 30)
            login_or_sign_with_zampto.offset(x=xof,y=yof).click(by_js=False)
            # login_or_sign_with_zampto.click(by_js=True)
            await asyncio.sleep(random.randint(4, 6))

    url = 'https://hosting.zampto.net/?page=overview'
    page.get(url)
    await asyncio.sleep(random.randint(3,6))
    click_if_cookie_option(page)
async def login():
    url = "https://accounts.zampto.net/auth"
    await solve_turnstile(std_logger, url)  # , user_data_path=user_data_path)
    await asyncio.sleep(10)
    clickloginin(page)

async def main():
    global info
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    setup(user_agent)

    try:
        await login()
        await asyncio.sleep(random.randint(3, 7))
        # dev_setup()
        await open_server_overview_page()
        print(f"url_now:{page.url}")
        await asyncio.sleep(2)
        if "auth/" in page.url:
            print("⚠️ 登录没有成功，请检查认证信息是否正确，若正确，请尝试换一个的网络环境下执行")
            exit(1)
        await open_server_tab()
        print(f"url_now:{page.url}")
        if check_google() and info and tgbot_token and user_id :
            tg_notifacation(info)
    except Exception as e:
        print(f"执行过程中出现错误: {e}")
        # 可以选择记录日志或发送错误通知
    finally:
        page.quit()
        print("浏览器已关闭，避免进程驻留")

# 在脚本入口点运行
if __name__ == "__main__":
    asyncio.run(main())
