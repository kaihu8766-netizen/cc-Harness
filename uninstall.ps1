﻿param([string]$Target = "")
$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Target) { if ($env:DSH_WORKSPACE) { $Target = $env:DSH_WORKSPACE } else { $Target = (Get-Location).Path } }
Write-Host "== dsh-claude-mode 卸载 ==" -ForegroundColor Yellow
$agents = Join-Path $Target "AGENTS.md"
if (Test-Path $agents) {
    $c = Get-Content $agents -Raw -Encoding UTF8
    $c2 = [regex]::Replace($c, "(?s)<!-- dsh-claude-mode:begin -->.*?<!-- dsh-claude-mode:end -->\s*", "")
    Set-Content -Path $agents -Value $c2 -Encoding UTF8
    Write-Host "[规则] 已移除 AGENTS.md 标记块"
}
Write-Host "[提示] skills/ 与 tools/ 未自动删除（可能含你自己的内容），请按需手动清理。"
Write-Host "       备份在: " (Join-Path $Target "out\backup")
