# Celestial Drug Simulator 安装器

本目录是 Celestial Drug Simulator 的完整本机安装器，遵循
`Celestial-Research-Intelligence-CRI/docs/Architecture/INSTALLER-CONTRACT.md`（v1）。
安装器文件随本仓提交，不依赖其他仓库的运行文件。

## 运行要求

- Windows 10/11 x64，普通用户权限（**不需要管理员**）。
- Python 3.12+ 且包含 Tk；pip 可用。
- 核心 Tk 工作流无必需第三方 Python 包（见 `docs/RUNNING.md`）：
  - `PySide6 / QtWebEngine 6.12` 仅原生嵌入解剖视图使用，缺失时产品自动回退简化视图；
  - `numpy` 仅 `tools/build_web_anatomy.py` 构建期使用，运行时不导入。
  默认安装不下载这两个可选包（体积大、非必需）；需要原生解剖视图时可手动安装：

  ```powershell
  & "$env:LOCALAPPDATA\Celestial\Programs\Celestial-Drug-Simulator\.venv\Scripts\python.exe" `
      -m pip install "PySide6==6.12.0" "numpy>=2.0"
  ```

## 使用

```powershell
# 依赖检查 + 安装器自检（不创建/不修改安装，只写依赖报告）
./installer/Install.ps1 -CheckOnly

# 安装或修复（默认 %LOCALAPPDATA%\Celestial\Programs\Celestial-Drug-Simulator）
./installer/Install.ps1

# 强制重建 venv 并覆盖 payload（保留 state/ 与用户数据）
./installer/Install.ps1 -Force

# 安装到隔离根目录（验收/测试）
./installer/Install.ps1 -Root "$env:TEMP\celestial-installer-test" -Force

# 卸载（删除快捷方式与安装目录，保留用户数据）
./installer/Install.ps1 -Uninstall

# 卸载并清理安装根下的 state
./installer/Install.ps1 -Uninstall -PurgeState
```

退出码：`0` 成功；`2` 必需依赖无法满足或安装失败（**不会创建快捷方式**）。

脚本以 UTF-8 BOM 保存，已分别用 PowerShell 7（`pwsh`）与 Windows PowerShell 5.1
验证 `-CheckOnly`；两条命令均需在仓库根目录运行。

## 安装布局

```text
%LOCALAPPDATA%\Celestial\
  Programs\Celestial-Drug-Simulator\   # payload + .venv + state/ + install-receipt.json
  installers\celestial-drug-simulator.json  # 依赖报告（每次运行刷新）
```

- payload：`src/`、`assets/`（含 `assets/branding/`）、`data/`（不含运行时 `data/cache`、
  `data/reports`）、`docs/`、`README.md`、`celestial_single_instance.py`、`celestial_help.py`、
  `celestial_branding.py`。
- venv：`.venv\Scripts\python.exe`（运行）与 `.venv\Scripts\pythonw.exe`（快捷方式目标）。
- 入口：`pythonw.exe -m src.app`，工作目录为安装目录（`-m` 依赖该 cwd 解析 `src` 包）。
- 每次复制 payload 时逐文件比较源与安装目录的 SHA-256，不一致即失败；随后生成
  `install-receipt.json`（逐文件 SHA-256）。如清单提供 `payloadSha256` 固定哈希则额外强制校验。
- 安装后写 `celestial-product.json`（productId、displayName、entryPoint、entryArguments、
  workingDirectory、iconPath、shortcuts、registryHint），供 Throne 子项目扫描发现：
  `%LOCALAPPDATA%\Celestial\Programs\*\celestial-product.json`。
- 安装幂等：重复运行覆盖 payload、保留 `state/` 与用户数据；`-Force` 额外重建 venv。

## 依赖处理

1. 依次探测 `CELESTIAL_PYTHON`、PATH 上的 `python.exe`、
   `%LOCALAPPDATA%\Celestial\runtime\python`、`%LOCALAPPDATA%\Programs\Python\Python3*`、
   `C:\Python3*`，要求版本 ≥ 3.12 且 `import tkinter` 成功。
2. 缺失时优先 `winget install Python.Python.3.12 --scope user --silent`；
   winget 不可用或失败则下载 python.org 官方安装器并
   `/quiet InstallAllUsers=0 Include_tcltk=1 Include_pip=1 TargetDir=...`。
   该自动安装分支在本轮**未触发**（验收机已有 Python 3.14.3），标记 NOT_RUN。
3. 创建 venv 后执行 `pip install -r requirements.txt`（本产品为空清单）与 `pip check`；
   `optionalChecks` 在依赖报告中报告 PySide6 / numpy 是否可用（仅报告，不自动下载）。
4. 必需依赖失败：退出码 2，不创建桌面/开始菜单快捷方式。

依赖报告字段：`python / python-tk / pip / venv / pip-requirements / payload / icon /
registration` 的 `OK | INSTALLED | MISSING | FAILED` 与实际版本；`optionalChecks` 记录可选增强状态。

## 快捷方式

- 桌面：`[Desktop]\Celestial Drug Simulator.lnk`
- 开始菜单：`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Celestial\Celestial Drug Simulator.lnk`
- 目标：`<安装目录>\.venv\Scripts\pythonw.exe`，参数 `-m src.app`，工作目录为安装目录。
  **不是** `.cmd`/`.bat`/`powershell.exe`。这是契约对 Python 产品的适配：入口仍为真实
  `.exe`（pythonw），窗口程序无控制台。
- 图标：`IconLocation = <安装目录>\assets\branding\celestial-drug-simulator.ico,0`（安装器复制
  并在创建前检查文件存在，创建后用 WScript.Shell 回读 `TargetPath` 与 `IconLocation` 校验）。

## 单实例

`celestial_single_instance.py` 在 `src/app.py` 的 `main()` 最开始获取主机范围锁：

- 命名互斥体 `Global\Celestial.celestial-drug-simulator.simulator`；
- 全局命名空间不可用时回退 `%ProgramData%\Celestial\locks\celestial-drug-simulator.lock`
  （独占文件锁；ProgramData 不可写时再回退 `%LOCALAPPDATA%\Celestial\locks`）；
- 第二实例按窗口标题 `Celestial Drug Simulator · 人体作用与证据` 聚焦现有窗口，向 stderr
  输出 `CELESTIAL_ALREADY_RUNNING` 并以退出码 3 结束，不启动第二个 UI；
- 测试隔离：`--instance-scope=state` 只供验收脚本使用，正式入口不暴露该开关。

双进程验证：

```powershell
./scripts/Test-SingleInstance.ps1                 # 命名互斥体
./scripts/Test-SingleInstance.ps1 -LockMode file  # 文件锁回退
```

脚本会真实启动两个 GUI 进程，第二个必须退出 3 且第一个存活；随后验证第一实例退出后
新实例可再次启动。证据写入 `installer/evidence/single-instance-<mode>.json`。

## 已知限制

- `-CheckOnly` 在缺少 Python 3.12+/Tk 时退出 2（表示当前机器尚不满足安装前提）；
  venv/pip 依赖在安装前显示 `MISSING` 属于预期。
- 自动安装 Python 需要网络；离线机器请预先安装 Python 3.12+（含 Tk）。
- 默认不安装 PySide6/numpy（可选增强）；因此临时根安装的原生 3D 解剖视图会回退简化视图，
  这不影响核心 Tk 多药方案工作流。原生视图需要机器上可用的 QtWebEngine 6.12。
- 安装器不写注册表卸载项、不签名、不创建防火墙规则；卸载用 `Install.ps1 -Uninstall`。
- 单实例锁是主机范围；不同用户会话共享 `Global\` 互斥体（这是契约要求）。
