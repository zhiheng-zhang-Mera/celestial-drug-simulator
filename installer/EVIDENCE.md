# Celestial Drug Simulator 安装器 / 单实例验收证据

- 日期：2026-11-12（本机时区 Asia/Shanghai）
- 主机：Windows，Python 3.14.3（`C:\Python314\python.exe`），PowerShell 7（pwsh）
- 仓库分支：`ui/modernization`；本文件随提交一起保存，提交 SHA 记录在任务回报中。
- 原始证据：`installer/evidence/install-verification.json`、`global-scope.json`、
  `single-instance-mutex.json`、`single-instance-file.json`。

## 1. 现有测试

```powershell
python -B -m unittest discover -s tests
# exit 0 · Ran 109 tests in ~1.1s · OK
# 原有 103 项 + 新增 test_single_instance 6 项
```

（仓库 `docs/HTML_EMBEDDING.md` 所述 `node --test tests/web_anatomy.test.mjs` 是前端
可选测试，本次未运行；不影响 Python 安装器验收。）

## 2. 安装器（临时根，真实执行）

安装/自检命令均以 `-Root "$env:TEMP\celestial-verify-<id>"` 隔离，未改动机器现有安装：

| 步骤 | 命令 | 退出码 | 结果 |
|---|---|---|---|
| 安装前自检 | `./installer/Install.ps1 -CheckOnly -Root <temp>` | 0 | python 3.14.3 / python-tk / pip 均 OK；venv、pip-requirements 为 MISSING（安装时才创建，符合预期） |
| 安装 | `./installer/Install.ps1 -Root <temp> -Force` | 0 | payload 54 文件（`src/`、`assets/`、`data/`（不含 `data/cache`）、`docs/`、README、单实例模块）+ `install-receipt.json`；`.venv\Scripts\pythonw.exe` 存在 |
| 幂等重装 | `./installer/Install.ps1 -Root <temp>` | 0 | 快捷方式 target/arguments 不变 |
| 安装后自检 | `./installer/Install.ps1 -CheckOnly -Root <temp>` | 0 | python/python-tk/pip/venv/pip-requirements/payload 全部 OK |
| 卸载 | `./installer/Install.ps1 -Uninstall -Root <temp>` | 0 | 桌面/开始菜单快捷方式与安装目录均删除 |
| 失败路径 | 临时副本删除入口 `src\app.py` 后 `Install.ps1 -Root <temp2> -Force` | 2 | 未创建任何快捷方式；依赖报告 `result=FAILED`、`payload MISSING` |

快捷方式（安装器创建后再用 WScript.Shell 独立回读校验）：

- 桌面：`[Desktop]\Celestial Drug Simulator.lnk`
- 开始菜单：`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Celestial\Celestial Drug Simulator.lnk`
- TargetPath：`<install>\.venv\Scripts\pythonw.exe`（`.exe`，非 cmd/bat；`targetExists=true`）
- Arguments：`-m src.app`
- WorkingDirectory：`<install>`
- 直接以快捷方式 TargetPath/Arguments 启动：窗口出现（`windowFound=true`），进程存活。

依赖报告：`<temp>\installers\celestial-drug-simulator.json`（内容已内嵌于
`install-verification.json`）。

同一 `-CheckOnly` 命令另在 Windows PowerShell 5.1（`powershell.exe`）下真实执行，退出码 0；
脚本以 UTF-8 BOM 保存以兼容 5.1 的 ANSI 默认编码。

可选增强检查（仅报告，不自动下载）：`PySide6`、`numpy` 在临时 venv 中为 `MISSING`。
核心 Tk 工作流按 `docs/RUNNING.md` 不依赖它们；原生 3D 解剖视图会回退简化视图。
手动启用原生视图：`& <install>\.venv\Scripts\python.exe -m pip install "PySide6==6.12.0" "numpy>=2.0"`。

## 3. 单实例（真实双进程）

| 场景 | 证据 | 结果 |
|---|---|---|
| 测试隔离 scope + 命名互斥体 | `single-instance-mutex.json` | 第一实例窗口就绪；第二实例 exit 3、stderr 含 `CELESTIAL_ALREADY_RUNNING` 且聚焦现有窗口；第一实例存活；第一实例退出后第三实例可启动 |
| 测试隔离 scope + 文件锁回退（`-LockMode file`） | `single-instance-file.json` | 同上，走 `%ProgramData%\Celestial\locks` 回退实现 |
| 正式入口默认主机 scope（无 `--instance-scope`） | `global-scope.json` | 第二实例 exit 3 且聚焦现有窗口；第一实例存活。`programDataLockExists=false`，说明实际走的是 `Global\Celestial.celestial-drug-simulator.simulator` 互斥体 |

## 4. 未实测 / 已知限制

- 未触发 winget / python.org 自动安装分支：本机已有满足要求的 Python 3.14.3 + Tk。
  该分支代码已实现但未做真实下载安装验证（网络下载大文件较慢）。
- 默认根 `%LOCALAPPDATA%\Celestial` 未做破坏性安装验证；验收统一使用临时根，
  `-CheckOnly` 在仓库路径真实执行。
- 原生 PySide6/QtWebEngine 解剖视图未在临时 venv 中实测（默认不安装该可选包；
  本机系统 Python 有 PySide6 6.12.0，但安装出的 venv 是隔离的）。核心 Tk 工作流已由
  109 项测试与真实启动覆盖。
- `node --test tests/web_anatomy.test.mjs` 未运行（前端可选测试）。
- 安装器不写注册表卸载项、不签名、不创建防火墙规则；`-Uninstall` 为正式卸载方式。
- 双进程验证会短暂显示真实 GUI 窗口，验证后已强制结束进程。
