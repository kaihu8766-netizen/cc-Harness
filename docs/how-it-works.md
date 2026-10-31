# 工作原理

```
你的终端 / DSH
   │
   ├─ AGENTS.md 规则块（安装时注入）        ← 让模型守规矩
   ├─ tools/gateway.py + registry.json      ← 所有工具一个入口
   ├─ tools/mcp_server.py                   ← 把工具包装成 MCP
   ├─ tools/verify_all.py                   ← 自检，防止"假绿"
   ├─ tools/checkpoint.py                   ← 断点续命
   ├─ tools/ctx_search.py（SQLite FTS5）    ← 检索代替塞满上下文
   ├─ tools/fanout.py（线程池 + 写锁）      ← 并行不乱
   ├─ tools/watchdog.py                     ← 主动巡检
   └─ tools/code_lens.py（AST）             ← 代码结构理解
```

## 为什么这些设计
- **网关**：工具多了以后，模型记不住参数；统一 JSON + 校验 + 自愈重试，降低"调错工具"概率。
- **自检**：Agent 最爱说"已完成"，自检把这句话变成可验证的绿字。
- **断点**：上下文压缩是常态，100 字断点比重新读一万字便宜。
- **FTS5**：把长历史变成按需检索的片段，而不是每轮重发。
- **写锁**：并行最容易出的不是速度问题，是数据打架。
