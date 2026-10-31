# -*- coding: utf-8 -*-
"""代码理解（AST）：给定符号/文件，输出定义、调用者、上游调用树（补"代码工程理解"短板）。

用法：
  python tools/code_lens.py callers <符号名>          # 谁调用了它
  python tools/code_lens.py tree <函数名> [--depth 3]  # 上游调用树
  python tools/code_lens.py symbols --file tools/gateway.py
  python tools/code_lens.py index                      # 统计：文件数/函数数/类数
"""
import sys, io, os, ast, json, argparse, glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scan(paths):
    """返回 [{file, funcs:[{name,lineno,calls:[names]}]}]"""
    out = []
    for p in paths:
        try:
            src = open(p, encoding="utf-8", errors="replace").read()
            tree = ast.parse(src)
        except Exception:
            continue
        funcs = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                calls = []
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        f = sub.func
                        if isinstance(f, ast.Name):
                            calls.append(f.id)
                        elif isinstance(f, ast.Attribute):
                            calls.append(f.attr)
                funcs.append({"name": node.name, "lineno": node.lineno, "calls": sorted(set(calls))})
        out.append({"file": os.path.relpath(p, ROOT), "funcs": funcs})
    return out


def target_files(scope):
    if scope and scope != "all":
        return [scope]
    patterns = ["tools/*.py", "tools/*.mjs", "skills/**/*.md"]
    files = []
    for pat in patterns:
        files += glob.glob(os.path.join(ROOT, pat), recursive=True)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["callers", "tree", "symbols", "index"])
    ap.add_argument("name", nargs="?", default="")
    ap.add_argument("--file", default="")
    ap.add_argument("--depth", type=int, default=3)
    a = ap.parse_args()

    files = target_files(a.file)
    data = scan(files)

    if a.cmd == "index":
        nf = len(data)
        nfun = sum(len(d["funcs"]) for d in data)
        print(json.dumps({"files": nf, "functions": nfun}, ensure_ascii=False))
        return 0
    if a.cmd == "symbols":
        for d in data:
            for f in d["funcs"]:
                print(f'{d["file"]}:{f["lineno"]}  def {f["name"]}({len(f["calls"])} calls)')
        return 0
    if a.cmd == "callers":
        hits = [(d["file"], f) for d in data for f in d["funcs"] if a.name in f["calls"]]
        if not hits:
            print(f"无调用者: {a.name}")
            return 0
        for file, f in hits:
            print(f'{file}:{f["lineno"]}  {f["name"]} → 调用 {a.name}')
        print(f"共 {len(hits)} 处调用")
        return 0
    if a.cmd == "tree":
        # 上游调用树：谁调用 name，再谁调用它
        def find(name):
            return [f for d in data for f in d["funcs"] if f["name"] == name]
        def walk(name, depth, indent):
            if depth > a.depth:
                return
            callers = [(d["file"], f) for d in data for f in d["funcs"] if name in f["calls"]]
            for file, f in callers:
                print(f"{'  ' * indent}← {f['name']}  ({file}:{f['lineno']})")
                walk(f["name"], depth + 1, indent + 1)
        defs = find(a.name)
        if defs:
            for d in data:
                for f in d["funcs"]:
                    if f["name"] == a.name:
                        print(f"{a.name} 定义于 {d['file']}:{f['lineno']}  调用 {len(f['calls'])} 个函数")
        walk(a.name, 1, 0)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
