"""Минимальный RCON-клиент (Source RCON) без внешних зависимостей.

Minecraft 1.8.9 поддерживает RCON (enable-rcon=true). Этим клиентом мы
строим арену, телепортируем ботов и выдаём предметы командами сервера.
"""
import socket
import struct


class RCON:
    def __init__(self, host, port, password, timeout=10.0):
        self.host = host
        self.port = port
        self.password = password
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host, port))
        # login (type 3 = SERVERDATA_AUTH)
        self._send(3, self.password)
        rid, _ptype, _payload = self._recv_packet()
        if rid == -1:
            self.sock.close()
            raise RuntimeError("RCON auth failed (wrong rcon.password?)")

    def _send(self, ptype, payload):
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        body = struct.pack("<ii", 0, ptype) + payload + b"\x00\x00"
        self.sock.sendall(struct.pack("<i", len(body)) + body)

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("RCON connection closed")
            buf += chunk
        return buf

    def _recv_packet(self):
        length = struct.unpack("<i", self._recv_exact(4))[0]
        data = self._recv_exact(length)
        rid = struct.unpack("<i", data[:4])[0]
        ptype = struct.unpack("<i", data[4:8])[0]
        payload = data[8:-2].decode("utf-8", "ignore")
        return rid, ptype, payload

    def command(self, cmd):
        self._send(2, cmd)  # type 2 = SERVERDATA_EXECCOMMAND
        rid, _ptype, payload = self._recv_packet()
        # некоторые серверы шлют пустой пакет-маркер перед реальным ответом
        if payload == "":
            rid, _ptype, payload = self._recv_packet()
        return payload

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
