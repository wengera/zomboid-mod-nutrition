"""Minimal Source-RCON client (the dedicated server speaks the Valve protocol)."""
import socket
import struct


def rcon(host, port, password, cmd, timeout=5.0):
    """Auth then exec one command. Returns (ok, reply_text)."""
    def pkt(pid, ptype, body):
        b = body.encode() + b"\x00\x00"
        return struct.pack("<iii", len(b) + 8, pid, ptype) + b
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            s.sendall(pkt(1, 3, password))
            hdr = s.recv(4096)
            if len(hdr) < 12:
                return False, "short auth reply"
            _, pid, _ = struct.unpack("<iii", hdr[:12])
            if pid == -1:
                return False, "auth refused"
            s.sendall(pkt(2, 2, cmd))
            try:
                reply = s.recv(4096)
            except socket.timeout:
                reply = b""
            return True, reply[12:].decode(errors="replace").strip("\x00")
    except OSError as e:
        return False, str(e)
