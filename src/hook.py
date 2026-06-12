#!/usr/bin/env python
"""Claude Code hook -> 写入单会话红绿灯状态。

由 Claude Code 在各 hook 事件时调用,从 stdin 读取事件 JSON(含 session_id /
hook_event_name / cwd),把该会话当前状态写到:

    ~/.claude/cc-traffic-light/sessions/<session_id>.json

托盘程序(tray.pyw)轮询该目录并聚合所有会话状态。本脚本零第三方依赖,
力求极快、永不抛错(任何异常都静默吞掉,避免拖慢 / 打断 Claude Code)。
"""
import sys
import os
import json
import time

STATE_DIR = os.path.join(
    os.path.expanduser("~"), ".claude", "cc-traffic-light", "sessions"
)

# 事件 -> 颜色状态
EVENT_STATE = {
    "UserPromptSubmit": "red",     # 用户提交,Claude 开始处理
    "Notification": "yellow",      # 需要用户输入 / 权限确认
    "Stop": "green",               # 主回合结束,空闲
    "SubagentStop": "green",       # 子 agent 结束
}


def main():
    try:
        raw = sys.stdin.read()
    except Exception:
        raw = ""
    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    event = data.get("hook_event_name") or (sys.argv[1] if len(sys.argv) > 1 else "")
    session_id = data.get("session_id") or "default"
    cwd = data.get("cwd") or ""

    try:
        os.makedirs(STATE_DIR, exist_ok=True)
    except Exception:
        return

    path = os.path.join(STATE_DIR, session_id + ".json")

    # 会话结束:清理该会话的状态文件
    if event == "SessionEnd":
        try:
            os.remove(path)
        except OSError:
            pass
        return

    state = EVENT_STATE.get(event)
    if state is None:
        return

    payload = {
        "state": state,
        "event": event,
        "cwd": cwd,
        "ts": time.time(),
    }
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmp, path)  # 原子替换,避免托盘读到半截文件
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass


if __name__ == "__main__":
    main()
