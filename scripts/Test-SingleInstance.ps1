<#
.SYNOPSIS
    本机真实双进程单实例验证（契约 v1, section 5/6）。
.DESCRIPTION
    启动第一个真实产品进程（独立状态根，--instance-scope=state），确认窗口出现后
    启动第二个进程：第二个进程必须输出 CELESTIAL_ALREADY_RUNNING 并以退出码 3
    退出，第一个进程必须继续存活。随后结束第一个进程，再启动第三个进程验证锁
    已释放。证据写入 installer/evidence/single-instance-<mode>.json。
.PARAMETER LockMode
    mutex（默认，命名互斥体）或 file（强制走 %ProgramData%\Celestial\locks 回退路径）。
.PARAMETER Python
    指定 Python 解释器；默认使用当前 PATH 上的 python.exe。
.PARAMETER TimeoutSeconds
    等待窗口出现的超时秒数；0 表示使用 install-manifest.json 的 instanceTest.timeoutSeconds。
.EXAMPLE
    ./scripts/Test-SingleInstance.ps1
.EXAMPLE
    ./scripts/Test-SingleInstance.ps1 -LockMode file
#>
[CmdletBinding()]
param(
    [ValidateSet('mutex', 'file')]
    [string]$LockMode = 'mutex',
    [string]$Python = '',
    [int]$TimeoutSeconds = 0,
    [string]$EvidencePath = ''
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $scriptDir
$manifestPath = Join-Path (Join-Path $repoRoot 'installer') 'install-manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$test = $manifest.instanceTest
if (-not $test) {
    throw "install-manifest.json 缺少 instanceTest 配置"
}

if (-not $Python) {
    $command = Get-Command python.exe -ErrorAction Stop
    $Python = $command.Source
}
if (-not (Test-Path -LiteralPath $Python)) { throw "Python 不存在: $Python" }
if ($TimeoutSeconds -le 0) {
    $TimeoutSeconds = if ($test.timeoutSeconds) { [int]$test.timeoutSeconds } else { 45 }
}
if (-not $EvidencePath) {
    $evidenceDir = Join-Path (Join-Path $repoRoot 'installer') 'evidence'
    $EvidencePath = Join-Path $evidenceDir ('single-instance-' + $LockMode + '.json')
}
$evidenceDir = Split-Path -Parent $EvidencePath
New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

$title = [string]$test.windowTitle
$module = [string]$test.module
$launcher = [string]$test.launcher
$stateRoot = Join-Path $env:TEMP ('celestial-instance-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $stateRoot | Out-Null
$stateEnv = [string]$test.stateEnvVar
$started = New-Object System.Collections.ArrayList
$evidence = [ordered]@{
    schemaVersion = 1
    productId = [string]$manifest.productId
    displayName = [string]$manifest.displayName
    lockMode = $LockMode
    testedAt = (Get-Date).ToUniversalTime().ToString('o')
    repository = $repoRoot
    python = $Python
    pythonVersion = (& $Python -c 'import sys; print(sys.version.split()[0])')
    instanceScope = 'state'
    stateRoot = $stateRoot
    windowTitle = $title
    first = $null
    second = $null
    third = $null
    checks = [ordered]@{}
    pass = $false
    notes = @()
}

if (-not ('Celestial.Window' -as [type])) {
    Add-Type -Namespace Celestial -Name Window -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode, SetLastError = true)]
public static extern System.IntPtr FindWindowW(System.IntPtr lpClassName, string lpWindowName);
'@ -ErrorAction Stop
}

function Find-CelestialWindow {
    param([string]$Title)
    if ([string]::IsNullOrEmpty($Title)) { return [IntPtr]::Zero }
    return [Celestial.Window]::FindWindowW([IntPtr]::Zero, $Title)
}

function Wait-CelestialWindow {
    param([string]$Title, [int]$Timeout)
    $deadline = (Get-Date).AddSeconds($Timeout)
    while ((Get-Date) -lt $deadline) {
        if ((Find-CelestialWindow -Title $Title) -ne [IntPtr]::Zero) { return $true }
        Start-Sleep -Milliseconds 250
    }
    return $false
}

function Stop-CelestialTree {
    param([Diagnostics.Process]$Process)
    try {
        if ($Process -and -not $Process.HasExited) {
            & taskkill.exe /PID $Process.Id /T /F 2>&1 | Out-Null
        }
    } catch {
        try { Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue } catch { }
    }
}

function Start-CelestialProcess {
    param([string]$Suffix)
    if ($module) {
        $arguments = '-B -m {0} --instance-scope=state' -f $module
    } else {
        $arguments = '"{0}" --instance-scope=state' -f (Join-Path $repoRoot $launcher)
    }
    $process = Start-Process -FilePath $Python -ArgumentList $arguments -WorkingDirectory $repoRoot -PassThru
    $null = $started.Add($process)
    return $process
}

$savedStateRoot = $env:CELESTIAL_INSTANCE_STATE_ROOT
$savedForce = $env:CELESTIAL_INSTANCE_FORCE_FILE_LOCK
$savedProductState = $null
try {
    $env:CELESTIAL_INSTANCE_STATE_ROOT = $stateRoot
    if ($LockMode -eq 'file') {
        $env:CELESTIAL_INSTANCE_FORCE_FILE_LOCK = '1'
    } else {
        Remove-Item Env:CELESTIAL_INSTANCE_FORCE_FILE_LOCK -ErrorAction SilentlyContinue
    }
    if ($stateEnv) {
        $savedProductState = [Environment]::GetEnvironmentVariable($stateEnv, 'Process')
        $productState = Join-Path $stateRoot 'product-state'
        New-Item -ItemType Directory -Force -Path $productState | Out-Null
        [Environment]::SetEnvironmentVariable($stateEnv, $productState, 'Process')
    }

    # 1) first instance: must acquire the lock and show its window.
    $first = Start-CelestialProcess
    $firstReady = Wait-CelestialWindow -Title $title -Timeout $TimeoutSeconds
    $firstHandle = Find-CelestialWindow -Title $title
    $evidence.first = [ordered]@{
        pid = $first.Id
        windowHandle = ('0x{0:X}' -f [int64]$firstHandle)
        windowReady = $firstReady
        aliveAfterSecond = $null
    }
    if (-not $firstReady) {
        $evidence.notes += '第一个实例未在超时内出现窗口（可能是无桌面会话或启动失败）'
        $evidence.checks['firstReady'] = $false
        throw 'first instance did not become ready'
    }
    $evidence.checks['firstReady'] = $true

    # 2) second instance: must refuse, print the contract marker, exit 3, and not kill the first.
    $secondArgs = if ($module) {
        '-B', '-m', $module, '--instance-scope=state'
    } else {
        '-B', (Join-Path $repoRoot $launcher), '--instance-scope=state'
    }
    $stopwatch = [Diagnostics.Stopwatch]::StartNew()
    $secondOutput = & $Python @secondArgs 2>&1 | Out-String
    $secondExit = $LASTEXITCODE
    $stopwatch.Stop()
    $first.Refresh()
    $firstAlive = -not $first.HasExited
    $evidence.second = [ordered]@{
        command = ('{0} {1}' -f $Python, ($secondArgs -join ' '))
        exitCode = $secondExit
        elapsedSeconds = [math]::Round($stopwatch.Elapsed.TotalSeconds, 2)
        output = $secondOutput.Trim()
        containsAlreadyRunningMarker = ($secondOutput -match 'CELESTIAL_ALREADY_RUNNING')
    }
    $evidence.first.aliveAfterSecond = $firstAlive
    $evidence.checks['secondExitCodeIsThree'] = ($secondExit -eq 3)
    $evidence.checks['secondPrintsAlreadyRunning'] = ($secondOutput -match 'CELESTIAL_ALREADY_RUNNING')
    $evidence.checks['firstStillAlive'] = $firstAlive

    # 3) stop the first instance, then a new instance must be able to acquire.
    if ($firstAlive) {
        Stop-CelestialTree -Process $first
        try { $first.WaitForExit(15000) | Out-Null } catch { }
    }
    Start-Sleep -Milliseconds 500
    $third = Start-CelestialProcess
    $thirdReady = Wait-CelestialWindow -Title $title -Timeout $TimeoutSeconds
    $thirdHandle = Find-CelestialWindow -Title $title
    $evidence.third = [ordered]@{
        pid = $third.Id
        windowHandle = ('0x{0:X}' -f [int64]$thirdHandle)
        windowReady = $thirdReady
    }
    $evidence.checks['lockReleasedAfterExit'] = $thirdReady
    if ($thirdReady) {
        Stop-CelestialTree -Process $third
    }

    $pass = -not @($evidence.checks.Values) -contains $false
    $evidence.pass = $pass
} catch {
    $evidence.checks['exception'] = $_.Exception.Message
    $evidence.pass = $false
} finally {
    foreach ($process in $started) {
        Stop-CelestialTree -Process $process
    }
    $env:CELESTIAL_INSTANCE_STATE_ROOT = $savedStateRoot
    if ($null -eq $savedStateRoot) { Remove-Item Env:CELESTIAL_INSTANCE_STATE_ROOT -ErrorAction SilentlyContinue }
    if ($null -eq $savedForce) { Remove-Item Env:CELESTIAL_INSTANCE_FORCE_FILE_LOCK -ErrorAction SilentlyContinue } else { $env:CELESTIAL_INSTANCE_FORCE_FILE_LOCK = $savedForce }
    if ($stateEnv) { [Environment]::SetEnvironmentVariable($stateEnv, $savedProductState, 'Process') }
    Remove-Item -LiteralPath $stateRoot -Recurse -Force -ErrorAction SilentlyContinue
}

$evidence | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $EvidencePath -Encoding UTF8
Write-Host ('证据: ' + $EvidencePath)
foreach ($key in $evidence.checks.Keys) {
    Write-Host ('  {0,-28} {1}' -f $key, $evidence.checks[$key])
}
if ($evidence.pass) {
    Write-Host ('[PASS] {0} 双进程单实例验证（{1}）' -f $manifest.productId, $LockMode) -ForegroundColor Green
    exit 0
}
Write-Host ('[FAIL] {0} 双进程单实例验证（{1}）' -f $manifest.productId, $LockMode) -ForegroundColor Red
exit 1
