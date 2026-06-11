<!-- Language: English (primary) · 中文见下方 -->

# YouTube Email Scraper

A small **macOS / Windows** desktop tool: paste one or many YouTube channel links, click once, and it pulls each channel's **name, link, public email, and subscriber count**, then exports everything to **Excel** with one click. A command-line version is included too.

> Only emails the creator has **made public** (in the channel "About" or video descriptions) are collected. It does **not** bypass YouTube's CAPTCHA-gated "business email" button. Use lawfully and within YouTube's Terms of Service.

**中文说明见本文档下半部分 → [跳到中文](#中文说明)**

---

## Download

Pre-built apps are published on the **[Releases](../../releases)** page (produced automatically by CI):

| Platform | File | Notes |
|---|---|---|
| **Windows** | `YouTubeEmailScraper.exe` | Single file, double-click to run. No Python needed. |
| **macOS** | `YouTube邮箱采集器.dmg` | Open, then run. No Python needed. |

> Not signed/notarized, so the first launch shows a security prompt — see [First launch](#first-launch--getting-past-the-security-prompt).

---

## What it does

- ✅ One or **many** channels at once (one link per line)
- ✅ Pulls **channel name, link, public email, subscriber count**
- ✅ One-click **Excel (.xlsx)** export
- ✅ Detects lightly-obfuscated emails (e.g. `name (at) gmail (dot) com`)
- ✅ Auto-dedupe and junk-email filtering
- ✅ Optional: scan recent **video descriptions** when the About page has no email
- ✅ Works on **macOS and Windows**; packaged builds need **no Python**

![Interface guide](docs/interface.svg)

---

## How to use (GUI)

1. **① Paste links** — one channel link per line into the top box.
2. **② Get / Load** — click to start; the table fills row by row.
   - You can **Stop** anytime, or **Clear** the table.
   - Tick **"scan video descriptions when no email"** for deeper (slower) search.
3. **③ Results** — name, link, email, subscribers, status. **Double-click a row to open that channel.**
4. **④ Export Excel** — save the results as `.xlsx`.

Accepted link forms (auto-normalized): `https://youtube.com/@Handle`, `/channel/UC…`, `/c/Name`, `/user/Name`, `@Handle`, or just `Handle`.

---

## First launch — getting past the security prompt

The apps aren't paid-Apple/Windows code-signed, so the first open is gated. This is normal (not malware).

**macOS** — the `.dmg` ships with a one-click helper:
1. Open the `.dmg`, then **double-click `打不开请双击我.command`** → click **Open** in the small terminal window → it installs and launches the app automatically.
2. Or: right-click the app → **Open** → **Open**; on newer macOS go to **System Settings → Privacy & Security → Open Anyway**.

![First-open guide](docs/first-open-guide.svg)

**Windows** — double-click the `.exe`. If SmartScreen appears, click **More info → Run anyway**.

---

## What it can / can't find

| Where the email is | Found? |
|---|---|
| In the **channel description** | ✅ Yes |
| In a **video description** (enable the video-scan option) | ✅ Yes |
| Behind the CAPTCHA-gated **"view email address"** button | ❌ No (any scraper would need a human to solve the CAPTCHA) |
| Not published anywhere | ❌ No |

So some channels showing "no email" is expected — it isn't a bug.

---

## Excel output

One sheet with columns: **YouTube频道名称 (name) · YouTube频道链接 (link) · YouTuber邮箱 (email) · 订阅数据 (subscribers) · 状态 (status)**. Multiple emails are joined with `; `. Status is `成功` (found) / `无邮箱` (none) / `错误` (error).

---

## Command line

```bash
pip install -r requirements.txt

# single / multiple channels
python youtube_email_scraper.py -u https://www.youtube.com/@TechOnEarth
python youtube_email_scraper.py -u @ChannelA @ChannelB

# batch from a file → CSV
python youtube_email_scraper.py -f channels.txt -o results.csv

# also scan up to 15 recent video descriptions → JSON
python youtube_email_scraper.py -f channels.txt --videos 15 -o results.json
```

| Flag | Meaning |
|---|---|
| `-u, --url` | one or more channel links / handles |
| `-f, --file` | file with one channel per line |
| `-o, --output` | output path, `.csv` or `.json` |
| `--videos N` | scan N recent video descriptions if About has no email (default 0) |
| `--delay S` | seconds between channels (default 1.5) |

---

## Build from source

⚠️ **PyInstaller can't cross-compile** — build the Windows `.exe` on Windows, the macOS `.app` on macOS.

**macOS** (`bash build_macos.sh`) — must use a Python whose bundled **Tcl/Tk is ≥ 8.6** (Homebrew Tk 9.0, or python.org universal2 Tk 8.6). The script picks one automatically and **refuses the system `/usr/bin/python3`**, because its Tk 8.5 crashes on launch (`Tcl_Panic`) on recent macOS. Output: `dist/YouTube邮箱采集器.dmg`.

**Windows** (`build_windows.bat`, needs [python.org](https://www.python.org/downloads/) Python) — output: `dist\YouTubeEmailScraper.exe`.

**Cloud (no Windows machine needed)** — CI is set up in `.github/workflows/build.yml`. Run **Actions → Build apps**, or push a `v*` tag, to build the Windows `.exe` + macOS `.dmg` and publish them to **[Releases](../../releases)** automatically.

---

## Project layout

```
youtube_email_gui.py        GUI (main app)
youtube_email_scraper.py    scraping engine + CLI
requirements.txt            deps (requests, openpyxl)
youtube_email_gui.spec      PyInstaller config
build_macos.sh              one-click macOS .dmg build
build_windows.bat           one-click Windows .exe build
dist-extras/                Gatekeeper "one-click unblock" helper + notes (bundled into the dmg)
docs/                       interface & first-open guide images
.github/workflows/build.yml cloud build → Windows .exe + macOS .dmg to Releases
```

## Disclaimer

For collecting **publicly listed** contact info only (e.g. business inquiries). You are responsible for complying with YouTube's Terms of Service, local laws, and privacy regulations (GDPR/PIPL). Do not use for harassment or spam.

<br/>

---
---

<a id="中文说明"></a>
# YouTube 邮箱采集器（中文说明）

一个 **macOS / Windows 通用**的小工具：粘贴一个或一批 YouTube 频道链接，点一下，自动抓取每个频道的 **名称、链接、公开邮箱、订阅数**，并一键导出 **Excel**。也带命令行版本。

> 只采集创作者**已公开**的邮箱（频道简介 / 视频简介里写的）。不会绕过 YouTube 那个需要验证码的"商务邮箱"按钮。请合法、并在符合 YouTube 服务条款的前提下使用。

## 下载

预编译好的程序发布在 **[Releases](../../releases)** 页（由 CI 自动构建）：

| 平台 | 文件 | 说明 |
|---|---|---|
| **Windows** | `YouTubeEmailScraper.exe` | 单文件，双击即用，免装 Python |
| **macOS** | `YouTube邮箱采集器.dmg` | 打开后运行，免装 Python |

> 未做签名，首次打开会有安全提示 —— 见下方[首次打开](#首次打开如何通过安全提示)。

## 功能

- ✅ 单个或**批量**频道（每行一个）
- ✅ 抓取**名称、链接、公开邮箱、订阅数**
- ✅ 一键导出 **Excel（.xlsx）**
- ✅ 识别轻度伪装邮箱（如 `name (at) gmail (dot) com`）
- ✅ 自动去重、过滤无效邮箱
- ✅ 可选：About 没邮箱时扫描最近**视频简介**
- ✅ macOS / Windows 都能用，打包版**免装 Python**

## 怎么用（图形界面）

1. **① 粘贴链接** —— 每行一个频道链接。
2. **② 获取 / 加载** —— 点击开始，表格逐行出结果（可随时**停止 / 清空**；勾选「没邮箱时扫描视频简介」可挖得更深、更慢）。
3. **③ 抓取结果** —— 名称、链接、邮箱、订阅数、状态；**双击某行可打开该频道**。
4. **④ 导出 Excel** —— 保存为 `.xlsx`。

支持的链接写法（自动归一化）：`https://youtube.com/@用户名`、`/channel/UC…`、`/c/名称`、`/user/名称`、`@用户名`、或直接 `用户名`。

## 首次打开（如何通过安全提示）

没买苹果/Windows 签名，所以首次打开会被拦，这是正常现象、并非有毒。

**macOS** —— dmg 里带了一键小工具：
1. 打开 dmg，**双击 `打不开请双击我.command`** → 弹窗点【打开】→ 自动装好并打开；
2. 或右键 App →「打开」→「打开」；新版 macOS 到 *系统设置 → 隐私与安全性* 点「仍要打开」。

**Windows** —— 双击 `.exe`；若弹 SmartScreen，点**更多信息 → 仍要运行**。

## 能抓到 / 抓不到什么

| 邮箱位置 | 能否抓到 |
|---|---|
| 写在**频道简介**里 | ✅ 能 |
| 写在**视频简介**里（需勾选扫描） | ✅ 能 |
| 验证码挡住的「查看邮箱」按钮后面 | ❌ 不能（任何工具都得人工过验证码） |
| 根本没公开 | ❌ 没有就是没有 |

所以部分频道显示「无邮箱」是正常的，不是工具坏了。

## 导出的 Excel

一个工作表，列为：**YouTube频道名称 · YouTube频道链接 · YouTuber邮箱 · 订阅数据 · 状态**。多个邮箱用 `; ` 分隔；状态为 `成功 / 无邮箱 / 错误`。

## 命令行

```bash
pip install -r requirements.txt
python youtube_email_scraper.py -u https://www.youtube.com/@TechOnEarth      # 单个
python youtube_email_scraper.py -f channels.txt -o results.csv               # 批量 → CSV
python youtube_email_scraper.py -f channels.txt --videos 15 -o results.json  # 扫视频简介
```

参数：`-u` 链接/用户名（可多个）、`-f` 批量文件、`-o` 输出（.csv/.json）、`--videos N` 扫描 N 个视频简介、`--delay S` 频道间隔秒数。

## 自行打包

⚠️ **不能跨平台编译**：Windows 的 `.exe` 必须在 Windows 上打，macOS 的 `.app` 必须在 macOS 上打。

- **macOS**：`bash build_macos.sh`。必须用**自带 Tcl/Tk ≥ 8.6** 的 Python（Homebrew Tk 9.0 或 python.org Tk 8.6）；脚本会自动挑选，并**拒绝系统 `/usr/bin/python3`**（它的 Tk 8.5 在新版 macOS 上一启动就 `Tcl_Panic` 崩溃）。
- **Windows**：在装了 [python.org](https://www.python.org/downloads/) Python 的机器上双击 `build_windows.bat`，产出 `dist\YouTubeEmailScraper.exe`。
- **云端（无需 Windows 机器）**：CI 已配置在 `.github/workflows/build.yml`。运行 **Actions → Build apps**（或打 `v*` tag），即可同时构建 Windows `.exe` + macOS `.dmg` 并自动发布到 **[Releases](../../releases)**。

## 免责声明

仅用于采集创作者**已公开**的联系方式（如商务合作）。请自行遵守 YouTube 服务条款、当地法律及隐私法规（GDPR / 个人信息保护法），切勿用于骚扰或群发垃圾邮件。
