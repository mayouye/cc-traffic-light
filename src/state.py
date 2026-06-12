#!/usr/bin/env python
"""会话状态读取与聚合(被 widget 复用)。

会话状态由 hook.py 写到 ~/.claude/cc-traffic-light/sessions/<id>.json。
本模块负责读取所有会话、清理僵尸会话、并聚合成单一状态。零第三方依赖。
"""
import os
import json
import time
import glob

HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, ".claude", "cc-traffic-light")
SESSIONS_DIR = os.path.join(BASE, "sessions")

STALE_SECONDS = 30 * 60  # 超过该时长未更新的会话视为僵尸,清理

LABELS = {
    "red":    "忙碌(正在处理)",
    "yellow": "等待输入",
    "green":  "空闲",
    "idle":   "无会话",
}


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
