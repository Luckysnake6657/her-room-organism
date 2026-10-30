# -*- coding: utf-8 -*-
"""内感受推断 + 二阶态度（第 1、2 层）。

状态 + 事件评价 → 效价/唤醒/第一人称词/置信；不编原因。
"""
import re

LABELS = ("平静", "还行", "有点累", "有点困", "有点烦", "有点闷",
          "有点孤单", "有点慌", "松下来了", "挺好的")

CAUSE = re.compile(r"因为|由于|都是你|你害|怪你")


def _clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def appraisal(text="", presence=""):
    """粗评价：这句话/这个场景对她是需要还是压力。"""
    t = str(text or "")
    need = 0.0
    if any(k in t for k in ("累", "难受", "烦", "不想", "没意思")):
        need += 0.3
    if any(k in t for k in ("陪我", "聊聊", "在吗", "想你")):
        need += 0.4
    if presence == "他有一阵没来了":
        need += 0.3
    return _clip(need)


def infer(body, text="", presence="", memories=(), valence_shift=0.0,
          extra_components=()):
    e = float(getattr(body, "e", 0.6))
    s = float(getattr(body, "s", 0.0))
    a = float(getattr(body, "a", 0.0))
    i = float(getattr(body, "i", 0.0))
    l = float(getattr(body, "l", 0.0))

    # 效价：能量/孤独/应激/免疫共同决定（越接近 1 越好）
    valence = _clip(0.35 + 0.35 * e - 0.30 * l - 0.25 * a - 0.20 * i - 0.10 * s
                    + float(valence_shift or 0.0))
    # 唤醒：应激 + 睡眠债
    arousal = _clip(0.25 * a + 0.15 * s + 0.10 * e)
    need = appraisal(text, presence)

    if valence < 0.30 and arousal > 0.55:
        label = "有点慌"
    elif valence < 0.30 and l > 0.55:
        label = "有点孤单"
    elif valence < 0.35 and a > 0.55:
        label = "有点烦"
    elif valence < 0.35 and e < 0.35:
        label = "有点累"
    elif s > 0.60:
        label = "有点困"
    elif valence < 0.45:
        label = "有点闷"
    elif valence > 0.70:
        label = "挺好的"
    elif valence > 0.60:
        label = "还行"
    else:
        label = "平静"

    # 置信：信号一致度；弱信号要模糊
    flags = [e < 0.35, l > 0.55, a > 0.55, s > 0.6, i > 0.5]
    strength = sum(1 for f in flags if f) / 5.0
    confidence = round(_clip(0.25 + 0.6 * strength), 2)

    # 二阶态度：想要 / 不想要
    if l > 0.6 and need > 0.2:
        want = "想有人说话"
    elif a > 0.6:
        want = "想安静一会儿"
    elif need > 0.5:
        want = "想被看见"
    elif valence > 0.65:
        want = "想继续这样"
    else:
        want = "不想被打扰"

    # 复合感受：同时存在的都列出来（最多两个）
    comps = []
    if e < 0.35:
        comps.append("累")
    if s > 0.55:
        comps.append("困")
    if a > 0.55:
        comps.append("烦")
    if l > 0.60:
        comps.append("孤单")
    if i > 0.50:
        comps.append("不舒服")
    for c in (extra_components or ()):
        if c and c not in comps:
            comps.append(str(c))
    comps = comps[:2]

    phrase = _phrase(label, confidence, want, comps)
    return dict(valence=round(valence, 3), arousal=round(arousal, 3),
                label=label, confidence=confidence, components=comps,
                want=want, phrase=phrase,
                no_cause=not bool(CAUSE.search(phrase)))


NEUTRAL = {"平静": "", "还行": "还行吧", "挺好的": "挺好的",
           "松下来了": "松下来了"}


def _phrase(label, conf, want, comps=()):
    # 中性/正面不从"说不清"起头；那是负向模糊的句式
    if label in NEUTRAL:
        return NEUTRAL[label]
    if len(comps) >= 2:
        body = "又%s又%s" % (comps[0], comps[1])
    elif len(comps) == 1:
        body = "有点" + comps[0]
    else:
        body = label
    if conf < 0.5:
        head = "说不太上来，"
    elif conf < 0.7:
        head = "有点说不好，"
    else:
        head = ""
    return "%s%s" % (head, body)
