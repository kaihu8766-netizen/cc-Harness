#!/usr/bin/env bash
# 安装 cc-Harness 到当前 DSH 工作区（macOS / Linux）
# 用法: bash install.sh [目标工作区路径]
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-${DSH_WORKSPACE:-$(pwd)}}"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$TARGET/out/backup"

[ -d "$TARGET" ] || { echo "目标工作区不存在: $TARGET"; exit 1; }

# 0) Validate an existing rule block BEFORE creating backups, copying files or rebuilding the index.
AGENTS="$TARGET/AGENTS.md"
BEGIN="<!-- cc-Harness:begin -->"
END="<!-- cc-Harness:end -->"
NEED_APPEND=1
if [ -f "$AGENTS" ]; then
  begin_count=$(grep -cF "$BEGIN" "$AGENTS" || true)
  end_count=$(grep -cF "$END" "$AGENTS" || true)
  begin_line=$(grep -nF "$BEGIN" "$AGENTS" | head -1 | cut -d: -f1 || true)
  end_line=$(grep -nF "$END" "$AGENTS" | head -1 | cut -d: -f1 || true)
  if [ "$begin_count" = "0" ] && [ "$end_count" = "0" ]; then
    NEED_APPEND=1
  elif [ "$begin_count" = "1" ] && [ "$end_count" = "1" ] && [ -n "$begin_line" ] && [ -n "$end_line" ] && [ "$begin_line" -lt "$end_line" ]; then
    NEED_APPEND=0
  else
    echo "[规则] 标记块残缺或重复（begin=$begin_count end=$end_count），已停止且未改动目标目录。" >&2
    exit 1
  fi
fi

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

# 3) 追加 AGENTS.md 规则块（有效性已在步骤 0 校验）
if [ "$NEED_APPEND" = "1" ]; then
  if [ -f "$AGENTS" ]; then
    printf '\n%s\n' "$BLOCK" >> "$AGENTS"; echo "[规则] 已追加到 AGENTS.md"
  else
    printf '%s\n' "$BLOCK" > "$AGENTS"; echo "[规则] 已创建 AGENTS.md"
  fi
else
  echo "[规则] 已存在完整标记块，跳过（重复安装不会重复写入）"
fi

echo ""
echo "== 完成 =="
echo "下一步："
echo "  1) python tools/gateway.py list"
echo "  2) python tools/check_install.py   # 安装完整性（规则块/工具/技能索引）"
echo "  3) python tools/verify_all.py      # 自检（使用临时状态，不改动你的断点/索引/台账）"
