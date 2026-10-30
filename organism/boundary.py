# -*- coding: utf-8 -*-
"""边界闸：第一次见面（stranger）时，不接受亲密称呼与越界要求。

人物卡的"不太顺着人"是提示词，模型可以不听；这条是代码。
只在 stranger 模式生效；已经认识之后不拦（那时候亲昵是双方长出来的）。
"""
INTIMATE_REQUESTS = ("亲爱的", "宝贝", "老婆", "老公", "在一起", "亲一个", "抱抱")
REFUSAL_MARKS = ("不", "别", "还不熟", "太快", "不合适", "刚认识")
DEFAULT_REFUSAL = "我们还不熟，这样叫不太合适。"


def check(text: str, user_text: str, mode: str = "acquaintance") -> tuple:
    if mode != "stranger":
        return text, False
    if not any(w in (user_text or "") for w in INTIMATE_REQUESTS):
        return text, False
    if any(w in text for w in REFUSAL_MARKS):
        return text, False
    return DEFAULT_REFUSAL, True
