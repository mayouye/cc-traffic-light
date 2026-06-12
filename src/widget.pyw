#!/usr/bin/env pythonw
"""Claude Code 悬浮红绿灯(PySide6,三联灯)。

屏幕上一个无边框、置顶、半透明的小红绿灯,聚合所有 Claude Code 会话状态:
    任一忙(red) > 有等待(yellow) > 空闲(green) > 无会话(idle 全暗)

特性:
- 自动吸附 / 跟随 Windows Terminal 窗口(右上角),也可拖动切换为手动定位
- 双击或右键菜单可收起成单灯小圆点
- 激活灯带发光晕染 + 轻微呼吸动画
- 位置 / 模式 / 收起态持久化到 ~/.claude/cc-traffic-light/widget.json

依赖:PySide6(窗口跟踪用标准库 ctypes,见 follow.py)。建议用 pythonw 启动。
"""
import os
import sys
import json

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import (
    Qt, QTimer, QPointF, Property, QPropertyAnimation, QEasingCurve,
)

# 允许以脚本方式运行时导入同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state as state_mod      # noqa: E402
import follow as follow_mod    # noqa: E402

# ---- 几何 ----
LAMP_R = 15
GAP = 12
PAD_V = 14
PAD_H = 13
MARGIN = 14                                   # 发光晕染留白,避免被裁切
HOUSING_W = 2 * LAMP_R + 2 * PAD_H            # 56
HOUSING_H = 3 * 2 * LAMP_R + 2 * GAP + 2 * PAD_V  # 142
FULL_W = HOUSING_W + 2 * MARGIN               # 84
FULL_H = HOUSING_H + 2 * MARGIN               # 170
COLLAPSED_W = 2 * LAMP_R + 2 * MARGIN         # 58

ORDER = ["red", "yellow", "green"]
COLORS = {
    "red":    QtGui.QColor(0xDC, 0x3C, 0x3C),
    "yellow": QtGui.QColor(0xF0, 0xBE, 0x28),
    "green":  QtGui.QColor(0x3C, 0xBE, 0x5A),
}

CONFIG = os.path.join(state_mod.BASE, "widget.json")
DEFAULT_CFG = {
    "mode": "follow",
    "pos": [None, None],
    "collapsed": False,
    "dock_top": 46,    # 跟随时距终端顶部的偏移(避开标签栏)
    "dock_right": 2,   # 跟随时灯箱右缘距终端右边的间隙(越小越贴右)
}


def load_cfg():
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CONFIG, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_cfg(cfg):
    try:
        os.makedirs(state_mod.BASE, exist_ok=True)
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
    except Exception:
        pass


class TrafficLight(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.cfg = load_cfg()
        self.current = "idle"
        self.collapsed = bool(self.cfg.get("collapsed"))
        self._drag_off = None
        self._pulse = 0.0

        self.setWindowTitle("cc-traffic-light")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setToolTip("Claude Code")

        # 呼吸动画(0->1->0 循环),仅激活时运行
        self._pulse_anim = QPropertyAnimation(self, b"pulse")
        self._pulse_anim.setDuration(1600)
        self._pulse_anim.setKeyValueAt(0.0, 0.0)
        self._pulse_anim.setKeyValueAt(0.5, 1.0)
        self._pulse_anim.setKeyValueAt(1.0, 0.0)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_anim.setLoopCount(-1)

        self._apply_size()

        # 轮询会话状态
        self._poll = QTimer(self)
        self._poll.timeout.connect(self._refresh_state)
        self._poll.start(500)

        # 跟随窗口
        self._track = QTimer(self)
        self._track.timeout.connect(self._reposition)
        self._track.start(300)

        self._refresh_state()
        if self.cfg.get("mode") == "manual":
            x, y = self.cfg.get("pos", [None, None])
            if x is not None and y is not None:
                self.move(int(x), int(y))
            self.show()
        else:
            self._reposition()
            self.show()

    # ---- 呼吸动画属性 ----
    def _get_pulse(self):
        return self._pulse

    def _set_pulse(self, v):
        self._pulse = v
        self.update()

    pulse = Property(float, _get_pulse, _set_pulse)

    def _apply_size(self):
        self.setFixedSize(COLLAPSED_W, COLLAPSED_W) if self.collapsed \
            else self.setFixedSize(FULL_W, FULL_H)

    # ---- 状态 ----
    def _refresh_state(self):
        agg = state_mod.aggregate(state_mod.read_sessions())
        if agg != self.current:
            self.current = agg
            self.setToolTip("Claude Code: " + state_mod.LABELS.get(agg, ""))
            if agg == "idle":
                self._pulse_anim.stop()
                self._pulse = 0.0
            elif self._pulse_anim.state() != QPropertyAnimation.State.Running:
                self._pulse_anim.start()
            self.update()

    # ---- 跟随 / 定位 ----
    def _reposition(self):
        if self.cfg.get("mode") != "follow":
            return
        r = follow_mod.find_terminal_rect()
        if r is None:
            if self.isVisible():
                self.hide()
            return
        if not self.isVisible():
            self.show()
        tx, ty, tw, _th = r
        vis_w = (2 * LAMP_R) if self.collapsed else HOUSING_W
        dock_right = self.cfg.get("dock_right", 2)
        dock_top = self.cfg.get("dock_top", 46)
        # 让可见灯箱右缘贴近终端右边(扣掉透明发光留白 MARGIN)
        self.move(tx + tw - MARGIN - vis_w - dock_right, ty + dock_top)

    # ---- 绘制 ----
    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        if self.collapsed:
            cx = cy = COLLAPSED_W / 2
            if self.current == "idle":
                self._draw_lamp(p, cx, cy, QtGui.QColor(120, 120, 120), False)
            else:
                self._draw_lamp(p, cx, cy, COLORS[self.current], True)
        else:
            rect = QtCore.QRectF(MARGIN, MARGIN, HOUSING_W, HOUSING_H)
            p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 28), 1))
            p.setBrush(QtGui.QColor(22, 24, 28, 235))
            p.drawRoundedRect(rect, 16, 16)
            cx = MARGIN + HOUSING_W / 2
            for i, name in enumerate(ORDER):
                cy = MARGIN + PAD_V + LAMP_R + i * (2 * LAMP_R + GAP)
                self._draw_lamp(p, cx, cy, COLORS[name], name == self.current)

    def _draw_lamp(self, p, cx, cy, color, active):
        center = QPointF(cx, cy)
        if active:
            intensity = 0.6 + 0.4 * self._pulse
            glow_r = LAMP_R * (2.0 + 0.4 * self._pulse)
            grad = QtGui.QRadialGradient(cx, cy, glow_r)
            c_in = QtGui.QColor(color)
            c_in.setAlpha(int(150 * intensity))
            c_out = QtGui.QColor(color)
            c_out.setAlpha(0)
            grad.setColorAt(0.0, c_in)
            grad.setColorAt(1.0, c_out)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(grad)
            p.drawEllipse(center, glow_r, glow_r)
            p.setBrush(QtGui.QColor(color))
            p.drawEllipse(center, LAMP_R, LAMP_R)
            # 高光
            p.setBrush(QtGui.QColor(255, 255, 255, 90))
            p.drawEllipse(QPointF(cx - LAMP_R * 0.3, cy - LAMP_R * 0.35),
                          LAMP_R * 0.34, LAMP_R * 0.27)
        else:
            dim = QtGui.QColor(color.red() // 5 + 16,
                               color.green() // 5 + 16,
                               color.blue() // 5 + 16)
            p.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 90), 1))
            p.setBrush(dim)
            p.drawEllipse(center, LAMP_R, LAMP_R)

    # ---- 交互 ----
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_off = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if (e.buttons() & Qt.MouseButton.LeftButton) and self._drag_off is not None:
            self.move(e.globalPosition().toPoint() - self._drag_off)
            self.cfg["mode"] = "manual"   # 拖动即脱离跟随
            e.accept()

    def mouseReleaseEvent(self, e):
        if self._drag_off is not None:
            self._drag_off = None
            if self.cfg.get("mode") == "manual":
                self.cfg["pos"] = [self.x(), self.y()]
                save_cfg(self.cfg)

    def mouseDoubleClickEvent(self, e):
        self._toggle_collapsed()

    def contextMenuEvent(self, e):
        menu = QtWidgets.QMenu()
        follow = self.cfg.get("mode") == "follow"
        a_mode = menu.addAction("切换为手动定位" if follow else "切换为跟随窗口")
        a_col = menu.addAction("展开" if self.collapsed else "收起")
        menu.addSeparator()
        a_quit = menu.addAction("退出")
        act = menu.exec(e.globalPos())
        if act == a_mode:
            if follow:
                self.cfg["mode"] = "manual"
                self.cfg["pos"] = [self.x(), self.y()]
            else:
                self.cfg["mode"] = "follow"
            save_cfg(self.cfg)
            self._reposition()
        elif act == a_col:
            self._toggle_collapsed()
        elif act == a_quit:
            QtWidgets.QApplication.quit()

    def _toggle_collapsed(self):
        self.collapsed = not self.collapsed
        self.cfg["collapsed"] = self.collapsed
        save_cfg(self.cfg)
        self._apply_size()
        if self.cfg.get("mode") == "follow":
            self._reposition()
        self.update()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    _w = TrafficLight()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
