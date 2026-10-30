# -*- coding: utf-8 -*-
"""答案类型门控：问名字/日期/金额/地点/数量时，候选要有对应证据。"""
import re

NAME_Q = re.compile(r"叫什么|名字|姓名|昵称")
DATE_Q = re.compile(r"哪天|什么时候|几号|生日|日期")
MONEY_Q = re.compile(r"多少钱|工资|月薪|收入")
PLACE_Q = re.compile(r"住哪|哪儿|哪里|在哪")
NUM_Q = re.compile(r"多少|几[个次天场]")

DATE_A = re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*日|\d{4}-\d{2}-\d{2}|"
                    r"周[一二三四五六日]|今天|明天|昨天|生日|上午|下午|晚上")
MONEY_A = re.compile(r"\d+\s*(元|块|万|k|K|千)|工资|月薪|收入|提成")
NAME_A = re.compile(r"叫|「|“|\"")
PLACE_A = re.compile(r"在|住|地方|城市|小区|公司|医院|学校|宿舍|家")
NUM_A = re.compile(r"\d|零|一|二|三|四|五|六|七|八|九|十|百|千|万|两")


def gate(query: str, text: str) -> bool:
    """True = 候选像答案；False = 只有相关，不应当断言。"""
    t = str(text or "")
    if NAME_Q.search(query):
        return bool(NAME_A.search(t))
    if DATE_Q.search(query):
        return bool(DATE_A.search(t))
    if MONEY_Q.search(query):
        return bool(MONEY_A.search(t))
    if PLACE_Q.search(query):
        return bool(PLACE_A.search(t))
    if NUM_Q.search(query):
        return bool(NUM_A.search(t))
    return True
