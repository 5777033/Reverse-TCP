import socket
import threading
import select
import logging
from cryptography.fernet import Fernet

logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s] %(message)s')

SERVER_IP = '0.0.0.0'
SERVER_PORT = 6000
PROXY_PORTS = {6001: 22, 6002: 80}

FERNET_KEY = b'6aUXWau3OKQ5mV-M5g5CkZxep_t8XzxxUQ_G8GgpNto='  # 替换为你生成的key
cipher = Fernet(FERNET_KEY)

clients = {}
pending_conn = {}

def encrypt(data):
    return cipher.encrypt(data)

def decrypt(data):
    return cipher.decrypt(data)

def relay(s1, s2):
    try:
        sockets = [s1, s2]
        while True:
            r, _, _ = select.select(sockets, [], [])
            for sock in r:
                data = sock.recv(4096)
                if not data:
                    return
                if sock is s1:
                    s2.sendall(data)
                else:
                    s1.sendall(data)
    finally:
        s1.close()
        s2.close()

def handle_proxy_port(proxy_port):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((SERVER_IP, proxy_port))
    srv.listen(50)
    logging.info(f"代理端口启动: {proxy_port}")
    while True:
        sock, addr = srv.accept()
        if not clients:
            sock.close()
            continue
        cid, ctrl = next(iter(clients.items()))
        try:
            ctrl.sendall(encrypt(f"NEW_CONN {proxy_port}\n".encode()))
            pending_conn[(cid, proxy_port)] = sock
        except:
            sock.close()

def handle_client_connection(conn):
    try:
        header = decrypt(conn.recv(2048)).decode().strip()
        if ' ' in header:
            cid, port = header.split()
            port = int(port)
            key = (cid, port)
            if key in pending_conn:
                external = pending_conn.pop(key)
                relay(external, conn)
            else:
                conn.close()
        else:
            cid = header
            clients[cid] = conn
            logging.info(f"客户端注册成功: {cid}")
            while True:
                data = conn.recv(2048)
                if not data:
                    break
                _ = decrypt(data)  # 这里可以忽略内容
            if cid in clients:
                del clients[cid]
    except Exception as e:
        logging.error(f"控制通道异常: {e}")
    finally:
        conn.close()

def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((SERVER_IP, SERVER_PORT))
    srv.listen(100)
    logging.info(f"服务器启动，监听端口: {SERVER_PORT}")

    for p in PROXY_PORTS:
        threading.Thread(target=handle_proxy_port, args=(p,), daemon=True).start()

    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client_connection, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    main()
