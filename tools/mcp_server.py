# -*- coding: utf-8 -*-
"""最小 MCP（Model Context Protocol）服务端：把 registry.json 暴露为标准 MCP 工具。

协议：JSON-RPC 2.0 over stdio（MCP 规范核心子集）
  - initialize           → 返回 serverInfo 与 capabilities
  - tools/list           → 列出全部工具（name/description/inputSchema）
  - tools/call           → 调用工具（复用 gateway 执行逻辑）

用法：
  python tools/mcp_server.py            # 作为 MCP server 运行（stdio）
  python tools/mcp_server.py --selftest # 自测：模拟 initialize/tools/list/tools/call 一次
"""
import sys, io, os, json, subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, "tools", "registry.json")
PY = sys.executable


def load_tools():
    return json.load(open(REG, encoding="utf-8"))["tools"]


def schema_of(spec):
    props = {}
    for a in spec.get("args") or []:
        props[a] = {"type": "string", "description": f"参数 {a}"}
    return {"type": "object", "properties": props, "required": []}


def handle(msg):
    mid = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}
    tools = load_tools()

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    if method == "initialize":
        return ok({
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "dsh-local-mcp", "version": "1.0.0"},
        })
    if method in ("notifications/initialized", "initialized"):
        return None
    if method == "tools/list":
        return ok({"tools": [
            {"name": n, "description": s.get("desc", ""), "inputSchema": schema_of(s)}
            for n, s in tools.items()
        ]})
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name not in tools:
            return err(-32602, f"未知工具: {name}")
        # 复用 gateway：拼 argv
        argv = [PY, os.path.join(ROOT, "tools", "gateway.py"), "run", name, "--json", json.dumps(args, ensure_ascii=False)]
        try:
            r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300, cwd=ROOT)
            out = (r.stdout or "").strip()
            return ok({"content": [{"type": "text", "text": out[-4000:]}], "isError": r.returncode != 0})
        except Exception as e:
            return ok({"content": [{"type": "text", "text": f"调用异常: {e}"}], "isError": True})
    return err(-32601, f"未知方法: {method}")


def serve():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}), flush=True)
            continue
        resp = handle(msg)
        if resp is not None:
            print(json.dumps(resp, ensure_ascii=False), flush=True)


def selftest():
    results = []
    tools = load_tools()
    r1 = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    results.append(("initialize", r1["result"]["serverInfo"]["name"] == "dsh-local-mcp"))
    r2 = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    n = len(r2["result"]["tools"])
    results.append((f"tools/list（{n} 个工具）", n == len(tools) and n >= 8))
    r3 = handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                 "params": {"name": "checkpoint.get", "arguments": {}}})
    txt = r3["result"]["content"][0]["text"]
    results.append(("tools/call checkpoint.get", bool(txt) and not r3["result"]["isError"]))
    r4 = handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "no.such", "arguments": {}}})
    results.append(("未知工具返回错误", "error" in r4))
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    passed = sum(1 for _, ok in results if ok)
    print(f"MCP selftest: {passed}/{len(results)} " + ("ALL PASS" if passed == len(results) else "FAIL"))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    serve()
