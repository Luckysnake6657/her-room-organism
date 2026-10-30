# -*- coding: utf-8 -*-
"""给已确认的用户事实补同义关键词（检索会用 keywords）。"""
import json

from . import notebook

VARIANTS = {
    "手机": "手机 电话 机型 设备 华为 P70",
    "AIGC": "搜过 技术 AI 大模型 代理 学习 方向 了解 关注",
    "Stable Diffusion": "AI 画图 绘图 SD",
    "小说": "文件 发过 文档 书",
    "小5金哲": "小5 金哲 朋友 一起 拉",
    "考研": "考研 找工作 选择 纠结 以后 前途 毕业",
    "S25": "游戏 段位 赛季 场次 打",
    "295": "游戏 场次 总场 历史",
    "1790": "游戏 分数 最高分 段位",
    "Rating": "游戏 评分 rating",
    "KD": "游戏 kd 击杀",
    "胜率": "游戏 胜率 赢 比例 水平 厉害",
    "通关": "游戏 水平 厉害 自称",
    "语气": "说话 语气 口头禅 句子短 风格 特点",
    "薪资": "工资 薪资 收入 多少钱 待遇",
    "提成": "工资 收入 提成 toB",
    "硬扛": "前半年 工作 状态 累",
    "训练量": "训练 量 健身 运动",
    "群聊": "群 限制 规矩 看法 观点",
    "汇报": "告诉 汇报 说一声",
    "真有事": "找你 联系 什么时候 告诉",
}


def main():
    nb = notebook.Notebook("evidence/p3/cmw_native/notebook.json")
    n = 0
    for e in nb.entries:
        if e.get("source") != "user_confirmed":
            continue
        kw = e.get("keywords", "")
        add = []
        for k, v in VARIANTS.items():
            if k.lower() in e["text"].lower() and v not in kw:
                add.append(v)
        if add:
            e["keywords"] = (kw + " " + " ".join(add)).strip()
            n += 1
    nb.save()
    print("enriched", n)


if __name__ == "__main__":
    main()
