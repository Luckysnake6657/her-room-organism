# -*- coding: utf-8 -*-
from organism.native import Native

n = Native("evidence/p3/cmw_native", "evidence/p3/cmw_import", tick=False)
batches = [
    ["还在搞", "应该快了", "就这四句吗…"],
    ["没事", "现在的活就是陪你聊聊天", "[表情包]"],
]
lines = []
for b in batches:
    out = n.respond(b)
    lines.append("- 他：%s\\n- 草稿：%s" % (" / ".join(b), out["text"] if out else "（没回）"))
open("evidence/p3/batch_test.md", "w", encoding="utf-8").write("\\n\\n".join(lines))
n.close()
print("done")
