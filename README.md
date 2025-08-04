# 🔐 Reverse-TCP-Proxy (Fernet 版)

```markdown
# 🔐 Reverse-TCP-Proxy (Fernet 版)

一个基于 Python 实现的轻量级 **反向 TCP 代理工具**，支持：

- 单端口控制通道
- 多端口反向代理
- **控制通道加密 (Fernet)**，防止外部监听
- 数据通道透明转发（支持 SSH、HTTP 等任意 TCP 流量）

适用于 **内网穿透** 场景，例如：

- 无法直接暴露内网主机，但需要外部访问内网服务（SSH、Web 等）
- 简单自建 FRP 类似功能

---

## ✨ 功能特性

- [x] 单控制端口（默认 6000）
- [x] 多代理端口支持（示例：6001→22，6002→80）
- [x] 控制消息加密（Fernet 对称加密）
- [x] 自动连接与转发
- [x] 代码简单，无额外依赖服务

---

## 🏗️ 架构原理

```

\[外部客户端]      ssh -p 6001 user@公网IP
|
v
\[公网服务器] server.py
\|   (控制通道加密)
|<-----------------------> \[内网客户端] client.py
\|                                    |
v                                    v
\[内网服务] <--- 22端口 / 80端口 / 其他端口 ----

````

- `server.py` 运行在公网服务器，监听控制端口 (6000) 和代理端口 (6001, 6002)
- `client.py` 运行在内网主机，建立加密控制连接，按需反连数据通道
- 外部访问 `公网IP:6001` 时，流量通过反向隧道转发到内网 SSH 端口 22

---

## 📦 安装依赖

需要 Python 3.7+：

```bash
pip install cryptography
````

---

## 🔑 生成加密密钥

使用 Fernet 生成一个安全随机密钥：

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

示例输出：

```
6aUXWau3OKQ5mV-M5g5CkZxep_t8XzxxUQ_G8GgpNto=
```

将此值填入：

* `server.py` → `FERNET_KEY`
* `client.py` → `FERNET_KEY`

---

## 🚀 使用方法

### 1️⃣ 启动服务端

在 **公网服务器** 运行：

```bash
python3 server.py
```

默认监听：

* `6000` 控制通道
* `6001` → 反向代理内网 22 端口
* `6002` → 反向代理内网 80 端口

---

### 2️⃣ 启动客户端

在 **内网主机** 运行：

```bash
python3 client.py
```

此时，客户端会注册到服务器，等待外部连接触发。

---

### 3️⃣ 外部访问

在本地或第三方机器上：

* SSH 访问内网主机：

```bash
ssh -p 6001 user@<公网服务器IP>
```

* HTTP 访问内网网站：

```bash
curl http://<公网服务器IP>:6002
```

数据将自动通过加密控制通道建立反向 TCP 隧道转发。

---

## ⚙️ 配置修改

可根据需求修改：

* 服务器端口映射：

```python
PROXY_PORTS = {6001: 22, 6002: 80}
```

* 客户端本地服务端口映射：

```python
PROXY_TO_LOCAL_PORT = {6001: 22, 6002: 80}
```

* 客户端 ID：

```python
CLIENT_ID = 'client1'
```

多个客户端可用不同 `CLIENT_ID`。

---

## 🔒 安全性

* 控制通道使用 **Fernet 对称加密**，避免明文传输控制信息
* 数据通道透明转发，不解密 SSH/HTTP 数据，保持原始安全协议（如 SSH 内部加密）
* 建议：

  * 使用强随机密钥
  * 配置防火墙限制控制通道访问来源
  * 使用 SSH 密钥认证代替密码

---

## 🧠 TODO

* [ ] 多客户端注册管理
* [ ] 数据通道分帧加密（可选）
* [ ] Docker 镜像一键部署

---

# Reverse-TCP 代理服务部署指南

## 1. 克隆代码仓库

```bash
git clone https://github.com/5777033/reverse-tcp.git
```

---

## 2. 服务端部署

### 2.1 创建服务端目录并移动文件

```bash
sudo mkdir -p /opt/proxy-server
mv server.py /opt/proxy-server/
```

### 2.2 配置 systemd 服务 (`/etc/systemd/system/proxy-server.service`)

```ini
[Unit]
Description=Secure Reverse Proxy Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/proxy-server
ExecStart=/usr/bin/python3 /opt/proxy-server/server.py
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

### 2.3 启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable proxy-server
sudo systemctl start proxy-server
```

### 2.4 查看服务日志

```bash
journalctl -u proxy-server -f
```

---

## 3. 客户端部署

### 3.1 创建客户端目录并移动文件

```bash
sudo mkdir -p /opt/proxy-client
mv client.py /opt/proxy-client/
```

### 3.2 配置 systemd 服务 (`/etc/systemd/system/proxy-client.service`)

```ini
[Unit]
Description=Secure Reverse Proxy Client
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/proxy-client
ExecStart=/usr/bin/python3 /opt/proxy-client/client.py
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

### 3.3 启动客户端服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable proxy-client
sudo systemctl start proxy-client
```

### 3.4 查看客户端日志

```bash
journalctl -u proxy-client -f
```

---

## 4. 防火墙配置

### 4.1 服务端防火墙设置

允许客户端 IP 访问服务端端口（示例端口 6001-6004）：

```bash
sudo ufw allow from <客户端IP> to any port 6001:6004
```

### 4.2 客户端防火墙设置

确保本地需要代理的端口可访问，例如 SSH 和 HTTP：

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
```

---

## 5. 验证与测试

### 5.1 测试 SSH 连接

```bash
ssh -p 6001 user@your.server.ip
```

### 5.2 查看端口监听状态

服务端查看监听端口：

```bash
ss -tulnp | grep 600
```

客户端查看本地端口状态：

```bash
ss -tulnp | grep -E '22|80|3306|5432'
```

### 5.3 重启服务

```bash
sudo systemctl restart proxy-server
sudo systemctl restart proxy-client
```

## 📝 License

MIT License

---

## 🙋 作者 5777033

* 基于 Python3 开发
* 简易 FRP 替代方案
* 仅供学习交流使用，请勿用于非法用途


