# 安装 cc-Harness 到当前 DSH 工作区
# 用法: powershell -ExecutionPolicy Bypass -File install.ps1 [-Target <工作区路径>]
param(
    [string]$Target = ""
)
$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not $Target) {
    # 优先用 DSH_WORKSPACE 环境变量，否则用当前目录
    if ($env:DSH_WORKSPACE) { $Target = $env:DSH_WORKSPACE } else { $Target = (Get-Location).Path }
}
if (-not (Test-Path $Target)) { throw "目标工作区不存在: $Target" }

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path $Target "out\backup"
New-Item -ItemType Directory -Force -Path $Backup | Out-Null

Write-Host "== cc-Harness 安装 ==" -ForegroundColor Cyan
Write-Host "仓库:     $Repo"
Write-Host "目标:     $Target"
Write-Host "备份目录: $Backup"
Write-Host ""

# 1) 备份现有 skills / tools / AGENTS.md
foreach ($item in @("skills", "tools", "AGENTS.md")) {
    $p = Join-Path $Target $item
    if (Test-Path $p) {
        $dest = Join-Path $Backup "preinstall_${Stamp}_$($item -replace '[\\/]', '_')"
        Copy-Item $p $dest -Recurse -Force
        Write-Host "[备份] $item -> $dest"
    }
}

# 2) 复制 skills / tools（不覆盖同名文件，避免踩别人成果）
foreach ($dir in @("skills", "tools")) {
    $src = Join-Path $Repo $dir
    if (-not (Test-Path $src)) { continue }
    $dst = Join-Path $Target $dir
    New-Item -ItemType Directory -Force -Path $dst | Out-Null
    $copied = 0; $skipped = 0
    Get-ChildItem $src -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($src.Length).TrimStart('\', '/')
        $out = Join-Path $dst $rel
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $out) | Out-Null
        if (Test-Path $out) { $skipped++ } else { Copy-Item $_.FullName $out -Force; $copied++ }
    }
    Write-Host "[安装] $dir : 新增 $copied 个，跳过已存在 $skipped 个"
}

# 2.5) 部署人味模板（已存在则跳过，不覆盖用户的个性化版本）
$outDir = Join-Path $Target "out"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
foreach ($pair in @(@("persona.md", "out\persona.md"), @("user_profile.example.json", "out\user_profile.json"))) {
    $srcF = Join-Path $Repo $pair[0]
    $dstF = Join-Path $Target $pair[1]
    if ((Test-Path $srcF) -and -not (Test-Path $dstF)) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dstF) | Out-Null
        Copy-Item $srcF $dstF -Force
        Write-Host "[人味] 已部署 $($pair[1])（请按自己习惯改写）"
    }
}

# 3) 追加 AGENTS.md 规则块（带标记，可重复执行）
$agents = Join-Path $Target "AGENTS.md"
$begin = "<!-- cc-Harness:begin -->"
$end   = "<!-- cc-Harness:end -->"
$block = @"
$begin
## 工程化约定（cc-Harness 注入）

1. **未落盘 = 未做**：改完必须验证并写断点（`python tools/checkpoint.py set "..."`），否则视为未执行。
2. **工具优先走网关**：`python tools/gateway.py run <tool> --json '{...}'`；新能力注册到 `tools/registry.json` 即可生效。
3. **自检自查**：宣称"环境正常"前必须 `python tools/verify_all.py` 全绿。
4. **单页死守**：填表/提交页禁止跳站与刷新；保存只认写接口 2xx（"看起来保存了"不算）。
5. **失败两次即停**：连续失败 ≥2 次，停下来报告，不猜第三次。
6. **检索代替塞满**：历史内容用 `python tools/ctx_search.py search "<关键词>"` 取片段，不整段灌上下文。

安装元信息：cc-Harness / $Stamp
$end
"@
if (Test-Path $agents) {
    $content = Get-Content $agents -Raw -Encoding UTF8
    if ($content -match [regex]::Escape($begin)) {
        Write-Host "[规则] 已存在标记块，跳过（如需更新请先手动删除旧块）"
    } else {
        Add-Content -Path $agents -Value "`n$block" -Encoding UTF8
        Write-Host "[规则] 已追加到 AGENTS.md"
    }
} else {
    Set-Content -Path $agents -Value $block -Encoding UTF8
    Write-Host "[规则] 已创建 AGENTS.md"
}

Write-Host ""
Write-Host "== 完成 ==" -ForegroundColor Green
Write-Host "下一步："
Write-Host "  1) python tools/gateway.py list"
Write-Host "  2) python tools/verify_all.py"
Write-Host "  3) 把 tools/ 加进你的 PATH 或直接用 python 跑"
