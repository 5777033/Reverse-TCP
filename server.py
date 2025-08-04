import socket
import threading
import select
import logging
from cryptography.fernet import Fernet

logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s] %(message)s')

SERVER_IP = '0.0.0.0'
SERVER_PORT = 6000
PROXY_PORTS = {6001: 22}
#PROXY_PORTS = {6001: 22, 6002: 80}

FERNET_KEY = b'6aUXWau3OKQ5mV-M5g5CkZxep_t8XzxxUQ_G8GgpNto='  # 替换为生成的key
cipher = Fernet(FERNET_KEY)

clients = {}          # {client_id: control_socket}
pending_conn = {}      # {(client_id, proxy_port): external_socket}
proxy_sockets = {}     # {proxy_port: listening_socket}
active_clients = set() # 当前在线客户端

def encrypt(data):
    return cipher.encrypt(data)

def decrypt(data):
    return cipher.decrypt(data)

def relay(s1, s2, port):
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
    except Exception:
        pass
    finally:
        s1.close()
        s2.close()
        logging.info(f"[端口 {port}] 数据通道关闭")

def proxy_listener(proxy_port):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    srv.bind((SERVER_IP, proxy_port))
    srv.listen(50)
    proxy_sockets[proxy_port] = srv
    logging.info(f"[端口 {proxy_port}] 代理端口启动")

    while True:
        sock, addr = srv.accept()
        if not clients:
            logging.warning(f"[端口 {proxy_port}] 无客户端在线，拒绝连接 {addr}")
            sock.close()
            continue
        cid, ctrl = next(iter(clients.items()))
        try:
            ctrl.sendall(encrypt(f"NEW_CONN {proxy_port}\n".encode()))
            pending_conn[(cid, proxy_port)] = sock
            logging.info(f"[端口 {proxy_port}] 外部连接 {addr}")
        except Exception as e:
            logging.error(f"[端口 {proxy_port}] 通知客户端失败: {e}")
            sock.close()

def handle_client_connection(conn, addr):
    try:
        header = decrypt(conn.recv(2048)).decode().strip()
        if ' ' in header:
            # 数据通道
            cid, port = header.split()
            port = int(port)
            key = (cid, port)
            if key in pending_conn:
                external = pending_conn.pop(key)
                logging.info(f"[端口 {port}] 建立数据通道")
                relay(external, conn, port)
            else:
                conn.close()
        else:
            # 控制通道
            cid = header
            clients[cid] = conn
            active_clients.add(cid)
            logging.info(f"客户端注册成功: {cid}")

            while True:
                data = conn.recv(2048)
                if not data:
                    break
                _ = decrypt(data)

            # 客户端下线
            if cid in clients:
                del clients[cid]
            active_clients.discard(cid)
            logging.info(f"客户端下线: {cid}")

            if not active_clients:
                logging.info("所有客户端下线，暂停所有代理端口监听")
    except Exception as e:
        logging.error(f"控制通道异常: {e}")
    finally:
        conn.close()

def main():
    # 启动所有代理端口线程
    for p in PROXY_PORTS:
        threading.Thread(target=proxy_listener, args=(p,), daemon=True).start()

    # 启动控制服务
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((SERVER_IP, SERVER_PORT))
    srv.listen(100)
    logging.info(f"服务器启动，监听端口: {SERVER_PORT}")

    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client_connection, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
