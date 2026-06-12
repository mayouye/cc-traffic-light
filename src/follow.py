#!/usr/bin/env python
"""用 Win32 API(纯标准库 ctypes,无 pywin32)定位 Claude Code 所在终端窗口。

对外只暴露 find_terminal_rect():返回目标终端窗口的 (x, y, w, h),供悬浮窗
吸附;窗口最小化 / 找不到时返回 None。
"""
import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
DWMWA_EXTENDED_FRAME_BOUNDS = 9  # 取窗口真实可见边界(排除 Win11 隐形边框)

# 默认匹配的终端进程名(小写)。Claude Code 常见宿主。
DEFAULT_NAMES = (
    "windowsterminal.exe",  # Windows Terminal
    "wt.exe",
)

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]

kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)
]


def _process_name(pid):
    """返回进程 exe 文件名(小写),失败返回 ''。"""
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buf))
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            path = buf.value
            return path.rsplit("\\", 1)[-1].lower()
        return ""
    finally:
        kernel32.CloseHandle(h)


def _rect(hwnd):
    r = wintypes.RECT()
    # 优先用 DWM 真实可见边界:GetWindowRect 在 Win11 上会多算约 7px 隐形边框,
    # 导致贴右/对齐时偏出。DwmGetWindowAttribute 返回的才是肉眼可见的窗口框。
    try:
        if dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(r), ctypes.sizeof(r)
        ) == 0:
            return (r.left, r.top, r.right - r.left, r.bottom - r.top)
    except Exception:
        pass
    if user32.GetWindowRect(hwnd, ctypes.byref(r)):
        return (r.left, r.top, r.right - r.left, r.bottom - r.top)
    return None


def find_terminal_rect(names=DEFAULT_NAMES):
    """找到目标终端窗口的矩形 (x, y, w, h)。

    优先返回前台窗口(若它本身就是目标终端);否则返回枚举到的第一个可见、
    未最小化的目标窗口。都没有则返回 None。
    """
    names = tuple(n.lower() for n in names)

    # 先看前台窗口
    fg = user32.GetForegroundWindow()
    if fg and not user32.IsIconic(fg):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
        if _process_name(pid.value) in names:
            r = _rect(fg)
            if r:
                return r

    found = []

    def _cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if _process_name(pid.value) in names:
            r = _rect(hwnd)
            if r and r[2] > 0 and r[3] > 0:
                found.append(r)
                return False  # 找到一个就停
        return True

    user32.EnumWindows(WNDENUMPROC(_cb), 0)
    return found[0] if found else None


if __name__ == "__main__":
    print("terminal rect:", find_terminal_rect())
