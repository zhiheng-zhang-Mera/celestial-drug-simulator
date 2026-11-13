# Round 2 验收证据 · Celestial Drug Simulator

- 日期：2026-11-13（Asia/Shanghai），主机 Windows，Python 3.14.3，PowerShell 7（另测 Windows PowerShell 5.1）
- 规范：`Celestial-Research-Intelligence-CRI/docs/Architecture/ROUND2-UX-HELP-ICON-MOBILE-SPEC.md`

## 文件

| 文件 | 内容 |
|---|---|
| `help-bubble-collapsed-celestial-drug-simulator.png` | 真实 Tk 窗口，默认收起状态（各区域 `?`） |
| `help-bubble-expanded-celestial-drug-simulator.png` | 点击资料/在线状态 `?` 后展开的静态说明 |
| `ui-celestial-drug-simulator.json` | 12 个浮标的 key/文本/字数；开关、Enter、Esc、点击空白；`iconbitmap`+`iconphoto` 应用与路径 |
| `installer-verification.json` | `-CheckOnly`、临时根安装、图标复制与快捷方式 `IconLocation` 回读、`celestial-product.json`、安装后启动窗口、幂等重装、卸载 |
| `single-instance-mutex.json` / `single-instance-file.json` | 真实双进程单实例验证（互斥体 / 文件锁回退） |

## 复现命令与结果

```powershell
python -B -m unittest discover -s tests      # Ran 109 tests · OK
python -B scripts/verify_round2_ui.py        # PASS（12 bubbles；toggle/keyboard/Esc/click-away/icon）
pwsh -File ./installer/Install.ps1 -CheckOnly                       # exit 0
pwsh -File ./installer/Install.ps1 -Root "$env:TEMP\..." -Force     # exit 0
pwsh -File ./installer/Install.ps1 -Root "$env:TEMP\..."            # exit 0（幂等）
pwsh -File ./installer/Install.ps1 -CheckOnly -Root "$env:TEMP\..." # exit 0（安装后 icon/registration OK）
pwsh -File ./installer/Install.ps1 -Uninstall -Root "$env:TEMP\..." # exit 0
pwsh -File ./scripts/Test-SingleInstance.ps1                 # PASS（mutex）
pwsh -File ./scripts/Test-SingleInstance.ps1 -LockMode file  # PASS（file fallback）
```

安装器回读结果（临时根；默认根为 `%LOCALAPPDATA%\Celestial\Programs\Celestial-Drug-Simulator`）：

- TargetPath：`<install>\.venv\Scripts\pythonw.exe`，Arguments：`-m src.app`，工作目录 `<install>`
- IconLocation：`<install>\assets\branding\celestial-drug-simulator.ico,0`，图标文件存在
- `celestial-product.json`：productId / entryPoint / entryArguments / workingDirectory / iconPath / shortcuts
- 安装后按快捷方式目标启动：真实窗口出现（`installedLaunchWindow=true`）
- payload 逐文件 SHA-256 复制校验通过；`install-receipt.json` 存在

## NOT_RUN

- 纯新主机（无 Python）自动安装：本机已有 Python 3.14.3，winget / python.org 下载分支未触发。
- 原生 PySide6/QtWebEngine 3D 解剖视图：安装 venv 默认可选包不安装；本机系统 Python 有
  PySide6 6.12.0 但 venv 隔离。缺失时产品回退简化视图（核心 Tk 工作流已测）。
- Throne 主控「子项目」实际发现并启动本仓：跨仓验收属于 Celestial-Throne；本仓仅验证
  `celestial-product.json` 已生成且字段可读。
- `node --test tests/web_anatomy.test.mjs`、GUI 视频、Android/移动端：未运行。
