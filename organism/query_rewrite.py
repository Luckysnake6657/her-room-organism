# -*- coding: utf-8 -*-
"""查询改写：去口语填充、抽时间/实体、同义扩展。规则，无 API。"""
import re

FILLERS = ("你还记得", "你记得", "还记得", "我说过", "我跟你说过", "那个", "上次",
           "之前", "是不是", "吗", "呢", "吧", "啊", "呀", "的话")
TIME = ("今天", "明天", "昨天", "上周", "这周", "下周", "周三", "周四", "周五",
        "周六", "周日", "周一", "周二", "复查", "生日")
SYN = {"复查": ("医院", "检查"), "茶": ("乌龙茶",), "猫": ("团子",),
       "医院": ("复查",), "体检": ("医院", "检查"), "工作": ("公司", "上班"),
       "纠结": ("考研", "工作", "选择"), "以后": ("考研", "工作"),
       "前途": ("考研", "工作"), "毕业": ("考研", "工作")}


def rewrite(text: str) -> dict:
    t = str(text or "").strip()
    clean = t
    for f in FILLERS:
        clean = clean.replace(f, "")
    clean = re.sub(r"[？?！!。，,、\s]+", " ", clean).strip()
    times = [w for w in TIME if w in t]
    expand = []
    for k, vs in SYN.items():
        if k in t:
            expand.extend(vs)
    parts = [clean] + times + expand
    q = " ".join(dict.fromkeys(p for p in parts if p))
    return dict(original=t, clean=clean, times=times, expand=expand, query=q or t)
