import os
import sys
import signal
from DrissionPage import Chromium
from DrissionPage.common import Settings
from DrissionPage import ChromiumPage, ChromiumOptions
import asyncio
import logging
import random
import requests
from datetime import datetime
from time import sleep
from functools import wraps
import argparse
import socket

def signal_handler(sig, frame):
    print("\n捕捉到 Ctrl+C，正在退出...")
    # 这里可以添加清理逻辑，比如关闭文件、保存状态等
    sys.exit(1)
signal.signal(signal.SIGINT, signal_handler)
#解析url中的id
from urllib.parse import urlparse, parse_qs
def get_id_from_url(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return query_params.get('id', [None])[0]
#解析参数
parser = argparse.ArgumentParser(description="-k 在脚本运行结束后不结束浏览器")
parser.add_argument('-k', '--keep', action='store_true', help='启用保留模式')
parser.add_argument('-d', '--debug', action='store_true', help='启用调试模式')
parser.add_argument('-r', '--retry', type=int, default=0, help='重试次数（整数）')
iargs = parser.parse_args()
# 定义浏览器可执行候选路径
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
# 配置标准 logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
std_logger = logging.getLogger(__name__)

# 设置语言
Settings.set_language('en')
# 浏览器参数
options: ChromiumOptions
page: ChromiumPage
browser: Chromium

binpath = os.environ.get('CHROME_PATH', chromepath)
# 登录信息
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

# 通知
info = ""
# tg通知
tgbot_token = os.getenv("TG_TOKEN", "")
user_id = os.getenv("TG_USERID", "")
# 用来判断登录界面有没有被cf挡了
login_deny=False
if chromepath:
    print(f"✅ 使用浏览器路径：{chromepath}")
else:
    print("❌ 未找到可用的浏览器路径")
    error_exit("❌ 未找到可用的浏览器路径")
print(username)
if not username or not password:
    std_logger.warning("💡 请使用 Docker 的 -e 参数传入，例如：")
    std_logger.warning("docker run -itd -e USERNAME=your_username -e PASSWORD=your_password mingli2038/zam_ser:alpine")
    error_exit("❌ 缺少必要的环境变量 USERNAME 或 PASSWORD。")


if not tgbot_token:
    print("⚠️ 环境变量 TG_TOKEN 未设置，Telegram 通知功能将无法使用。")
    print("💡 请使用 Docker 的 -e TG_TOKEN=your_bot_token 传入。")

if not user_id:
    print("⚠️ 环境变量 TG_USERID 未设置，Telegram 通知功能将无法使用。")
    print("💡 请使用 Docker 的 -e TG_USERID=your_user_id 传入。")

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
def exit_process(num=0):
    global iargs,info,tgbot_token
    if info and info.strip():
        info="ℹ️ Zampto服务器续期通知\n"+info
        if check_google() and tgbot_token and user_id :
            tg_notifacation(info)
    if iargs.keep:
        print("✅ 启用了 -k 参数，保留浏览器模式")
    else:
        std_logger.info("✅ 浏览器已关闭，避免进程驻留")
        save_close_broser()
    exit(num)  
def save_close_broser():
    if 'browser' in globals() and browser:
        try:
            browser.quit()
            print("✅ 浏览器已安全关闭")
        except Exception as e:
            print(f"⚠️ 关闭浏览器时出错：{e}")
    else:
        print("⚠️ 浏览器对象不存在或未初始化，跳过关闭")
def error_exit(msg):
    global std_logger,info,iargs
    std_logger.debug(f"[ERROR] {msg}")
    info+=f"[ERROR] {msg}\n"
    exit_process(1)

async def get_latest_tab_safe():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: browser.latest_tab)
def require_browser_alive(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        global browser,iargs
        if browser.tabs_count == 0:
            error_exit("⚠️ 页面已崩溃或未附加，请重试运行一次脚本/镜像")
        try:
            page = await asyncio.wait_for(get_latest_tab_safe(), timeout=5)
        except asyncio.TimeoutError:
            if iargs.keep and iargs.debug:
                pass
            else:
                save_close_broser()
            error_exit("⚠️ 获取 latest_tab 超时，页面可能已崩溃")
        
        return await func(*args, **kwargs)
    return wrapper
def capture_screenshot( file_name=None,save_dir='screenshots'):
    global page
    import os
    os.makedirs(save_dir, exist_ok=True)
    if not file_name:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f'screenshot_{timestamp}.png'
    full_path = os.path.join(save_dir, file_name)
    try:
        page.get_screenshot(path=save_dir, name=file_name, full_page=True)
        print(f"📸 截图已保存：{full_path}")
    except Exception as e:
        print("⚠️ 截图失败，未能成功保存。")

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
    global page,browser
    options = (
        ChromiumOptions()
        .incognito(True)
        .set_user_agent(user_agent)
        .set_argument('--guest')
        .set_argument('--no-sandbox')
        .set_argument('--disable-gpu')
        .set_argument('--window-size=1280,800')
        .set_argument('--remote-debugging-port=9222')
        .set_browser_path(binpath)
    )
    if 'DISPLAY' not in os.environ:
        options.headless(True)
        options.set_argument('--headless=new') 
        std_logger.info("✅ DISPLAY环境变量为空，浏览器使用无头模式")
    else:
        options.headless(False)
        std_logger.info("✅ DISPLAY环境变量存在，浏览器使用正常模式")
    if user_data_path:
        options.set_user_data_path(user_data_path)
    # 创建 Chromium 浏览器对象
    browser = attach_browser()
    if browser is None or not browser.states.is_alive:
        # 接管失败，启动新浏览器
        browser = Chromium(options)

    # 获取当前激活的标签页
    page = browser.latest_tab

@require_browser_alive
async def test():
    pass
    
def is_port_open(host='127.0.0.1', port=9222, timeout=1):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def attach_browser(port=9222):
    try:
        if is_port_open():
            browser = Chromium(port)
            if browser.states.is_alive:
                print(f"✅ 成功接管浏览器（端口 {port}）")
                return browser
            print("❌ 接管失败，浏览器未响应")
        else:
            print(f"⚠️ 端口 {port} 未开放，跳过接管")
        return None
    except Exception as e:
        print(f"⚠️ 接管浏览器时出错：{e}")
        return None

async def dev_setup():
    pass
    
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
            std_logger.error('✗ cloudflare认证失败，退出')
            error_exit('✗ cloudflare认证失败，退出')
        return False

async def wait_for(a, b=None):
    global std_logger
    if b is None:
        b = a
    wait_time = random.uniform(a, b)
    std_logger.debug(f"即将等待 {wait_time:.2f} 秒（范围：{a} 到 {b}）...")
    await asyncio.sleep(wait_time)
    std_logger.debug(f"等待结束：{wait_time:.2f} 秒")
    
async def solve_turnstile(logger: logging.Logger):
    global options
    global page
    logger.debug('waiting for turnstile')
    await wait_for(15,30)
    inputauth(page)
    div = page.ele('xpath://*[@id="loginForm"]/div[3]/div/div', timeout=15)
    check_element('id=loginform', div)

    iframe1 = div.shadow_root.get_frame(1)
    check_element('iframe1', iframe1)

    body = iframe1.ele('@tag()=body', timeout=15)
    check_element('iframe-body', body)

    checkbox = body.shadow_root.ele('x://label/input', timeout=30)
    check_element('iframe1-body-checkbox', checkbox)
    xof = random.randint(5, 8)
    yof = random.randint(5, 8)
    checkbox.offset(x=xof, y=yof).click(by_js=False)
    std_logger.info(f"✅ 找到验证框，点击{checkbox}")
    await wait_for(5)
    capture_screenshot(f"cf_result.png")

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
        print("❌ [严重错误] 无法检查服务器存活时间状态，已终止程序执行！")
        error_exit(f'❌ [严重错误] 无法检查服务器存活时间状态，已终止程序执行！\n')
    server_name = server_name_span.inner_html
    if renew_notifacation:
        info += f'✅ 服务器 [{server_name}] 续期成功\n'
        print(f'✅ 服务器 [{server_name}] 续期成功')
        sleep(5)
        report_left_time(server_name)
    else:
        print(f'❌ [服务器: {server_name}] 续期失败')
        report_left_time(server_name)
        error_exit(f'❌ [服务器: {server_name}] 续期失败\n')

def report_left_time(server_name):
    global info
    left_time = page.ele('x://*[@id="nextRenewalTime"]', timeout=15)
    if left_time:
        info += f'🕒 [服务器: {server_name}] 存活期限：{left_time.inner_html}\n'
        print(f'🕒 [服务器: {server_name}] 存活期限：{left_time.inner_html}')

@require_browser_alive
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
    std_logger.info(f"待续期服务器：{server_list}")
    for s in server_list:
        page.get(s)
        await asyncio.sleep(5)
        renew_server(page)
        check_renew_result(page)
        ser_id=get_id_from_url(s)
        capture_screenshot(f"{ser_id}.png")

@require_browser_alive
async def hosting_login():
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
    await wait_for(7,10)
@require_browser_alive
async def open_server_overview_page():
    if page.url.endswith("hosting.zampto.net/auth/") :
        login_hosting= page.ele('x://*[@class="login-btn pulse"]', timeout=15)
        if login_hosting:
            std_logger.info(f"找到login_or_sign_with_zampto点击{login_hosting}")
            xof = random.randint(20, 60)
            yof = random.randint(5, 30)
            login_hosting.offset(x=xof, y=yof).click(by_js=False)
            await wait_for(10,15)
        else:
            std_logger.error("不能找到login_or_sign_with_zampto按钮,跳过")
    else:
        std_logger.info("你居然直接跳过hosting二阶段登录，这不可能发生")

    url = 'https://hosting.zampto.net/?page=overview'
    page.get(url)
    std_logger.info("等待cookie选项出现")
    await wait_for(10,15)
    click_if_cookie_option(page)

@require_browser_alive
async def login():
    global info,login_deny
    if login_deny and page.url.endswith("accounts.zampto.net/auth"):
        page.get("https://accounts.zampto.net/auth")
        login_deny=False
        await wait_for(10,15)
    await solve_turnstile(std_logger) 
    await wait_for(7,9)
    clickloginin(page)

    if "/auth" in page.url:
        msg = f"⚠️ {username}登录失败，请检查认证信息是否正确，若正确，可能是CF盾阻止了此IP访问，请尝试换一个的网络环境下执行"
        login_deny=True
        error_exit(msg)
    else:
        std_logger.info(f"{username}登录成功")
@require_browser_alive
async def open_web():
    url = "https://accounts.zampto.net/auth"
    if not page.url.startswith(url):
        page.get(url)
        await wait_for(20,35)
steps = [
    {"match": "/newtab/", "action": open_web, "name": "open_web"},
    {"match": "accounts.zampto.net/auth", "action": login, "name": "account"},
    {"match": "/?session_code=", "action": hosting_login, "name": "hosting_login"},
    {"match": "hosting.zampto.net/auth", "action": open_server_overview_page, "name": "open_server_overview"},
    {"match": "/?page=overview", "action": open_server_tab, "name": "open_server_tab"},
]

async def continue_execution(current_url: str = ""):
    global page, std_logger
    url = current_url or (page.url if page else "")
    std_logger.debug(f"当前页面 URL: {url}")
    if not url:
        std_logger.warning("URL为空，无法确定当前步骤")
        return
    # 找到当前步骤
    start_index = 0
    current_step_name = "unknown"
    
    for i, step in enumerate(steps):
        if step["match"] in url:
            start_index = i 
            current_step_name = step.get("name", f"step_{i}")
            std_logger.info(f"检测到当前步骤: {current_step_name}")
            break
    else:
        std_logger.warning(f"未找到匹配的步骤，URL: {url}")
        error_exit("没有匹配的步骤，退出")
    std_logger.info(f"从步骤 {start_index} 开始执行")

    # 从下一步继续执行
    for i, step in enumerate(steps[start_index:], start=start_index):
        step_name = step.get("name", f"step_{i}")
        std_logger.info(f"执行步骤 {i}: {step_name}")
        action = step["action"]
        try:
            # 执行操作
            result = action()
            if asyncio.iscoroutine(result):
                await result
            
            std_logger.debug(f"步骤 {step_name} 执行完成")
            std_logger.debug(f"当前URL: {page.url if page else 'N/A'}")

            await wait_for(2)
            # 截图记录
            screenshot_name = f"{step_name}_{i}.png"
            if start_index!=2:
                capture_screenshot(screenshot_name)
            
            # 可选：在每个步骤之间添加延迟
            if i < len(steps) - 1:  # 不是最后一步
                await wait_for(5)
                
        except Exception as e:
            std_logger.error(f"步骤 {step_name} 执行失败: {e}")
            return 1

    std_logger.info("所有步骤执行完成")
    return 0

async def main():
    global std_logger,iargs
    exit_code=0
    user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
    if iargs.debug:
        std_logger.info("DEBUG模式")
        await dev_setup()
        # exit_code=await continue_execution()
    else:
        setup(user_agent)
        try:
            exit_code=await continue_execution()
        except SystemExit as e:
            exit_code = e.code if isinstance(e.code, int) else 1
            print(f"捕获到系统退出，退出码: {exit_code}")
        except Exception as e:
            exit_code=1
            print(f"执行过程中出现错误: {e}")
            # 可以选择记录日志或发送错误通知
        finally:
            return exit_code

# 在脚本入口点运行
if __name__ == "__main__":
    
    if iargs.retry > 0 :
        for attempt in range(1,iargs.retry + 1):  # 包括第一次尝试
            success = asyncio.run(main())
            if success==0:
                std_logger.debug("执行成功，无需重试")
                exit_process(0)
                break
            else:
                std_logger.debug(f"第 {attempt} 次执行失败")
                if attempt < iargs.retry:
                    std_logger.debug("准备重试...")
                else:
                    std_logger.debug("已达到最大重试次数")
        else:
            exit_process(success)
    else:
        success=asyncio.run(main())
        exit_process(success)
