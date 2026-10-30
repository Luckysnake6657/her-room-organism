# -*- coding: utf-8 -*-
"""最小感知层：内感受 + 在场感。只输出信号，不编造。"""
import time


def interoception(body) -> list:
    out = []
    if float(body.e) < 0.35:
        out.append("有点累")
    if float(body.load) < 0.4:
        out.append("有点饿")
    if float(body.a) > 0.60:
        out.append("心里有点紧")
    if float(body.i) > 0.50:
        out.append("不太舒服")
    if float(body.s) > 0.50:
        out.append("没睡够")
    if float(body.l) > 0.60:
        out.append("想找人说话")
    return out[:2]


def presence(last_incoming_ts, now=None) -> str:
    if not last_incoming_ts:
        return ""
    ts = float(last_incoming_ts)
    if ts > 1e12:            # 毫秒时间戳
        ts /= 1000.0
    gap = (now or time.time()) - ts
    if gap < 300:
        return "他在"
    if gap > 6 * 3600:
        return "他有一阵没来了"
    return ""


def signals(body, last_incoming_ts=None, now=None) -> dict:
    return dict(intero=interoception(body),
                presence=presence(last_incoming_ts, now))
