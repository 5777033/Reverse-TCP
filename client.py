import socket
import threading
import logging
from cryptography.fernet import Fernet

logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s] %(message)s')

SERVER_IP = 'your.server.ip'   # 改成你的公网服务器IP
SERVER_PORT = 6000
CLIENT_ID = 'client1'
PROXY_TO_LOCAL_PORT = {6001: 22, 6002: 80}

FERNET_KEY = b'6aUXWau3OKQ5mV-M5g5CkZxep_t8XzxxUQ_G8GgpNto='  # 与服务端一致
cipher = Fernet(FERNET_KEY)

def encrypt(data):
    return cipher.encrypt(data)

def decrypt(data):
    return cipher.decrypt(data)

def forward(s1, s2):
    try:
        while True:
            data = s1.recv(4096)
            if not data:
                break
            s2.sendall(data)
    finally:
        s1.close()
        s2.close()

def handle_new_conn(proxy_port):
    local_port = PROXY_TO_LOCAL_PORT.get(proxy_port)
    if not local_port:
        return
    try:
        local = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        local.connect(('127.0.0.1', local_port))
    except:
        return

    data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    data_sock.connect((SERVER_IP, SERVER_PORT))
    data_sock.sendall(encrypt(f"{CLIENT_ID} {proxy_port}\n".encode()))

    threading.Thread(target=forward, args=(data_sock, local), daemon=True).start()
    threading.Thread(target=forward, args=(local, data_sock), daemon=True).start()

def listen_control():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_IP, SERVER_PORT))
    sock.sendall(encrypt((CLIENT_ID + '\n').encode()))
    logging.info("已连接控制通道")
    try:
        while True:
            data = sock.recv(2048)
            if not data:
                break
            cmd = decrypt(data).decode().strip()
            if cmd.startswith('NEW_CONN'):
                _, port = cmd.split()
                port = int(port)
                threading.Thread(target=handle_new_conn, args=(port,), daemon=True).start()
    finally:
        sock.close()

if __name__ == '__main__':
    listen_control()
