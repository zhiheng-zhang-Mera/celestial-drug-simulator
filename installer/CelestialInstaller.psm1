# Celestial unified installer module (contract v1).
# Dependency checks/installation, payload copy + hash receipt, shortcuts, uninstall.
# This file is intentionally identical across Celestial Python products; all
# product identity lives in install-manifest.json.

$script:CelestialState = @{
    Manifest        = $null
    ManifestDirectory = $null
    Layout          = $null
    Dependencies    = New-Object System.Collections.ArrayList
    Optional        = New-Object System.Collections.ArrayList
    Shortcuts       = New-Object System.Collections.ArrayList
    Warnings        = New-Object System.Collections.ArrayList
    Result          = 'OK'
}

function Reset-CelestialSession {
    $script:CelestialState.Dependencies = New-Object System.Collections.ArrayList
    $script:CelestialState.Optional = New-Object System.Collections.ArrayList
    $script:CelestialState.Shortcuts = New-Object System.Collections.ArrayList
    $script:CelestialState.Warnings = New-Object System.Collections.ArrayList
    $script:CelestialState.Result = 'OK'
}

function Write-CelestialLog {
    param([string]$Message, [string]$Level = 'INFO')
    Write-Host ("[{0}] {1}" -f $Level, $Message)
}

function Read-CelestialManifest {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "install-manifest.json 不存在: $Path"
    }
    $manifest = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($name in @('schemaVersion', 'productId', 'displayName', 'version', 'entryPoint', 'installDirName')) {
        if (-not $manifest.PSObject.Properties[$name] -or [string]::IsNullOrWhiteSpace([string]$manifest.$name)) {
            throw "install-manifest.json 缺少必需字段: $name"
        }
    }
    if ([string]$manifest.entryPoint -notmatch '\.exe$') {
        throw "entryPoint 必须是 .exe（实际: $($manifest.entryPoint)）"
    }
    if (-not $manifest.PSObject.Properties['payloadIncludes'] -or @($manifest.payloadIncludes).Count -eq 0) {
        throw "install-manifest.json 缺少 payloadIncludes"
    }
    $script:CelestialState.ManifestDirectory = Split-Path -Parent (Resolve-Path -LiteralPath $Path).Path
    $script:CelestialState.Manifest = $manifest
    return $manifest
}

function Get-CelestialLayout {
    param($Manifest, [string]$Root)
    if ([string]::IsNullOrWhiteSpace($Root)) {
        if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
            throw "无法确定 LOCALAPPDATA，请用 -Root 指定安装根目录"
        }
        $Root = Join-Path $env:LOCALAPPDATA 'Celestial'
    }
    $resolved = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Root)
    $layout = [pscustomobject]@{
        Root       = $resolved
        Programs   = Join-Path $resolved 'Programs'
        InstallDir = Join-Path (Join-Path $resolved 'Programs') $Manifest.installDirName
        VenvDir    = Join-Path (Join-Path (Join-Path $resolved 'Programs') $Manifest.installDirName) '.venv'
        ReportDir  = Join-Path $resolved 'installers'
        ReportPath = Join-Path (Join-Path $resolved 'installers') ($Manifest.productId + '.json')
    }
    $script:CelestialState.Layout = $layout
    return $layout
}

function Add-CelestialDependency {
    param(
        [string]$Kind,
        [string]$Status,
        [string]$Version = '',
        [string]$Detail = '',
        [bool]$Required = $true
    )
    $null = $script:CelestialState.Dependencies.Add([pscustomobject][ordered]@{
        kind = $Kind; status = $Status; version = $Version; detail = $Detail; required = $Required
    })
}

function Add-CelestialWarning {
    param([string]$Message)
    $null = $script:CelestialState.Warnings.Add($Message)
    Write-CelestialLog $Message 'WARN'
}

function Test-CelestialExcluded {
    param([string]$RelativePath, [string[]]$Patterns)
    $normalized = $RelativePath.Replace('\', '/')
    $segments = $normalized.Split('/')
    foreach ($pattern in @($Patterns)) {
        if ([string]::IsNullOrWhiteSpace($pattern)) { continue }
        $candidate = $pattern.Replace('\', '/').TrimEnd('/')
        if ($candidate -match '[\*\?]') {
            if ($normalized -like $candidate) { return $true }
            foreach ($segment in $segments) {
                if ($segment -like $candidate) { return $true }
            }
            continue
        }
        if ($normalized -eq $candidate -or $normalized.StartsWith($candidate + '/')) { return $true }
        if (('/' + $normalized + '/').Contains('/' + $candidate + '/')) { return $true }
    }
    return $false
}

function Get-CelestialPythonCandidates {
    $candidates = New-Object System.Collections.Generic.List[string]
    $add = {
        param([string]$Path)
        if ([string]::IsNullOrWhiteSpace($Path)) { return }
        if (-not $candidates.Contains($Path)) { $candidates.Add($Path) }
    }
    if (-not [string]::IsNullOrWhiteSpace($env:CELESTIAL_PYTHON)) {
        & $add $env:CELESTIAL_PYTHON
    }
    $commands = @(Get-Command python.exe -ErrorAction SilentlyContinue)
    foreach ($command in $commands) {
        if ($command -and $command.Source) { & $add $command.Source }
    }
    $patterns = @(
        (Join-Path $env:LOCALAPPDATA 'Celestial\runtime\python\python.exe')
    )
    if ($env:LOCALAPPDATA) {
        $patterns += (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python3*\python.exe')
    }
    if ($env:ProgramFiles) {
        $patterns += (Join-Path $env:ProgramFiles 'Python3*\python.exe')
    }
    $patterns += 'C:\Python3*\python.exe'
    foreach ($pattern in $patterns) {
        foreach ($item in @(Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue)) {
            & $add $item.FullName
        }
    }
    return $candidates
}

function Test-CelestialPythonAt {
    param([string]$Path, [version]$MinVersion, [bool]$RequiresTk)
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }
    $probe = @'
import json, sys
info = {"version": "%d.%d.%d" % sys.version_info[:3], "executable": sys.executable, "tk": False, "pip": False}
try:
    import tkinter
    info["tk"] = True
except Exception as error:
    info["tkError"] = str(error)
try:
    import pip
    info["pip"] = True
except Exception as error:
    info["pipError"] = str(error)
print(json.dumps(info))
'@
    # Run from a temporary file: Windows PowerShell 5.1 drops quotes from native
    # command-line arguments, which corrupts an inline `-c` probe on multiline code.
    $probePath = Join-Path $env:TEMP ('celestial-python-probe-' + [guid]::NewGuid().ToString('N') + '.py')
    Set-Content -LiteralPath $probePath -Value $probe -Encoding ASCII
    try {
        $raw = & $Path -B $probePath 2>&1
        $probeExit = $LASTEXITCODE
    } finally {
        Remove-Item -LiteralPath $probePath -Force -ErrorAction SilentlyContinue
    }
    if ($probeExit -ne 0 -or -not $raw) { return $null }
    $line = @($raw)[-1]
    try { $info = $line | ConvertFrom-Json } catch { return $null }
    if (-not $info -or -not $info.version) { return $null }
    try { $version = [version]$info.version } catch { return $null }
    $info | Add-Member -NotePropertyName VersionObject -NotePropertyValue $version -Force
    $info | Add-Member -NotePropertyName Path -NotePropertyValue $Path -Force
    $info | Add-Member -NotePropertyName MeetsMinimum -NotePropertyValue ($version -ge $MinVersion) -Force
    $info | Add-Member -NotePropertyName HasTk -NotePropertyValue ([bool]$info.tk) -Force
    return $info
}

function Find-CelestialPython {
    param($Manifest)
    $spec = $null
    if ($Manifest.PSObject.Properties['python']) { $spec = $Manifest.python }
    $minVersion = [version]'3.12'
    if ($spec -and $spec.minVersion) { $minVersion = [version]$spec.minVersion }
    $requiresTk = $true
    if ($spec -and $spec.PSObject.Properties['requiresTk']) { $requiresTk = [bool]$spec.requiresTk }
    $fallback = $null
    foreach ($candidate in Get-CelestialPythonCandidates) {
        $info = Test-CelestialPythonAt -Path $candidate -MinVersion $minVersion -RequiresTk $requiresTk
        if (-not $info) { continue }
        if (-not $info.MeetsMinimum) { continue }
        if (-not $info.HasTk -and $requiresTk) {
            if (-not $fallback) { $fallback = $info }
            continue
        }
        return $info
    }
    if ($fallback) {
        Write-CelestialLog ("找到 Python {0} 但缺少 Tk: {1}" -f $fallback.version, $fallback.Path) 'WARN'
    }
    return $null
}

function Install-CelestialPython {
    param($Manifest, $Layout)
    $spec = $null
    if ($Manifest.PSObject.Properties['python']) { $spec = $Manifest.python }
    $minVersion = [version]'3.12'
    if ($spec -and $spec.minVersion) { $minVersion = [version]$spec.minVersion }
    $wingetId = 'Python.Python.3.12'
    if ($spec -and $spec.PSObject.Properties['wingetId'] -and $spec.wingetId) { $wingetId = $spec.wingetId }

    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($winget) {
        Write-CelestialLog "尝试 winget 安装 $wingetId（当前用户）"
        try {
            & $winget.Source install --id $wingetId -e --scope user --silent --accept-package-agreements --accept-source-agreements 2>&1 | ForEach-Object { Write-CelestialLog ([string]$_) }
        } catch {
            Write-CelestialLog ("winget 失败: {0}" -f $_.Exception.Message) 'WARN'
        }
        $found = Find-CelestialPython -Manifest $Manifest
        if ($found) { return $found }
    } else {
        Write-CelestialLog "未找到 winget，改用 python.org 官方安装器" 'WARN'
    }

    $url = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe'
    if ($spec -and $spec.PSObject.Properties['downloadUrl'] -and $spec.downloadUrl) { $url = $spec.downloadUrl }
    $download = Join-Path $env:TEMP ('celestial-python-' + [guid]::NewGuid().ToString('N') + '.exe')
    Write-CelestialLog "下载官方安装器: $url"
    Invoke-WebRequest -Uri $url -OutFile $download -UseBasicParsing
    $targetDir = Join-Path $Layout.Root 'runtime\python'
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    $arguments = '/quiet InstallAllUsers=0 PrependPath=0 Include_tcltk=1 Include_pip=1 Include_launcher=0 Include_test=0 Shortcuts=0 AssociateFiles=0 TargetDir="{0}"' -f $targetDir
    Write-CelestialLog "运行 python.org 安装器（当前用户，$targetDir）"
    $process = Start-Process -FilePath $download -ArgumentList $arguments -Wait -PassThru
    Remove-Item -LiteralPath $download -Force -ErrorAction SilentlyContinue
    if (@(0, 3010) -notcontains $process.ExitCode) {
        throw "python.org 安装器失败，退出码 $($process.ExitCode)"
    }
    $candidate = Join-Path $targetDir 'python.exe'
    $found = Test-CelestialPythonAt -Path $candidate -MinVersion $minVersion -RequiresTk $true
    if (-not $found) { throw "Python 安装完成后仍无法通过 Tk 检查: $candidate" }
    return $found
}

function Install-CelestialVenv {
    param($Manifest, $Layout, [string]$PythonPath, [bool]$Force)
    $venvPython = Join-Path $Layout.VenvDir 'Scripts\python.exe'
    $status = 'OK'
    if ($Force -and (Test-Path -LiteralPath $Layout.VenvDir)) {
        Write-CelestialLog "强制重建 venv: $($Layout.VenvDir)"
        Remove-Item -LiteralPath $Layout.VenvDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $Layout.InstallDir | Out-Null
    if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-CelestialLog "创建 venv: $($Layout.VenvDir)"
        & $PythonPath -m venv $Layout.VenvDir
        if ($LASTEXITCODE -ne 0) { throw "创建 venv 失败，退出码 $LASTEXITCODE" }
        $status = 'INSTALLED'
    }
    if (-not (Test-Path -LiteralPath $venvPython)) {
        throw "venv 中缺少 python: $venvPython"
    }

    $requirements = $null
    if ($Manifest.PSObject.Properties['pipRequirements'] -and $Manifest.pipRequirements) {
        $requirements = Join-Path $script:CelestialState.ManifestDirectory $Manifest.pipRequirements
    }
    if ($requirements -and (Test-Path -LiteralPath $requirements)) {
        $packages = @(Get-Content -LiteralPath $requirements -Encoding UTF8 | Where-Object {
            $line = $_.Trim()
            $line -ne '' -and -not $line.StartsWith('#')
        })
        if ($packages.Count -gt 0) {
            Write-CelestialLog ("安装 pip 依赖（{0} 项）: {1}" -f $packages.Count, $requirements)
            & $venvPython -m pip install --disable-pip-version-check --no-input -r $requirements
            if ($LASTEXITCODE -ne 0) { throw "pip install 失败，退出码 $LASTEXITCODE" }
            $status = 'INSTALLED'
        } else {
            Write-CelestialLog "requirements 文件无第三方包；跳过 pip install（venv 已就绪）"
        }
    }
    & $venvPython -m pip check
    if ($LASTEXITCODE -ne 0) { throw "pip check 失败，退出码 $LASTEXITCODE" }
    return [pscustomobject]@{ VenvPython = $venvPython; Status = $status }
}

function Get-CelestialPayloadHashes {
    param($Manifest, $Layout)
    $excludes = @('__pycache__', '*.pyc', '*.pyo', '.git', '.venv', 'state')
    if ($Manifest.PSObject.Properties['payloadExcludes']) {
        foreach ($pattern in @($Manifest.payloadExcludes)) { $excludes += [string]$pattern }
    }
    $files = Get-ChildItem -LiteralPath $Layout.InstallDir -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $relative = $_.FullName.Substring($Layout.InstallDir.Length).TrimStart('\')
            -not (Test-CelestialExcluded -RelativePath $relative -Patterns $excludes)
        }
    return $files
}

function Copy-CelestialPayload {
    param($Manifest, $Layout, [string]$SourceRoot)
    if (-not (Test-Path -LiteralPath $SourceRoot -PathType Container)) {
        throw "payload 源目录不存在: $SourceRoot"
    }
    $excludes = @('__pycache__', '*.pyc', '*.pyo', '.git', '.venv', 'state')
    if ($Manifest.PSObject.Properties['payloadExcludes']) {
        foreach ($pattern in @($Manifest.payloadExcludes)) { $excludes += [string]$pattern }
    }
    New-Item -ItemType Directory -Force -Path $Layout.InstallDir | Out-Null
    $copied = 0
    foreach ($item in @($Manifest.payloadIncludes)) {
        $relativeItem = [string]$item
        $source = Join-Path $SourceRoot $relativeItem
        if (-not (Test-Path -LiteralPath $source)) {
            throw "payload 缺失: $relativeItem（请确认仓库 checkout 完整）"
        }
        $target = Join-Path $Layout.InstallDir $relativeItem
        if (Test-Path -LiteralPath $source -PathType Container) {
            $sourceRootPath = (Resolve-Path -LiteralPath $source).Path
            foreach ($file in @(Get-ChildItem -LiteralPath $source -Recurse -File)) {
                $relativeFile = $file.FullName.Substring($sourceRootPath.Length).TrimStart('\')
                $repoRelative = Join-Path $relativeItem $relativeFile
                if (Test-CelestialExcluded -RelativePath $repoRelative -Patterns $excludes) { continue }
                $destination = Join-Path $target $relativeFile
                New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
                Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
                $copied++
            }
        } else {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
            Copy-Item -LiteralPath $source -Destination $target -Force
            $copied++
        }
    }
    Write-CelestialLog "payload 已复制（$copied 个文件）到 $($Layout.InstallDir)"

    $hashes = @(Get-CelestialPayloadHashes -Manifest $Manifest -Layout $Layout | ForEach-Object {
        [pscustomobject][ordered]@{
            path = $_.FullName.Substring($Layout.InstallDir.Length).TrimStart('\')
            sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            bytes = $_.Length
        }
    } | Sort-Object path)
    $receipt = [ordered]@{
        schemaVersion = 1
        productId = $Manifest.productId
        version = $Manifest.version
        generatedAt = (Get-Date).ToUniversalTime().ToString('o')
        files = $hashes
    }
    $receiptPath = Join-Path $Layout.InstallDir 'install-receipt.json'
    $receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
    # Optional pinned hashes: when present they must all match.
    if ($Manifest.PSObject.Properties['payloadSha256']) {
        $expected = $Manifest.payloadSha256
        foreach ($property in $expected.PSObject.Properties) {
            $relative = $property.Name.Replace('\', '/')
            $match = $hashes | Where-Object { $_.path.Replace('\', '/') -eq $relative }
            if (-not $match) { throw "清单固定了哈希但 payload 中缺少文件: $relative" }
            if ($match.sha256 -ne ([string]$property.Value).ToLowerInvariant()) {
                throw "payload 哈希校验失败: $relative"
            }
        }
        Write-CelestialLog "payload SHA-256 校验通过（$(@($expected.PSObject.Properties).Count) 个固定文件）"
    }
    return $hashes
}

function New-CelestialShortcut {
    param($Manifest, $Layout, [string]$Path)
    $shortcutSpec = $Manifest.shortcut
    $target = Join-Path $Layout.InstallDir $Manifest.entryPoint
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
        throw "快捷方式目标不存在: $target"
    }
    if ([IO.Path]::GetExtension($target).ToLowerInvariant() -ne '.exe') {
        throw "快捷方式目标必须是 .exe: $target"
    }
    $arguments = ''
    if ($Manifest.PSObject.Properties['entryArguments'] -and $Manifest.entryArguments) {
        $arguments = ([string]$Manifest.entryArguments).Replace('{installDir}', $Layout.InstallDir)
    }
    if ($arguments -match '(?i)\.(cmd|bat|ps1)("|\s|$)') {
        throw "entryArguments 不得指向 cmd/bat/ps1: $arguments"
    }
    $workingDirectory = $Layout.InstallDir
    if ($shortcutSpec -and $shortcutSpec.PSObject.Properties['workingDirectory'] -and $shortcutSpec.workingDirectory) {
        $workingDirectory = Join-Path $Layout.InstallDir ([string]$shortcutSpec.workingDirectory)
    }
    $icon = $target
    if ($shortcutSpec -and $shortcutSpec.PSObject.Properties['icon'] -and $shortcutSpec.icon) {
        $icon = Join-Path $Layout.InstallDir ([string]$shortcutSpec.icon)
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path) | Out-Null
    $shell = New-Object -ComObject WScript.Shell
    try {
        $link = $shell.CreateShortcut($Path)
        $link.TargetPath = $target
        $link.Arguments = $arguments
        $link.WorkingDirectory = $workingDirectory
        $link.IconLocation = "$icon,0"
        $link.Description = [string]$Manifest.displayName
        $link.Save()
        $saved = $shell.CreateShortcut($Path)
        if ($saved.TargetPath -ne $target) {
            throw "快捷方式目标校验失败: $($saved.TargetPath) != $target"
        }
        return [pscustomobject][ordered]@{
            path = $Path
            targetPath = $saved.TargetPath
            arguments = $saved.Arguments
            workingDirectory = $saved.WorkingDirectory
            iconLocation = $saved.IconLocation
        }
    } finally {
        if ($shell) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($shell) }
    }
}

function New-CelestialShortcuts {
    param($Manifest, $Layout)
    $spec = $Manifest.shortcut
    if (-not $spec) { return @() }
    $name = [string]$spec.name
    $created = @()
    if ($spec.desktop) {
        $desktop = [Environment]::GetFolderPath('Desktop')
        if (-not $desktop) { throw "无法确定桌面目录" }
        $path = Join-Path $desktop ($name + '.lnk')
        $record = New-CelestialShortcut -Manifest $Manifest -Layout $Layout -Path $path
        $record | Add-Member -NotePropertyName scope -NotePropertyValue 'desktop' -Force
        $null = $script:CelestialState.Shortcuts.Add($record)
        Write-CelestialLog "桌面快捷方式: $path -> $($record.targetPath) $($record.arguments)"
        $created += $record
    }
    if ($spec.startMenu) {
        $programs = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Celestial'
        $path = Join-Path $programs ($name + '.lnk')
        $record = New-CelestialShortcut -Manifest $Manifest -Layout $Layout -Path $path
        $record | Add-Member -NotePropertyName scope -NotePropertyValue 'startMenu' -Force
        $null = $script:CelestialState.Shortcuts.Add($record)
        Write-CelestialLog "开始菜单快捷方式: $path -> $($record.targetPath) $($record.arguments)"
        $created += $record
    }
    return $created
}

function Test-CelestialOptionalChecks {
    param($Manifest, $Layout)
    if (-not $Manifest.PSObject.Properties['optionalChecks']) { return }
    $venvPython = Join-Path $Layout.VenvDir 'Scripts\python.exe'
    foreach ($check in @($Manifest.optionalChecks)) {
        $kind = [string]$check.kind
        $record = [pscustomobject][ordered]@{
            kind = $kind; status = 'MISSING'; detail = ''; required = $false
        }
        switch ($kind) {
            'ollama' {
                try {
                    $response = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3 -ErrorAction Stop
                    $record.status = 'OK'
                    $record.detail = ('本机模型 {0} 个' -f @($response.models).Count)
                } catch {
                    $record.status = 'MISSING'
                    $record.detail = 'Ollama 未运行（仅报告，不自动下载模型）'
                }
            }
            'python-module' {
                if (Test-Path -LiteralPath $venvPython) {
                    $module = [string]$check.module
                    & $venvPython -B -c ("import {0}" -f $module) 2>$null
                    if ($LASTEXITCODE -eq 0) { $record.status = 'OK'; $record.detail = ("venv 内可导入 {0}" -f $module) }
                    else { $record.status = 'MISSING'; $record.detail = ("venv 内缺少 {0}" -f $module) }
                } else {
                    $record.status = 'MISSING'
                    $record.detail = 'venv 尚未创建'
                }
            }
            default {
                $record.status = 'SKIPPED'
                $record.detail = "未实现的 optionalChecks kind: $kind"
            }
        }
        if ($check.PSObject.Properties['reason'] -and $check.reason) {
            $record.detail = ($record.detail + '；' + [string]$check.reason).Trim('；')
        }
        $null = $script:CelestialState.Optional.Add($record)
        Write-CelestialLog ("可选检查 {0}: {1} ({2})" -f $kind, $record.status, $record.detail)
    }
}

function Write-CelestialReport {
    param($Manifest, $Layout, [string]$Mode, [string]$Result, [string[]]$Errors = @())
    $payload = [ordered]@{
        schemaVersion = 1
        productId = [string]$Manifest.productId
        displayName = [string]$Manifest.displayName
        version = [string]$Manifest.version
        mode = $Mode
        result = $Result
        generatedAt = (Get-Date).ToUniversalTime().ToString('o')
        host = $env:COMPUTERNAME
        root = $Layout.Root
        installDir = $Layout.InstallDir
        entryPoint = (Join-Path $Layout.InstallDir ([string]$Manifest.entryPoint))
        dependencies = @($script:CelestialState.Dependencies)
        optionalChecks = @($script:CelestialState.Optional)
        shortcuts = @($script:CelestialState.Shortcuts)
        warnings = @($script:CelestialState.Warnings)
        errors = @($Errors)
    }
    New-Item -ItemType Directory -Force -Path $Layout.ReportDir | Out-Null
    $payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Layout.ReportPath -Encoding UTF8
    Write-CelestialLog "依赖报告: $($Layout.ReportPath)"
    return $payload
}

function Test-CelestialEntryCheck {
    param($Manifest, [string]$BasePath)
    if (-not $Manifest.PSObject.Properties['entryCheck'] -or -not $Manifest.entryCheck) {
        return [pscustomobject]@{ Ok = $true; Path = '' }
    }
    $relative = [string]$Manifest.entryCheck.path
    $path = Join-Path $BasePath $relative
    return [pscustomobject]@{ Ok = (Test-Path -LiteralPath $path -PathType Leaf); Path = $relative }
}

function Test-CelestialPayloadSources {
    param($Manifest, [string]$SourceRoot)
    foreach ($item in @($Manifest.payloadIncludes)) {
        $source = Join-Path $SourceRoot ([string]$item)
        if (-not (Test-Path -LiteralPath $source)) {
            return [pscustomobject]@{ Ok = $false; Missing = [string]$item }
        }
    }
    $entry = Test-CelestialEntryCheck -Manifest $Manifest -BasePath $SourceRoot
    if (-not $entry.Ok) {
        return [pscustomobject]@{ Ok = $false; Missing = $entry.Path }
    }
    return [pscustomobject]@{ Ok = $true; Missing = '' }
}

function Invoke-CelestialCheck {
    param($Manifest, $Layout, [string]$SourceRoot)
    Reset-CelestialSession
    $python = Find-CelestialPython -Manifest $Manifest
    if ($python) {
        Add-CelestialDependency -Kind 'python' -Status 'OK' -Version $python.version -Detail $python.Path
        Add-CelestialDependency -Kind 'python-tk' -Status ($(if ($python.HasTk) { 'OK' } else { 'MISSING' })) -Version ('Tk ' + $python.version) -Detail 'tkinter 可导入'
        Add-CelestialDependency -Kind 'pip' -Status ($(if ($python.pip) { 'OK' } else { 'MISSING' })) -Version $python.version -Detail 'python -m pip 可用'
    } else {
        Add-CelestialDependency -Kind 'python' -Status 'MISSING' -Detail '未找到 Python 3.12+（含 Tk）；安装器将尝试 winget/python.org 自动安装'
    }
    $venvPython = Join-Path $Layout.VenvDir 'Scripts\python.exe'
    if (Test-Path -LiteralPath $venvPython) {
        & $venvPython -m pip check 2>&1 | Out-Null
        $pipOk = ($LASTEXITCODE -eq 0)
        Add-CelestialDependency -Kind 'venv' -Status 'OK' -Version '' -Detail $Layout.VenvDir
        Add-CelestialDependency -Kind 'pip-requirements' -Status ($(if ($pipOk) { 'OK' } else { 'MISSING' })) -Detail $venvPython
    } else {
        Add-CelestialDependency -Kind 'venv' -Status 'MISSING' -Detail '安装时将创建 venv'
        Add-CelestialDependency -Kind 'pip-requirements' -Status 'MISSING' -Detail '安装时将创建 venv 并执行 pip install'
    }
    $payload = Test-CelestialPayloadSources -Manifest $Manifest -SourceRoot $SourceRoot
    Add-CelestialDependency -Kind 'payload' -Status ($(if ($payload.Ok) { 'OK' } else { 'MISSING' })) -Detail ($(if ($payload.Ok) { $SourceRoot } else { '缺少 payload 项: ' + $payload.Missing }))
    Test-CelestialOptionalChecks -Manifest $Manifest -Layout $Layout
    # Verify an existing installation's shortcuts without modifying it.
    $shortcut = $Manifest.shortcut
    if (Test-Path -LiteralPath $Layout.InstallDir) {
        foreach ($scope in @('desktop', 'startMenu')) {
            if (-not $shortcut -or -not $shortcut.$scope) { continue }
            $path = if ($scope -eq 'desktop') {
                Join-Path ([Environment]::GetFolderPath('Desktop')) ([string]$shortcut.name + '.lnk')
            } else {
                Join-Path (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Celestial') ([string]$shortcut.name + '.lnk')
            }
            if (Test-Path -LiteralPath $path) {
                $shell = New-Object -ComObject WScript.Shell
                try {
                    $link = $shell.CreateShortcut($path)
                    $null = $script:CelestialState.Shortcuts.Add([pscustomobject][ordered]@{
                        scope = $scope; path = $path; targetPath = $link.TargetPath
                        arguments = $link.Arguments; workingDirectory = $link.WorkingDirectory
                    })
                } finally {
                    if ($shell) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($shell) }
                }
            }
        }
    }
    $failed = @($script:CelestialState.Dependencies | Where-Object {
        $_.required -and $_.kind -in @('python', 'python-tk', 'pip') -and $_.status -ne 'OK'
    })
    $result = if ($failed.Count -eq 0) { 'OK' } else { 'FAILED' }
    $script:CelestialState.Result = $result
    $report = Write-CelestialReport -Manifest $Manifest -Layout $Layout -Mode 'check' -Result $result
    foreach ($dependency in $report.dependencies) {
        Write-CelestialLog ("{0,-18} {1,-10} {2}" -f $dependency.kind, $dependency.status, $dependency.detail)
    }
    if ($result -eq 'OK') {
        Write-CelestialLog "依赖检查通过；运行 Install.ps1 执行安装/修复"
        return 0
    }
    Write-Host "[FAILED] 必需依赖不满足；安装器不会创建快捷方式" -ForegroundColor Red
    return 2
}

function Install-Celestial {
    param($Manifest, $Layout, [string]$SourceRoot, [bool]$Force)
    Reset-CelestialSession
    $errors = New-Object System.Collections.ArrayList
    try {
        Write-CelestialLog ("安装 {0} {1} -> {2}" -f $Manifest.displayName, $Manifest.version, $Layout.InstallDir)
        $payload = Test-CelestialPayloadSources -Manifest $Manifest -SourceRoot $SourceRoot
        if (-not $payload.Ok) { throw "payload 缺失: $($payload.Missing)；请确认仓库 checkout 完整" }
        Add-CelestialDependency -Kind 'payload' -Status 'OK' -Detail $SourceRoot

        $python = Find-CelestialPython -Manifest $Manifest
        if ($python) {
            Add-CelestialDependency -Kind 'python' -Status 'OK' -Version $python.version -Detail $python.Path
        } else {
            Write-CelestialLog "未找到可用的 Python 3.12+（含 Tk），尝试自动安装"
            $python = Install-CelestialPython -Manifest $Manifest -Layout $Layout
            Add-CelestialDependency -Kind 'python' -Status 'INSTALLED' -Version $python.version -Detail $python.Path
        }
        Add-CelestialDependency -Kind 'python-tk' -Status ($(if ($python.HasTk) { 'OK' } else { 'MISSING' })) -Detail ('Tk ' + $python.version)
        Add-CelestialDependency -Kind 'pip' -Status ($(if ($python.pip) { 'OK' } else { 'MISSING' })) -Version $python.version -Detail 'python -m pip'
        if (-not $python.HasTk) { throw "Python 缺少 Tk，无法运行窗口程序" }

        $null = Copy-CelestialPayload -Manifest $Manifest -Layout $Layout -SourceRoot $SourceRoot
        $entry = Test-CelestialEntryCheck -Manifest $Manifest -BasePath $Layout.InstallDir
        if (-not $entry.Ok) { throw "payload 缺少入口文件: $($entry.Path)" }
        $venv = Install-CelestialVenv -Manifest $Manifest -Layout $Layout -PythonPath $python.Path -Force $Force
        Add-CelestialDependency -Kind 'venv' -Status $venv.Status -Detail $Layout.VenvDir
        Add-CelestialDependency -Kind 'pip-requirements' -Status $(if ($venv.Status -eq 'INSTALLED') { 'INSTALLED' } else { 'OK' }) -Detail 'pip check 通过'
        New-Item -ItemType Directory -Force -Path (Join-Path $Layout.InstallDir 'state') | Out-Null
        Test-CelestialOptionalChecks -Manifest $Manifest -Layout $Layout

        $entry = Join-Path $Layout.InstallDir ([string]$Manifest.entryPoint)
        if (-not (Test-Path -LiteralPath $entry -PathType Leaf)) { throw "安装后缺少入口可执行文件: $entry" }
        $null = New-CelestialShortcuts -Manifest $Manifest -Layout $Layout
        $report = Write-CelestialReport -Manifest $Manifest -Layout $Layout -Mode 'install' -Result 'OK'
        Write-CelestialLog ("安装完成：{0}" -f $Layout.InstallDir)
        foreach ($shortcut in $report.shortcuts) {
            Write-CelestialLog ("快捷方式 {0}: {1} -> {2} {3}" -f $shortcut.scope, $shortcut.path, $shortcut.targetPath, $shortcut.arguments)
        }
        return 0
    } catch {
        $message = $_.Exception.Message
        $null = $errors.Add($message)
        Write-Host ("[FAILED] {0}" -f $message) -ForegroundColor Red
        $null = Write-CelestialReport -Manifest $Manifest -Layout $Layout -Mode 'install' -Result 'FAILED' -Errors $errors
        return 2
    }
}

function Uninstall-Celestial {
    param($Manifest, $Layout, [bool]$PurgeState)
    Reset-CelestialSession
    $spec = $Manifest.shortcut
    $removed = @()
    if ($spec) {
        $name = [string]$spec.name
        $paths = @()
        if ($spec.desktop) { $paths += (Join-Path ([Environment]::GetFolderPath('Desktop')) ($name + '.lnk')) }
        if ($spec.startMenu) { $paths += (Join-Path (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Celestial') ($name + '.lnk')) }
        foreach ($path in $paths) {
            if (Test-Path -LiteralPath $path) {
                Remove-Item -LiteralPath $path -Force
                Write-CelestialLog "已删除快捷方式: $path"
                $removed += $path
            }
        }
    }
    if (Test-Path -LiteralPath $Layout.InstallDir) {
        Remove-Item -LiteralPath $Layout.InstallDir -Recurse -Force
        Write-CelestialLog "已删除安装目录: $($Layout.InstallDir)（用户数据目录保留）"
    }
    if ($PurgeState) {
        $stateDir = Join-Path $Layout.Root 'state'
        if (Test-Path -LiteralPath $stateDir) { Remove-Item -LiteralPath $stateDir -Recurse -Force }
        Write-CelestialLog "已清理安装根 state 目录（-PurgeState）"
    }
    $null = Write-CelestialReport -Manifest $Manifest -Layout $Layout -Mode 'uninstall' -Result 'OK'
    return 0
}

Export-ModuleMember -Function `
    Read-CelestialManifest, Get-CelestialLayout, Invoke-CelestialCheck, Install-Celestial, `
    Uninstall-Celestial, Write-CelestialReport, Test-CelestialExcluded, Find-CelestialPython, `
    Install-CelestialPython, New-CelestialShortcut, New-CelestialShortcuts, Copy-CelestialPayload, `
    Write-CelestialLog
