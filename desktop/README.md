# iCinema 桌面客户端

`desktop/` 是未来 iCinema 桌面客户端的归属目录，不是 B 站专用应用，也不会另建一套房间后端。规划中的分工：

| 目录 | 职责 |
| --- | --- |
| `frontend/` | 现有 Vue/Vite 界面、房间同步逻辑和可共用的播放源 UI；桌面端复用其构建产物。 |
| `backend/` | 现有账号、房间、成员、消息与播放状态同步服务；不保存 B 站凭据、不转发 B 站媒体。 |
| `desktop/` | Electron 窗口、受限的本机能力接口、用户设备上的第三方会话与必要的本机媒体协议、桌面打包。 |

当前先按 [现有业务 Electron 化计划](../docs/architecture/electron-desktop-plan.md) 建立正式桌面客户端，复用已有前端，不加入 B 站功能。[`probes/bilibili`](probes/bilibili/README.md) 是保留的隔离验证原型；它的登录与媒体能力要等现有业务桌面化验收后才接入。不要把原型页面当成正式桌面客户端界面。

## 开发版桌面壳

开发模式下，`main.cjs` 打开现有 Vite 前端，默认地址为 `http://localhost:5173/`；后端仍由现有服务提供。窗口不启用 Node 集成，不加载 B 站原型的登录、解析或媒体协议。站内路由留在桌面窗口，外部 HTTP(S) 与邮件链接交由系统打开，其余导航被阻止。

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

## Windows 便携版

在 Windows 上运行以下命令，构建前端并生成可直接运行的目录，不需要增加依赖：

```powershell
npm --prefix .\desktop run build:windows
```

命令会打印 `desktop/release/iCinema-win32-.../iCinema.exe` 的实际路径。整个目录需要一起保留或复制；双击 `iCinema.exe` 会加载内置前端，不需要启动 Vite。正式便携版把登录状态、浏览器存储和缓存放在 exe 同级的 `data/`，因此目录必须可写；更新到新的目录时请一并复制旧版的 `data/`。将来的安装版则使用 `%LOCALAPPDATA%\iCinema`，避免向安装目录写数据。两种发行模式各自保存本机登录与设置，具体位置可在“个人资料”页查看。现有数据不会自动迁移。开发命令 `start` 与 `start:built` 仍使用原来的用户数据目录。后端仍需单独运行。默认连接 `http://localhost:8000`，若后端地址不同，请从 PowerShell 启动并在当前会话设置地址：

主窗口首次打开的目标大小为 1360×960；屏幕较小时会以可用区域为上限。调整窗口大小后，Electron 会在本机数据目录保存并在下次启动时恢复普通窗口的大小与位置；已保存的尺寸优先于新的默认值，最大化或全屏状态不会自动恢复。应用内另开的窗口不会覆盖主窗口记录。

```powershell
$env:ICINEMA_API_ORIGIN = 'https://your-backend.example'
& '.\desktop\release\iCinema-win32-x64-实际后缀\iCinema.exe'
```

首次运行会在 `data/connection.json` 中生成默认后端地址。连接其他后端时，关闭 iCinema 后编辑其中的 `apiOrigin`，例如 `"https://cinema.example"`；若 WebSocket 使用不同地址，再添加 `"wsOrigin": "wss://ws.cinema.example"`。保存后重新启动即可双击连接，更新版本时该文件随 `data/` 保留。PowerShell 中的 `ICINEMA_API_ORIGIN`、`ICINEMA_WS_ORIGIN` 仍可临时覆盖文件设置。配置只接受地址根路径，不含账号或令牌；配置有误时启动会显示错误。此构建是未签名的便携版，不含安装器或后端服务；不要只复制 `.exe` 文件，也不要把已登录的 `data/` 一起放进公开发布包。
