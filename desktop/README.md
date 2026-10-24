# iCinema 桌面客户端

`desktop/` 是 iCinema 桌面客户端的归属目录。各目录分工：

| 目录 | 职责 |
| --- | --- |
| `frontend/` | 现有 Vue/Vite 界面、房间同步逻辑和可共用的播放源 UI；桌面端复用其构建产物。 |
| `backend/` | 现有账号、房间、成员、消息与播放状态同步服务；不保存 B 站凭据、不转发 B 站媒体。 |
| `desktop/` | Electron 窗口、受限的本机能力接口、用户设备上的第三方会话与必要的本机媒体协议、桌面打包。 |

现有业务与 B 站同步播放已完成验收。客户端按后端地址和 iCinema 用户隔离 B 站登录，凭据经系统密钥加密后保存在本机。点击分 P 后通过 Shaka 加载 DASH，Electron 本机媒体协议为 CDN 请求附加 Referer 并处理 Range；视频流由用户设备直连 CDN。房间只广播视频身份和播放状态。[`probes/bilibili`](probes/bilibili/README.md) 保留为播放技术验证资料。

## 开发版桌面壳

开发模式下，`main.cjs` 打开现有 Vite 前端，默认地址为 `http://localhost:5173/`；后端仍由现有服务提供。窗口不启用 Node 集成，B 站登录通过受限的 preload 接口打开隔离窗口。站内路由留在桌面窗口，外部 HTTP(S) 与邮件链接交由系统打开，其余导航被阻止。桌面端会读取前端开发环境的 `VITE_API_ORIGIN` 供 B 站账号隔离和用户校验使用；若用 `ICINEMA_API_ORIGIN` 临时覆盖，请与前端连接的后端保持一致。

本目录声明的 Electron 版本为 `44.7.0`，与隔离验证原型一致。请先审阅依赖与命令，再自行在项目根目录运行安装：

```powershell
npm install --prefix .\desktop --no-audit --no-fund
```

保持现有前后端本地服务运行后，从项目根目录启动桌面窗口：

```powershell
npm --prefix .\desktop start
```

若 Vite 不在默认地址，可在当前 PowerShell 会话设置 `ICINEMA_DESKTOP_URL` 为前端的 HTTP(S) 根地址后再启动。此命令使用开发服务器；内置前端预览按下一节构建。目前尚未制作 Windows 安装包。

## 内置前端预览

第二阶段可把现有前端构建并复制到 `desktop/renderer/`，然后从固定的 `icinema://app/` 页面打开。此模式不需要 Vite，后端服务仍需运行：

```powershell
npm --prefix .\desktop run build:renderer
$env:ICINEMA_API_ORIGIN = 'http://127.0.0.1:8000'
npm --prefix .\desktop run start:built
```

若后端不在本机，请把 `ICINEMA_API_ORIGIN` 改成实际地址；本机测试优先用 `localhost` 或 `127.0.0.1`，远程后端应使用 HTTPS。安全页面请求非环回 HTTP 地址可能被浏览器的混合内容规则阻止。如 WebSocket 使用另一个域名，可另设 `ICINEMA_WS_ORIGIN` 为 `ws://` 或 `wss://` 地址。桌面模式会把经过校验的地址交给现有前端，不把 Node 能力开放给页面。部署后端若限制跨域来源，需要允许 `icinema://app`。此预览尚未生成 Windows 安装包。

内置页面与开发版 Vite 页面使用不同来源，因此首次打开内置版时需要重新登录，浏览器中的本地缓存也不会自动迁移。固定的内置来源在后续版本中保持不变，以延续桌面应用内的存储。

## Windows 免安装版

在 Windows 上运行以下命令，构建前端并生成可直接运行的目录，不需要增加依赖：

```powershell
npm --prefix .\desktop run build:windows
```

命令会打印 `desktop/release/iCinema-win32-.../iCinema.exe` 的实际路径。整个目录需要一起保留或复制；双击 `iCinema.exe` 会加载内置前端，不需要启动 Vite。自 0.1.1 起，正式版统一将登录状态、设置、窗口信息和缓存保存到 `%LOCALAPPDATA%\iCinema`，通常为 `C:\Users\用户名\AppData\Local\iCinema`。免安装版也使用这一位置，更新或移动程序目录不影响本机数据；多份程序共用一个数据目录，只允许同时启动一个正式版实例。“关于”页可以查看并打开该目录。开发命令 `start` 与 `start:built` 仍使用独立的开发数据目录。

新安装默认连接 `https://icinema.site`，由 `release-config.json` 配置；已有 `connection.json` 保持原值。若后端地址不同，可关闭程序并修改用户数据目录中的 `connection.json`，或从 PowerShell 临时覆盖：

主窗口首次打开的目标大小为 1360×960；屏幕较小时会以可用区域为上限。调整窗口大小后，Electron 会在本机数据目录保存并在下次启动时恢复普通窗口的大小与位置；已保存的尺寸优先于新的默认值，最大化或全屏状态不会自动恢复。应用内另开的窗口不会覆盖主窗口记录。

```powershell
$env:ICINEMA_API_ORIGIN = 'https://your-backend.example'
& '.\desktop\release\iCinema-win32-x64-实际后缀\iCinema.exe'
```

首次运行会在 `%LOCALAPPDATA%\iCinema\connection.json` 中生成默认后端地址。连接其他后端时，编辑其中的 `apiOrigin`，例如 `"https://cinema.example"`；若 WebSocket 使用不同地址，再添加 `"wsOrigin": "wss://ws.cinema.example"`。配置只接受地址根路径，不含账号或令牌。此构建不含安装器或后端服务；发布时压缩完整程序目录，不包含个人数据。

## 从旧版迁移

升级前关闭旧版 iCinema。若新用户目录尚不存在，程序会将 exe 同级的旧 `data/` 复制到新位置，保留登录、连接配置、加密 B 站凭据、窗口设置与站内缓存，跳过可重建的 Chromium 缓存和锁文件。复制完成后才启用新目录；复制失败时停止启动，原文件不变。

如果把新版本解压到了新目录，需要在首次启动前将旧 `data/` 复制到新 exe 旁，程序才能找到它。不会搜索磁盘上的其他旧版本；新用户目录已有数据时不会覆盖或合并。迁移保留旧 `data/`，确认新版本正常后再自行处理旧目录。同一 Windows 账号下迁移加密凭据，换电脑或 Windows 账号时可能需要重新登录。

## 下载页面与版本检查

网页侧边栏的“客户端下载”页按 Windows、Android、iOS、macOS 展示。Windows 的安装版、便携版分别读取 `frontend/.env` 中的 `VITE_DESKTOP_INSTALLER_DOWNLOAD_URL`、`VITE_DESKTOP_PORTABLE_DOWNLOAD_URL`；安装版地址留空时禁用按钮并显示“暂未发布”，其他平台显示“正在开发中”。便携版未配置时回退到原有 `VITE_DESKTOP_DOWNLOAD_URL`，播放源面板也继续使用该通用入口。地址可换成自行托管的 HTTPS 下载地址；更改后需重新构建前端。桌面端同一入口显示“关于”，读取 `desktop/package.json` 的版本，进入页面或点击“检查更新”时查询 `release-config.json` 中仓库的 GitHub 最新正式 Release。

检查排除 GitHub 标记为草稿和预发行的版本，按版本号比较，并提供 Release 下载链接。网络失败或限流用 toast 提示；请求有超时与短期缓存。检查仅查询公开发布信息，不携带 iCinema 或 B 站凭据，不自动安装更新。

后续发布时同步更新 `desktop/package.json` 与锁文件中的项目版本，重新构建，并使用对应的 `v0.1.2` 等版本标签发布 Release、上传 ZIP。当前构建版本为 0.1.1；更新检测测试覆盖旧版标签 `v0.1.0-desktop-beta`。
