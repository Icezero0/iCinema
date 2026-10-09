# Bilibili 播放接入设计（功能分支）

日期：2026-10-09。分支 `feat/bilibili-playback`。当前文档是实施约束和验收顺序，不代表已经接通 Bilibili；CMS 工作暂放。目标是普通 BV 投稿视频、非 DRM DASH、每位用户使用自己的 B 站登录态，在 iCinema 房间内同步播放。

## 与当前代码的接点

- 后端 `RoomVideoSourceType` 目前只有 `external_url`、`local_file`、`omofun`；前端房间源面板也只有这三种选项。
- Omofun 房间源把 `external_url` 放进运行态和持久快照，并通过 `room_video_source_set` 发给成员。Bilibili 不能沿用这条地址广播路径：新增 `bilibili` 类型及独立元数据，只广播 `bvid`、`cid`、分P身份、播放位置和状态；不广播 CDN URL、登录凭据、代理令牌或画质权限。
- 同步核心继续控制当前页面的 `HTMLVideoElement`。Bilibili DASH 前端适配器通过 dash.js/Shaka 接到同一个 video 元素，生命周期必须与现有 HLS/本地文件引擎协调，切源时清理旧播放器。
- 用户进入或重连房间，先接收相同资源身份和房间播放快照，再由本人的会话独立获取可用画质和媒体流；无法播放的用户明确显示个人原因，不阻止有权限的成员播放。
- BiliPai 是 GPL-3.0 的 Android 实现，仅用作接口行为参考。后端用 Python 实现请求、会话和受限媒体网关；前端用 TypeScript 实现 UI、DASH 适配及现有同步接线，不复制其 Kotlin 代码。

## 分段实施与验收

1. **公开投稿播放链路实测。** 从实际 BV URL 解析 BVID，调用 `x/web-interface/view` 获取 CID 与分P；以目标 VPS 的网络环境请求播放信息，筛选普通非 DRM DASH。取得一条允许的媒体请求，验证 `Range` 返回 206。记录 API 错误码、地区限制、是否要登录与是否需要 Referer。只有实测成功才把“可解析”升级为“可播放”。
2. **按用户绑定账号。** 二维码登录由后端取得和轮询，凭据仅保存于对应 iCinema 用户的加密存储；支持查看绑定状态和退出/撤销。配置独立加密密钥，限制日志/响应不出现 `SESSDATA`、`bili_jct`、access token 或 CDN 地址。账号失效时该用户重新登录，不将房主会话借给其他人。
3. **元数据与播放解析。** 服务端按 BV、分P与 CID 获取作品信息和 `x/player/wbi/playurl` 数据，必要时使用 WBI 签名；标准化 DASH 视频/音频轨、codec、带宽、`SegmentBase`、候选 CDN 和有效期。返回明确的登录、会员、付费、地区、私密、下架及 DRM 不支持状态。只在本人有权限且存在普通非 DRM 轨时生成短期播放会话；不尝试绕过 DRM 或付费判断。
4. **受限媒体网关与 DASH 播放。** 后端依据本人短期会话中的轨 ID 选择预验证的 CDN URL，为前端生成 MPD；代理端处理 Referer、必要 User-Agent 和单段 `Range` 请求，原样保留有效的 200/206、`Content-Range`、`Accept-Ranges`、`Content-Length`、`Content-Type`。代理只能访问受控 B 站媒体域名，并在 DNS 解析和连接时检查目标为公网；禁止任意 URL 参数、重定向到新域、私网连接和无限缓存/响应。令牌短期有效，绑定 iCinema 用户与流，不写入房间状态。前端用 DASH 库驱动同一个 video 元素，验证播放、暂停、跳转和倍速。
5. **房间同步与回归。** 房主/有权限的成员选择 BV 和分P后，房间只保存身份与播放状态。两名绑定不同 B 站账号的成员各自获取媒体，重新进入可按房间位置同步；一方无 B 站权限或会话过期时只影响自身。其他播放源、房间权限、资源状态和 Omofun 刷新不中断行为需回归。

## 技术边界

- 首版只承诺普通投稿视频和非 DRM DASH；番剧、课程/PUGV、HDR、Dolby、8K、直播和 DRM 不在验收范围。
- `playurl` 和 CDN URL 会过期。过期时本人重新解析并更新本地短期会话；房间资源身份与当前播放不会因此自动切源。
- 代理媒体会消耗 VPS 出站流量和带宽；实施前用一个短样本测请求数、Range 行为及两人同时播放的带宽，再设定限流与最大连接数。
- 任何接口、登录和媒体可用性以运行中的 Bilibili 与部署地区实测为准。Android 客户端可访问不等于浏览器或目标 VPS 能访问。
- 新依赖预期为后端凭据加密库、前端 DASH 播放库。确定版本和接线后提供基于 `backend/venv` 的安装命令与前端安装命令；本文件不引入依赖。

参考：[BiliPai](https://github.com/jay3-yy/BiliPai)、[dash.js](https://github.com/Dash-Industry-Forum/dash.js)、[iCinema 房间源协议](backend/ws-protocol.md)。
