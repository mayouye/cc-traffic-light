# cc-traffic-light

[English](README.md) | **中文**

给 Windows 上 [Claude Code](https://claude.com/claude-code) 用的**悬浮红绿灯**。
一个置顶的小挂件,一眼看出 Claude 当前是在**干活**、在**等你**、还是**空闲** ——
并且会**聚合你打开的所有 Claude Code 窗口**的状态,还能自动吸附到终端窗口上。

| 灯 | 含义 |
| :---: | --- |
| 🔴 红 | 至少有一个会话正忙(Claude 正在处理) |
| 🟡 黄 | 有会话需要你输入 / 确认权限 |
| 🟢 绿 | 所有会话都空闲 |
| ⚫ 暗 | 当前没有活动会话 |

基于 **PySide6** 构建。窗口跟踪用标准库 `ctypes` 调 Windows API(**不需要** `pywin32`)。仅支持 Windows。

## 特性

- **三联灯**悬浮挂件 —— 当前激活的灯带柔和发光晕染 + 轻微呼吸动画。
- **自动吸附终端** —— 跟随 Windows Terminal 窗口(右上角),窗口移动灯也跟着走。
  用窗口的**真实可见边界**(DWM extended frame),所以能和窗口边缘严丝合缝地对齐。
- **随手拖动** 即切换为手动定位,并记住你放的位置。
- **收起** 成一个小圆点(双击,或右键菜单)以节省空间。
- **右键菜单**:切换 跟随 / 手动、收起 / 展开、退出。
- **多窗口聚合** —— 汇总所有会话:任一忙 → 红,否则任一等待 → 黄,否则绿。

## 工作原理

Claude Code 会在会话事件时触发 [hooks](https://docs.claude.com/en/docs/claude-code/hooks)。
一个很小的 `hook.py` 从 stdin 读取事件 JSON,把该会话的当前状态写到独立文件:

```
~/.claude/cc-traffic-light/sessions/<session_id>.json
```

| Hook 事件 | 状态 |
| --- | --- |
| `UserPromptSubmit` | 红 |
| `Notification` | 黄 |
| `Stop` / `SubagentStop` | 绿 |
| `SessionEnd` | (删除该文件) |

挂件 `widget.pyw` 每秒轮询约 2 次该目录,聚合所有会话状态(优先级 `红 > 黄 > 绿`),
点亮对应的灯。对于变"陈旧"的会话(崩溃、未触发 `SessionEnd`,超过 30 分钟没更新的僵尸会话)会被自动清理。

## 安装

需要 Windows + Python 3.9 及以上。

```sh
git clone https://github.com/mayouye/cc-traffic-light.git
cd cc-traffic-light
pip install -r requirements.txt

# 把 hooks 注册进 ~/.claude/settings.json(会自动备份原文件)
python src/install.py
```

然后启动挂件:

```sh
# 静默启动(无控制台窗口)
start-widget.vbs
```

或直接用 `pythonw src\widget.pyw` 运行。

### 开机自启(可选)

按 <kbd>Win</kbd>+<kbd>R</kbd>,运行 `shell:startup`,把 `start-widget.vbs` 的快捷方式拖进那个文件夹即可。

## 配置

挂件的状态存在 `~/.claude/cc-traffic-light/widget.json`:

| 键 | 含义 |
| --- | --- |
| `mode` | `follow`(吸附终端)或 `manual`(固定位置) |
| `pos` | 手动模式下保存的 `[x, y]` |
| `collapsed` | 是否收起成小圆点 |
| `dock_top` | 跟随时距终端顶部的偏移(默认 46) |
| `dock_right` | 跟随时距终端右边的间隙(默认 2,越小越贴右) |

## 卸载

```sh
python src/install.py --uninstall   # 从 settings.json 中移除 hooks
```

之后删掉开机自启的快捷方式和本仓库目录即可。状态目录 `~/.claude/cc-traffic-light/` 也可以一并删除。

## 说明

- hooks 用 `pythonw.exe` 运行(取自执行 `install.py` 时的那个 Python),所以**每次提交 prompt 不会闪黑框**。
- `install.py` 是**合并**写入 `settings.json` —— 你已有的 hooks / 配置都会保留,原文件备份到 `settings.json.bak`。
- hook 脚本**零第三方依赖**,且吞掉所有异常,所以绝不会拖慢或搞坏 Claude Code。

## 许可证

MIT
