#!/usr/bin/env pythonw
"""Claude Code 红绿灯托盘指示器(多会话聚合)。

轮询 ~/.claude/cc-traffic-light/sessions/ 下所有会话状态文件,聚合后在系统
托盘显示一个彩色圆点:

    任一会话忙碌(red)   -> 红
    否则任一等待输入(yellow) -> 黄
    否则有空闲会话(green)    -> 绿
    无任何会话              -> 灰

陈旧会话(超过 STALE_SECONDS 未更新,通常是崩溃 / 未触发 SessionEnd 的僵尸
会话)会被自动从目录中清理。

依赖:pystray, pillow。建议用 pythonw.exe 启动(无控制台窗口)。
"""
import os
import sys
import json
import time
import glob
import threading

from PIL import Image, ImageDraw
import pystray
from pystray import Menu, MenuItem

HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, ".claude", "cc-traffic-light")
SESSIONS_DIR = os.path.join(BASE, "sessions")

POLL_INTERVAL = 0.6          # 轮询间隔(秒)
STALE_SECONDS = 30 * 60      # 超过该时长未更新的会话视为僵尸,清理

COLORS = {
    "red":    (220, 60, 60),
    "yellow": (240, 190, 40),
    "green":  (60, 190, 90),
    "idle":   (130, 130, 130),
}
LABELS = {
    "red":    "忙碌(正在处理)",
    "yellow": "等待输入",
    "green":  "空闲",
    "idle":   "无会话",
}


def make_icon(color):
    """生成一个该颜色的圆点图标。"""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = 6
    d.ellipse([pad, pad, size - pad, size - pad], fill=color + (255,))
    return img


def read_sessions():
    """读取所有会话状态;顺便清理僵尸会话文件。"""
    out = []
    now = time.time()
    try:
        paths = glob.glob(os.path.join(SESSIONS_DIR, "*.json"))
    except OSError:
        return out
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        if now - d.get("ts", 0) > STALE_SECONDS:
            try:
                os.remove(p)
            except OSError:
                pass
            continue
        out.append(d)
    return out


def aggregate(items):
    """按优先级聚合多个会话状态:red > yellow > green > idle。"""
    if not items:
        return "idle"
    states = {i.get("state") for i in items}
    if "red" in states:
        return "red"
    if "yellow" in states:
        return "yellow"
    return "green"


class App:
    def __init__(self):
        try:
            os.makedirs(SESSIONS_DIR, exist_ok=True)
        except OSError:
            pass
        self._icons = {k: make_icon(v) for k, v in COLORS.items()}
        self.current = "idle"
        self.sessions = []
        self.icon = pystray.Icon(
            "cc-traffic-light",
            self._icons["idle"],
            "Claude Code",
            menu=Menu(
                MenuItem(self._status_text, lambda *a: None, enabled=False),
                Menu.SEPARATOR,
                MenuItem("打开会话目录", self._open_dir),
                MenuItem("退出", self._quit),
            ),
        )

    def _status_text(self, item=None):
        return "{} · {} 个会话".format(LABELS.get(self.current, ""), len(self.sessions))

    def _open_dir(self, *args):
        try:
            os.startfile(BASE)  # noqa: S606 (Windows only)
        except Exception:
            pass

    def _quit(self, *args):
        self.icon.stop()

    def _loop(self):
        while True:
            items = read_sessions()
            agg = aggregate(items)
            self.sessions = items
            if agg != self.current:
                self.current = agg
                try:
                    self.icon.icon = self._icons[agg]
                except Exception:
                    pass
            try:
                self.icon.title = "Claude Code: " + LABELS.get(agg, "")
            except Exception:
                pass
            time.sleep(POLL_INTERVAL)

    def run(self):
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()
        self.icon.run()


if __name__ == "__main__":
    App().run()
