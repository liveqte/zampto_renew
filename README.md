## 使用方法
克隆本项目到本地
```bash
#克隆项目
git clone https://github.com/liveqte/zampto_renew.git
cd zampto_renew
```
在目录中任意选择一种方式中运行本仓库
### 从源代码
```
#编辑zampto_renew.py添加你的chrome浏览器执行目录
nano zampto_renew.py
```
```
#安装python虚拟环境和依赖，并运行
python3 -m venv /venv \
    && /venv/bin/pip install --upgrade pip \
        && /venv/bin/pip install -r requirements.txt
/venv/bin/python zampto_server.py
```
### 从dockerfile
```bash
docker build -t zam_ser:alpine -f Dockerfile .
docker run -itd \
  -e USERNAME=a@abc.com \
  -e PASSWORD=pass \
  -e TG_TOKEN=token \
  -e TG_USERID=id \
  zam_ser:alpine
```
### 从dokcer镜像
```bash
docker run -itd -e USERNAME=a@abc.com -e PASSWORD=pass -e TG_TOKEN=token -e TG_USERID=id ghcr.io/liveqte/zampto_renew:latest
```
## 环境变量说明
| 变量名      | 示例值         | 说明                                         | 是否必填 |
|-------------|----------------|----------------------------------------------|-----------|
| `USERNAME`  | `a@abc.com`    | 登录用户名或账号标识，用于身份验证或服务接入 | ✅ 是      |
| `PASSWORD`  | `pass`         | 对应用户名的密码或访问令牌                   | ✅ 是      |
| `TG_TOKEN`  | `token`        | Telegram Bot 的访问令牌，用于发送通知消息    | ❌ 否      |
| `TG_USERID` | `id`           | Telegram 用户的 ID，Bot 将消息发送到该用户    | ❌ 否      |

## 注意
一、开发此工具时，我的账号可能因为多次登录，以及异地登录，已经被限制不可访问hosting服务，所以推荐只在固定IP使用，并且不要在短时间运行多次docker镜像。

二、是否使用本工具的选择权在你手中，风险请自行承担。

三、脚本靠模拟点击网页元素，有时效性，如果网页一直不改就能一直用，如果改了就不行了，~~我账号已经被限制，所以没有办法进行维护，后期如果有申请到新账号再说。~~ 新号已经下来，~~近期会更新Github action流程~~ 放弃，因为网络环境不符合登录条件。

四、账户登录我在idx网络环境/github action下失败，其他随便找一个游戏机的节点就能成功。
