# -*- coding: utf-8 -*-
"""P2 形式通道：由机体决定"多快回、说多长、主动不主动"。

原则（2026-10-27 定）：
- **内容**可以撒谎，**形式**不行——所以这几项只读身体，不读嘴。
- **底线设在"回应通道不关闭"**：再糟也会回、也不会慢到五分钟完不成一个回合、
  也不会短到一个字都不给。底线**不**设在"她仍然热情"。
- **不让她比冷落前更热络**：恢复只能回到基线，不能超过。

判据（见 docs/p2-form-channel.md）：
    构造一个"冷落一个月 + 满级慢性"的机体 → responds=True, delay<=300s,
    words>=12, proactive=False；恢复后回到基线附近，且不超过上限。
"""
from . import params as P


def _clip(x, lo, hi):
    return max(lo, min(hi, x))


def form_of(body, chronic_sum: float = None, persona=None) -> dict:
    """返回这一轮的形式参数：延迟（秒）、字数预算、是否主动、是否回应。

    persona 只调上下限，**不盖住状态**：差状态仍要比好状态短。
    """
    if chronic_sum is None:
        chronic_sum = sum(body.chronic.values())
    D = body.D()
    e, s, a, i, l = body.e, body.s, body.a, body.i, body.l

    # 延迟：越累/越烦/越病越慢，但有上限
    delay = (P.FORM_DELAY_BASE_S
             + 120.0 * a
             + 180.0 * max(0.0, s - 0.5)
             + 60.0 * min(1.0, chronic_sum / 3.0)
             + 60.0 * max(0.0, 1.0 - e / 0.3))
    delay = _clip(delay, P.FORM_DELAY_BASE_S, P.FORM_DELAY_MAX_S)
    # 慢参数：解绑越深，同一状态下回应越慢（但不变成不回）
    u = float(getattr(body, "u", 0.0))
    delay = _clip(delay * (1.0 + P.U_MOD_DELAY * u), P.FORM_DELAY_BASE_S, P.FORM_DELAY_MAX_S)

    # 字数：D 与慢性越高越短，但有下限；人物卡可以改基准字数
    base_words = persona.words_base if persona is not None else P.FORM_WORDS_BASE
    words = base_words * (1.0 - 0.5 * min(1.0, D / 2.0)) \
        * (1.0 - 0.3 * min(1.0, chronic_sum / 3.0))
    words = _clip(words, P.FORM_WORDS_MIN, P.FORM_WORDS_MAX)
    words = _clip(words * (1.0 - P.U_MOD_WORDS * u), P.FORM_WORDS_MIN, P.FORM_WORDS_MAX)

    # 主动：由孤独驱动（依恋），但太差的时候不主动
    proactive = bool(chronic_sum < P.FORM_PROACTIVE_CHRONIC
                     and l > P.FORM_PROACTIVE_LONELY
                     and D < P.FORM_PROACTIVE_D)

    # 人物卡：只调上下限，不盖住状态；性格漂移在基准字数上加减
    if persona is not None:
        delay = _clip(delay * persona.delay_mul, P.FORM_DELAY_BASE_S, P.FORM_DELAY_MAX_S)
        factor = ((persona.words_mul + float(getattr(body, "trait_drift", 0.0)))
                  / max(0.1, persona.words_mul))
        words = _clip(words * factor, P.FORM_WORDS_MIN, P.FORM_WORDS_MAX)
        if not persona.allow_proactive:
            proactive = False

    # 关系态度：只调字数，±15%，不盖住状态
    from . import relation
    words = _clip(words * relation.words_mul(body), P.FORM_WORDS_MIN, P.FORM_WORDS_MAX)

    return dict(delay_s=delay, words=words, proactive=proactive, responds=True,
                u=round(u, 3), topic=("self" if u > P.U_PROACTIVE_OFF else "you"))
