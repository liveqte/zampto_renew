## 使用方法
克隆本项目到本地，在项目目录中运行如下命令
### 从源代码
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

三、脚本靠模拟点击网页元素，有时效性，如果网页一直不改就能一直用，如果改了就不行了，我账号已经被限制，所以没有办法进行维护，后期如果有申请到新账号再说。
