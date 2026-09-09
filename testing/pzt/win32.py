"""Win32 helpers: find a client's game window and post input to it.

PostMessage goes through GLFW's window procedure like real input, but needs no
focus change, so driven clients can sit behind other windows.
"""
import ctypes
import ctypes.wintypes as w
import os
import time

WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP = 0x0200, 0x0201, 0x0202
user32 = ctypes.windll.user32 if os.name == "nt" else None


def find_windows(pid=None, title="Project Zomboid"):
    """Visible top-level windows with this title, optionally owned by one process."""
    found = []
    if user32 is None:
        return found

    @ctypes.WINFUNCTYPE(ctypes.c_bool, w.HWND, w.LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        if buf.value != title:
            return True
        if pid is not None:
            owner = w.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value != pid:
                return True
        found.append(hwnd)
        return True
    user32.EnumWindows(cb, 0)
    return found


def post_click(hwnd, hold=0.12):
    """Left click in the middle of the client area, held for a few frames."""
    r = w.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    lparam = ((r.bottom // 2) << 16) | (r.right // 2)
    user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
    user32.PostMessageW(hwnd, WM_LBUTTONDOWN, 1, lparam)
    time.sleep(hold)
    user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)
