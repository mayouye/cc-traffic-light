#!/usr/bin/env python
"""安装器:把红绿灯 hooks 写入 Claude Code 的 settings.json。

- 自动探测当前 Python 的 pythonw.exe(hook 用它执行,避免每次事件闪黑框)
- 备份原 settings.json 到 settings.json.bak
- 合并(而非覆盖)hooks 配置;若已存在本程序的 hook 则跳过,可重复运行

用法:
    python install.py            # 安装到 ~/.claude/settings.json
    python install.py --uninstall # 移除本程序写入的 hooks
"""
import os
import sys
import json
import shutil

HOME = os.path.expanduser("~")
SETTINGS = os.path.join(HOME, ".claude", "settings.json")
HOOK_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook.py")

# 这些事件交给同一个 hook.py 处理
EVENTS = ["UserPromptSubmit", "Notification", "Stop", "SubagentStop", "SessionEnd"]


def pythonw_exe():
    """返回与当前解释器配套的 pythonw.exe 路径(找不到则退回 python.exe)。"""
    exe = sys.executable
    cand = exe.replace("python.exe", "pythonw.exe")
    return cand if os.path.exists(cand) else exe


def hook_command():
    return '"{}" "{}"'.format(pythonw_exe(), HOOK_SCRIPT)


def is_ours(entry):
    """判断某个 hook 配置项是否由本程序写入(按 hook.py 路径识别)。"""
    for h in entry.get("hooks", []):
        if HOOK_SCRIPT.lower() in str(h.get("command", "")).lower():
            return True
    return False


def load_settings():
    if not os.path.exists(SETTINGS):
        return {}
    with open(SETTINGS, encoding="utf-8") as f:
        return json.load(f)


def save_settings(data):
    if os.path.exists(SETTINGS):
        shutil.copyfile(SETTINGS, SETTINGS + ".bak")
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def install():
    data = load_settings()
    hooks = data.setdefault("hooks", {})
    cmd = hook_command()
    for ev in EVENTS:
        lst = hooks.setdefault(ev, [])
        # 移除本程序的旧条目,再写入新的(便于升级路径)
        lst[:] = [e for e in lst if not is_ours(e)]
        lst.append({"hooks": [{"type": "command", "command": cmd}]})
    save_settings(data)
    print("已安装 hooks 到", SETTINGS)
    print("hook 命令:", cmd)
    print("事件:", ", ".join(EVENTS))
    print("（已备份原文件到 settings.json.bak）")


def uninstall():
    data = load_settings()
    hooks = data.get("hooks", {})
    for ev in list(hooks.keys()):
        hooks[ev] = [e for e in hooks[ev] if not is_ours(e)]
        if not hooks[ev]:
            del hooks[ev]
    if not hooks:
        data.pop("hooks", None)
    save_settings(data)
    print("已移除本程序写入的 hooks。")


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        uninstall()
    else:
        install()
