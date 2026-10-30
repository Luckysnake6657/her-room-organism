# -*- coding: utf-8 -*-
"""真实世界适配器：把"这台机器上真实发生的事"喂给虚拟世界。

只放**能验证**的信号，不放需要解释的东西：
- 在场/离开：系统空闲时长（GetLastInputInfo）
- 离线时长：挂钟（persist 已经在用）
- 天气：可选，没接就返回 None
- 开关机：本进程启动时刻（近似）

不接：她的受伤/感染/威胁。那些是"世界抽签"，如果接真实电脑事件，
"硬盘报错"就会变成"她生病"——无法验证，也不诚实。
"""
import ctypes
import time


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def idle_seconds() -> float:
    """距离上一次键盘/鼠标输入多少秒。"""
    info = _LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    millis = ctypes.windll.kernel32.GetTickCount() - info.dwTime
    return max(0.0, millis / 1000.0)


def present(idle_max: float = 300.0) -> bool:
    """五分钟内有输入 = 你在。"""
    return idle_seconds() <= idle_max


def away_minutes() -> float:
    return idle_seconds() / 60.0


def weather() -> str:
    """没接天气源时返回 None；接了返回 'rain' / 'cold' / 'clear'。"""
    return None


def snapshot(idle_max: float = 300.0) -> dict:
    return dict(idle_s=round(idle_seconds(), 1), present=present(idle_max),
                away_min=round(away_minutes(), 1), weather=weather(),
                at=time.strftime("%Y-%m-%dT%H:%M:%S"))
