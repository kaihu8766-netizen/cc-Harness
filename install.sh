#!/usr/bin/env bash
# 安装 dsh-claude-mode 到当前 DSH 工作区（macOS / Linux）
# 用法: bash install.sh [目标工作区路径]
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-${DSH_WORKSPACE:-$(pwd)}}"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$TARGET/out/backup"

[ -d "$TARGET" ] || { echo "目标工作区不存在: $TARGET"; exit 1; }
mkdir -p "$BACKUP"

echo "== dsh-claude-mode 安装 =="
echo "仓库:     $REPO"
echo "目标:     $TARGET"
echo "备份目录: $BACKUP"

# 1) 备份
for item in skills tools AGENTS.md; do
  [ -e "$TARGET/$item" ] && cp -r "$TARGET/$item" "$BACKUP/preinstall_${STAMP}_${item//\//_}" && echo "[备份] $item"
done

# 2) 复制 skills / tools（不覆盖同名文件）
for dir in skills tools; do
  [ -d "$REPO/$dir" ] || continue
  copied=0; skipped=0
  while IFS= read -r -d '' f; do
    rel="${f#"$REPO/"}"
    out="$TARGET/$rel"
    mkdir -p "$(dirname "$out")"
    if [ -e "$out" ]; then skipped=$((skipped+1)); else cp "$f" "$out"; copied=$((copied+1)); fi
  done < <(find "$REPO/$dir" -type f -print0)
  echo "[安装] $dir : 新增 $copied，跳过已存在 $skipped"
done

# 3) 追加 AGENTS.md 规则块
AGENTS="$TARGET/AGENTS.md"
BEGIN="<!-- dsh-claude-mode:begin -->"
END="<!-- dsh-claude-mode:end -->"
BLOCK="$BEGIN
## 工程化约定（dsh-claude-mode 注入）

1. **未落盘 = 未做**：改完必须验证并写断点，否则视为未执行。
2. **工具优先走网关**：\`python tools/gateway.py run <tool> --json '{...}'\`
3. **自检自查**：宣称环境正常前必须 \`python tools/verify_all.py\` 全绿。
4. **单页死守**：填表/提交页禁止跳站与刷新；保存只认写接口 2xx。
5. **失败两次即停**。
6. **检索代替塞满**：用 \`python tools/ctx_search.py search "<关键词>"\`。

安装元信息：dsh-claude-mode / $STAMP
$END"

if [ -f "$AGENTS" ]; then
  if grep -qF "$BEGIN" "$AGENTS"; then
    echo "[规则] 已存在标记块，跳过"
  else
    printf '\n%s\n' "$BLOCK" >> "$AGENTS"; echo "[规则] 已追加到 AGENTS.md"
  fi
else
  printf '%s\n' "$BLOCK" > "$AGENTS"; echo "[规则] 已创建 AGENTS.md"
fi

echo ""
echo "== 完成 =="
echo "下一步： python tools/gateway.py list && python tools/verify_all.py"
