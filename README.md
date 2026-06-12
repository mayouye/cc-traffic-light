# cc-traffic-light

A tiny system-tray **traffic light** for [Claude Code](https://claude.com/claude-code) on Windows.
It shows, at a glance, whether Claude is **working**, **waiting for you**, or **idle** —
aggregated across **all open Claude Code windows**.

| Color | Meaning |
| :---: | --- |
| 🔴 Red | At least one session is busy (Claude is processing) |
| 🟡 Yellow | A session needs your input / permission |
| 🟢 Green | All sessions idle |
| ⚪ Gray | No active sessions |

Pure Python (`pystray` + `pillow`), no binary assets, ~250 lines. Windows-only.

## How it works

Claude Code fires [hooks](https://docs.claude.com/en/docs/claude-code/hooks) on
session events. A small `hook.py` reads the event JSON on stdin and writes a
per-session state file:

```
~/.claude/cc-traffic-light/sessions/<session_id>.json
```

| Hook event | State |
| --- | --- |
| `UserPromptSubmit` | red |
| `Notification` | yellow |
| `Stop` / `SubagentStop` | green |
| `SessionEnd` | (file removed) |

The tray app (`tray.pyw`) polls that directory ~2×/sec, aggregates
(`red > yellow > green`), and updates the tray icon. Sessions that go stale
(crashed without `SessionEnd`, >30 min without an update) are cleaned up
automatically.

## Install

Requires Python 3.9+ on Windows.

```sh
git clone https://github.com/<you>/cc-traffic-light.git
cd cc-traffic-light
pip install -r requirements.txt

# Register the hooks in ~/.claude/settings.json (backs up the original)
python src/install.py
```

Then start the tray app:

```sh
# Silent launch (no console window)
start-tray.vbs
```

Or run directly with `pythonw src\tray.pyw`.

### Auto-start on login (optional)

Press <kbd>Win</kbd>+<kbd>R</kbd>, run `shell:startup`, and drop a shortcut to
`start-tray.vbs` into that folder.

## Uninstall

```sh
python src/install.py --uninstall   # removes the hooks from settings.json
```

Then delete the startup shortcut and the repo folder. The state directory at
`~/.claude/cc-traffic-light/` can be removed too.

## Notes

- Hooks run with `pythonw.exe` (resolved from the Python that ran
  `install.py`) so there is **no console flash** on every prompt.
- `install.py` **merges** into `settings.json` — your existing hooks/config are
  preserved, and the original is backed up to `settings.json.bak`.
- The hook script has **zero third-party dependencies** and swallows all
  errors, so it can never slow down or break Claude Code.

## License

MIT
