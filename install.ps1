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

# 0) Validate an existing rule block BEFORE creating backups, copying files or rebuilding the index.
$agents = Join-Path $Target "AGENTS.md"
$begin = "<!-- cc-Harness:begin -->"
$end   = "<!-- cc-Harness:end -->"
$NeedAppend = $true
if (Test-Path $agents) {
    $existing = Get-Content $agents -Raw -Encoding UTF8
    $beginCount = ([regex]::Matches($existing, [regex]::Escape($begin))).Count
    $endCount = ([regex]::Matches($existing, [regex]::Escape($end))).Count
    if ($beginCount -eq 0 -and $endCount -eq 0) {
        $NeedAppend = $true
    } elseif ($beginCount -eq 1 -and $endCount -eq 1 -and $existing.IndexOf($begin) -lt $existing.IndexOf($end)) {
        $NeedAppend = $false
    } else {
        Write-Host "[规则] 标记块残缺或重复（begin=$beginCount end=$endCount），已停止且未改动目标目录。" -ForegroundColor Red
        exit 1
    }
}

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

# 2.9) 生成技能索引（触发词表）
Push-Location $Target
try { python tools\skills_index.py 2>$null | Out-Null } catch {}
Pop-Location

# 3) 追加 AGENTS.md 规则块（带标记，可重复执行；有效性已在步骤 0 校验）
$block = @'
<!-- cc-Harness:begin -->
## Workspace workflow (cc-Harness)

1. Verify changes and record a task checkpoint before reporting completion.
2. Use the tool gateway for registered commands: `python tools/gateway.py run <tool> --json '{...}'`.
3. Run `python tools/check_install.py` in the installed workspace, and `python tools/verify_all.py` for the self-check (it uses throwaway state).
4. Keep application forms on the current page. Verify saved changes through the write response.
5. Stop and report the issue after two consecutive failures.
6. Search local history with `python tools/ctx_search.py search "<keyword>"`.
7. Read `skills/INDEX.md` at startup. Load the matching skill with `python tools/gateway.py skill <name>` before acting.

Installed by cc-Harness: __CC_INSTALL_STAMP__
<!-- cc-Harness:end -->
'@
$block = $block.Replace('__CC_INSTALL_STAMP__', $Stamp)
if ($NeedAppend) {
    if (Test-Path $agents) {
        Add-Content -Path $agents -Value "`n$block" -Encoding UTF8
        Write-Host "[规则] 已追加到 AGENTS.md"
    } else {
        Set-Content -Path $agents -Value $block -Encoding UTF8
        Write-Host "[规则] 已创建 AGENTS.md"
    }
} else {
    Write-Host "[规则] 已存在完整标记块，跳过（重复安装不会重复写入）"
}

Write-Host ""
Write-Host "== 完成 ==" -ForegroundColor Green
Write-Host "下一步："
Write-Host "  1) python tools/gateway.py list"
Write-Host "  2) python tools/check_install.py   # 安装完整性（规则块/工具/技能索引）"
Write-Host "  3) python tools/verify_all.py      # 自检（使用临时状态，不改动你的断点/索引/台账）"
Write-Host "  4) 把 tools/ 加进你的 PATH 或直接用 python 跑"
