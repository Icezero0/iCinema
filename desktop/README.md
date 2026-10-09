# iCinema 桌面客户端

`desktop/` 是未来 iCinema 桌面客户端的归属目录，不是 B 站专用应用，也不会另建一套房间后端。规划中的分工：

| 目录 | 职责 |
| --- | --- |
| `frontend/` | 现有 Vue/Vite 界面、房间同步逻辑和可共用的播放源 UI；桌面端复用其构建产物。 |
| `backend/` | 现有账号、房间、成员、消息与播放状态同步服务；不保存 B 站凭据、不转发 B 站媒体。 |
| `desktop/` | Electron 窗口、受限的本机能力接口、用户设备上的第三方会话与必要的本机媒体协议、桌面打包。 |

当前先按 [现有业务 Electron 化计划](../docs/architecture/electron-desktop-plan.md) 建立正式桌面客户端，复用已有前端，不加入 B 站功能。[`probes/bilibili`](probes/bilibili/README.md) 是保留的隔离验证原型；它的登录与媒体能力要等现有业务桌面化验收后才接入。不要把原型页面当成正式桌面客户端界面。

## 开发版桌面壳

`main.cjs` 目前只打开现有 Vite 前端，默认地址为 `http://localhost:5173/`；后端仍由现有服务提供。窗口不启用 Node 集成，不加载 B 站原型的登录、解析或媒体协议。站内路由留在桌面窗口，外部 HTTP(S) 与邮件链接交由系统打开，其余导航被阻止。

本目录声明的 Electron 版本为 `44.7.0`，与隔离验证原型一致。请先审阅依赖与命令，再自行在项目根目录运行安装：

```powershell
npm install --prefix .\desktop --no-audit --no-fund
```

保持现有前后端本地服务运行后，从项目根目录启动桌面窗口：

```powershell
npm --prefix .\desktop start
```

若 Vite 不在默认地址，可在当前 PowerShell 会话设置 `ICINEMA_DESKTOP_URL` 为前端的 HTTP(S) 根地址后再启动。当前版本只用于开发阶段验收，尚未打包前端静态资源，也尚未制作 Windows 安装包。
