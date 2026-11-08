#!/usr/bin/env bash
# 安装 cc-Harness 到当前 DSH 工作区（macOS / Linux）
# 用法: bash install.sh [目标工作区路径]
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-${DSH_WORKSPACE:-$(pwd)}}"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$TARGET/out/backup"

[ -d "$TARGET" ] || { echo "目标工作区不存在: $TARGET"; exit 1; }
mkdir -p "$BACKUP"

echo "== cc-Harness 安装 =="
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

# 2.5) 部署人味模板（不覆盖已有）
mkdir -p "$TARGET/out"
[ -f "$REPO/persona.md" ] && [ ! -f "$TARGET/out/persona.md" ] && cp "$REPO/persona.md" "$TARGET/out/persona.md" && echo "[人味] 已部署 out/persona.md"
[ -f "$REPO/user_profile.example.json" ] && [ ! -f "$TARGET/out/user_profile.json" ] && cp "$REPO/user_profile.example.json" "$TARGET/out/user_profile.json" && echo "[人味] 已部署 out/user_profile.json"

# 2.9) 生成技能索引
( cd "$TARGET" && python tools/skills_index.py >/dev/null 2>&1 || true )

# 3) 追加 AGENTS.md 规则块
AGENTS="$TARGET/AGENTS.md"
BEGIN="<!-- cc-Harness:begin -->"
END="<!-- cc-Harness:end -->"
BLOCK="$(cat <<'CC_HARNESS_RULES'
<!-- cc-Harness:begin -->
## Workspace workflow (cc-Harness)

1. Verify changes and record a task checkpoint before reporting completion.
2. Use the tool gateway for registered commands: `python tools/gateway.py run <tool> --json '{...}'`.
3. Run `python tools/verify_all.py` in a disposable workspace before reporting that the tools are ready.
4. Keep application forms on the current page. Verify saved changes through the write response.
5. Stop and report the issue after two consecutive failures.
6. Search local history with `python tools/ctx_search.py search "<keyword>"`.
7. Read `skills/INDEX.md` at startup. Load the matching skill with `python tools/gateway.py skill <name>` before acting.

Installed by cc-Harness: __CC_INSTALL_STAMP__
<!-- cc-Harness:end -->
CC_HARNESS_RULES
)"
BLOCK="${BLOCK/__CC_INSTALL_STAMP__/$STAMP}"

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
