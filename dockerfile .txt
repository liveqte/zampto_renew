FROM alpine:3.22

# 安装依赖
RUN apk update && apk add --no-cache \
    python3 py3-pip curl bash udev chromium chromium-chromedriver \
        gcc python3-dev musl-dev linux-headers

# 设置工作目录
WORKDIR /app
# 复制文件
COPY zampto_server.py /app/
COPY requirements.txt /app/

# 创建虚拟环境并激活
RUN python3 -m venv /venv \
    && /venv/bin/pip install --upgrade pip \
        && /venv/bin/pip install -r /app/requirements.txt

        # CMD ["tail", "-F", "/dev/null"]

# 使用虚拟环境中的 Python 运行
CMD ["/venv/bin/python", "zampto_server.py"]
