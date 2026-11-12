<#
.SYNOPSIS
    Celestial Butler 统一安装器（契约 v1）。安装 / 修复 / 自检 / 卸载。
.DESCRIPTION
    默认安装到 %LOCALAPPDATA%\Celestial\Programs\Celestial-Butler。
    依赖：Python 3.12+（含 Tk）与 pip；缺失时优先 winget，失败再下载 python.org
    官方安装器以当前用户静默安装。安装器全程不要求管理员权限。
.EXAMPLE
    ./installer/Install.ps1 -CheckOnly
.EXAMPLE
    ./installer/Install.ps1 -Root "$env:TEMP\celestial-installer-test" -Force
.EXAMPLE
    ./installer/Install.ps1 -Uninstall
#>
[CmdletBinding()]
param(
    [string]$Root = '',
    [switch]$CheckOnly,
    [switch]$Uninstall,
    [switch]$Force,
    [switch]$PurgeState
)

$ErrorActionPreference = 'Stop'
$installerDir = Split-Path -Parent $PSCommandPath
$sourceRoot = Split-Path -Parent $installerDir
$modulePath = Join-Path $installerDir 'CelestialInstaller.psm1'
$manifestPath = Join-Path $installerDir 'install-manifest.json'

try {
    Import-Module $modulePath -Force
    $manifest = Read-CelestialManifest -Path $manifestPath
    $layout = Get-CelestialLayout -Manifest $manifest -Root $Root
    if ($Uninstall) {
        $code = Uninstall-Celestial -Manifest $manifest -Layout $layout -PurgeState:$PurgeState
    } elseif ($CheckOnly) {
        $code = Invoke-CelestialCheck -Manifest $manifest -Layout $layout -SourceRoot $sourceRoot
    } else {
        $code = Install-Celestial -Manifest $manifest -Layout $layout -SourceRoot $sourceRoot -Force:$Force
    }
    exit $code
} catch {
    Write-Host ('[FAILED] ' + $_.Exception.Message) -ForegroundColor Red
    exit 2
}
