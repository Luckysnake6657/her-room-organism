# -*- coding: utf-8 -*-
"""她的世界：键鼠在场、声音、天气。只取信号，不存内容。"""
import ctypes
import datetime as dt
import json
import time
import urllib.request


def idle_seconds() -> float:
    class LII(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    l = LII()
    l.cbSize = ctypes.sizeof(l)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(l))
    return (ctypes.windll.kernel32.GetTickCount() - l.dwTime) / 1000.0


def classify_idle(sec: float) -> str:
    if sec < 120:
        return "他在电脑前"
    if sec > 600:
        return "他离开了一会儿"
    return ""


def classify_rms(rms: float) -> str:
    if rms > 0.02:
        return "有声音"
    return ""


def mic_rms(seconds: float = 0.2) -> float:
    try:
        import numpy as np
        import sounddevice as sd
        with sd.InputStream(channels=1, samplerate=16000, blocksize=1600) as s:
            n = int(16000 * seconds)
            d, _ = s.read(n)
        return float(np.sqrt((d ** 2).mean()))
    except Exception:
        return 0.0


WEATHER = {0: "晴", 1: "晴间多云", 2: "多云", 3: "阴", 45: "雾", 48: "雾",
           51: "小雨", 53: "小雨", 55: "小雨", 61: "雨", 63: "雨", 65: "大雨",
           71: "雪", 73: "雪", 75: "大雪", 80: "阵雨", 81: "阵雨", 82: "强阵雨",
           95: "雷雨", 96: "雷雨", 99: "雷雨"}


def code_to_text(code: int) -> str:
    return WEATHER.get(int(code), "天气不明")


_cache = dict(t=0.0, text="")


def weather(lat=39.9, lon=116.4, ttl=1800) -> str:
    if time.time() - _cache["t"] < ttl and _cache["text"]:
        return _cache["text"]
    try:
        url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
               "&current=temperature_2m,weather_code" % (lat, lon))
        with urllib.request.urlopen(url, timeout=6) as r:
            d = json.load(r)["current"]
        text = "外面 %d℃ %s" % (round(d["temperature_2m"]), code_to_text(d["weather_code"]))
        _cache.update(t=time.time(), text=text)
        return text
    except Exception:
        return _cache.get("text", "")


def signals(with_sound=True) -> list:
    out = []
    p = classify_idle(idle_seconds())
    if p:
        out.append(p)
    if with_sound:
        s = classify_rms(mic_rms())
        if s:
            out.append(s)
    w = weather()
    if w:
        out.append(w)
    return out
