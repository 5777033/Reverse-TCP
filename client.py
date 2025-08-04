import socket
import threading
import logging
from cryptography.fernet import Fernet

logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s] %(message)s')

SERVER_IP = '1.92.112.181'   # 替换成你的服务器公网IP
SERVER_PORT = 6000
CLIENT_ID = 'client1'
PROXY_TO_LOCAL_PORT = {
        6001: 22
        }

FERNET_KEY = b'6aUXWau3OKQ5mV-M5g5CkZxep_t8XzxxUQ_G8GgpNto='  # 与服务器端一致
cipher = Fernet(FERNET_KEY)


def encrypt(data):
    return cipher.encrypt(data)


def decrypt(data):
    return cipher.decrypt(data)


def forward(s1, s2, port):
    try:
        while True:
            data = s1.recv(4096)
            if not data:
                break
            s2.sendall(data)
    except Exception as e:
        logging.debug(f"[端口 {port}] forward 连接异常或关闭: {e}")
    finally:
        try:
            s1.shutdown(socket.SHUT_RD)
        except Exception:
            pass
        try:
            s2.shutdown(socket.SHUT_WR)
        except Exception:
            pass
        s1.close()
        s2.close()
        logging.info(f"[端口 {port}] 连接关闭通知")


def handle_new_conn(proxy_port):
    local_port = PROXY_TO_LOCAL_PORT.get(proxy_port)
    if not local_port:
        logging.error(f"未知本地端口映射: {proxy_port}")
        return

    try:
        local = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        local.connect(('127.0.0.1', local_port))
        logging.info(f"已连接本地服务端口 {local_port}")
    except Exception as e:
        logging.error(f"连接本地服务失败: {e}")
        return

    try:
        data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_sock.connect((SERVER_IP, SERVER_PORT))
        data_sock.sendall(encrypt(f"{CLIENT_ID} {proxy_port}\n".encode()))
        logging.info(f"数据通道建立成功 -> {proxy_port}")
    except Exception as e:
        logging.error(f"连接服务器失败: {e}")
        local.close()
        return

    threading.Thread(target=forward, args=(data_sock, local, proxy_port), daemon=True).start()
    threading.Thread(target=forward, args=(local, data_sock, proxy_port), daemon=True).start()


def listen_control():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_IP, SERVER_PORT))
        sock.sendall(encrypt((CLIENT_ID + '\n').encode()))
        logging.info("控制通道连接成功")
    except Exception as e:
        logging.error(f"控制通道连接失败: {e}")
        return

    try:
        while True:
            data = sock.recv(2048)
            if not data:
                logging.info("控制通道关闭")
                break
            try:
                cmd = decrypt(data).decode().strip()
            except Exception as e:
                logging.error(f"控制通道数据解密失败: {e}")
                continue

            if cmd.startswith('NEW_CONN'):
                _, port = cmd.split()
                port = int(port)
                logging.info(f"收到新连接请求: {port}")
                threading.Thread(target=handle_new_conn, args=(port,), daemon=True).start()
    except Exception as e:
        logging.error(f"控制通道异常断开: {e}")
    finally:
        sock.close()


if __name__ == '__main__':
    listen_control()
