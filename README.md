# cc-traffic-light

**English** | [中文](README.zh-CN.md)

A floating **traffic light** for [Claude Code](https://claude.com/claude-code) on Windows.
A small always-on-top widget that shows, at a glance, whether Claude is **working**,
**waiting for you**, or **idle** — aggregated across **all open Claude Code windows** —
and automatically docks to your terminal window.

| Light | Meaning |
| :---: | --- |
| 🔴 Red | At least one session is busy (Claude is processing) |
| 🟡 Yellow | A session needs your input / permission |
| 🟢 Green | All sessions idle |
| ⚫ Dim | No active sessions |

Built with **PySide6**. Window tracking uses the Windows API via the standard-library
`ctypes` (no `pywin32`). Windows-only.

## Features

- **Three-lamp traffic light** floating widget — the active lamp glows with a soft halo
  and a gentle breathing animation.
- **Auto-docks to the terminal** — follows your Windows Terminal window (top-right),
  moving with it. Uses the true visible window bounds (DWM extended frame) so it aligns
  flush with the window edge.
- **Drag anywhere** to switch to manual positioning; it remembers where you put it.
- **Collapse** to a single dot (double-click, or right-click menu) to save space.
- **Right-click menu**: toggle follow / manual, collapse / expand, quit.
- **Multi-window aware** — aggregates every session: any busy → red, else any waiting →
  yellow, else green.

## How it works

Claude Code fires [hooks](https://docs.claude.com/en/docs/claude-code/hooks) on session
events. A tiny `hook.py` reads the event JSON on stdin and writes a per-session state file:

```
~/.claude/cc-traffic-light/sessions/<session_id>.json
```

| Hook event | State |
| --- | --- |
| `UserPromptSubmit` | red |
| `Notification` | yellow |
| `Stop` / `SubagentStop` | green |
| `SessionEnd` | (file removed) |

The widget (`widget.pyw`) polls that directory ~2×/sec, aggregates
(`red > yellow > green`), and updates the lit lamp. Sessions that go stale (crashed
without `SessionEnd`, >30 min without an update) are cleaned up automatically.

## Install

Requires Windows + Python 3.9+.

```sh
git clone https://github.com/mayouye/cc-traffic-light.git
cd cc-traffic-light
pip install -r requirements.txt

# Register the hooks in ~/.claude/settings.json (backs up the original)
python src/install.py
```

Then start the widget:

```sh
# Silent launch (no console window)
start-widget.vbs
```

Or run directly with `pythonw src\widget.pyw`.

### Auto-start on login (optional)

Press <kbd>Win</kbd>+<kbd>R</kbd>, run `shell:startup`, and drop a shortcut to
`start-widget.vbs` into that folder.

## Settings

The widget stores its state in `~/.claude/cc-traffic-light/widget.json`:

| Key | Meaning |
| --- | --- |
| `mode` | `follow` (dock to terminal) or `manual` (fixed position) |
| `pos` | saved `[x, y]` for manual mode |
| `collapsed` | collapsed to a single dot |
| `dock_top` | vertical offset from the terminal top (default 46) |
| `dock_right` | gap from the terminal right edge (default 2, smaller = tighter) |

## Uninstall

```sh
python src/install.py --uninstall   # removes the hooks from settings.json
```

Then delete the startup shortcut and the repo folder. The state directory at
`~/.claude/cc-traffic-light/` can be removed too.

## Notes

- Hooks run with `pythonw.exe` (resolved from the Python that ran `install.py`), so there
  is **no console flash** on every prompt.
- `install.py` **merges** into `settings.json` — your existing hooks/config are preserved,
  and the original is backed up to `settings.json.bak`.
- The hook script has **zero third-party dependencies** and swallows all errors, so it can
  never slow down or break Claude Code.

## License

MIT
