# -*- coding: utf-8 -*-
"""断网时的对外话术。

原则（2026-10-28 定）：
- 只报状态，不解释机制、不道歉、不升华；
- 用口语词（"凑合"），不用对偶/排比；
- 她本人说一句，界面上挂一个小标签；
- 恢复时只说恢复，不复述刚才多惨。

她的话是"能力受限"，不是"状态不好"——所以不提累、病、难受。
"""
NOTICE = "网断了，我词不够用，凑合聊吧"
RECOVERED = "网好了。"
LABEL = "没网，话少"


class Notice:
    """只在"在线→断网"那一次说，恢复时再说一次；不重复刷屏。"""

    def __init__(self):
        self.offline = False
        self._said = False

    def fallback(self):
        if self.offline:
            return None
        self.offline = True
        if self._said:
            return None
        self._said = True
        return NOTICE

    def recover(self):
        if not self.offline:
            return None
        self.offline = False
        return RECOVERED

    def label(self):
        return LABEL if self.offline else None
