# Bilibili 播放链路技术验证

## 2026-10-09 补充：预取上限验收与调整

用户确认修正截断分段校验后，测试视频完整预取了 357 秒，另一个 BV 也播放流畅。这表明当前本机播放链路在这两个样本上可用；尚不代表所有视频或网络环境均稳定。根据用户反馈，前方预取目标上限由 600 秒收紧到 300 秒：短于 5 分钟尽量预取到片尾，较长视频最多提前预取 5 分钟。实际缓冲仍受网络与浏览器媒体缓冲区约束。

## 2026-10-09 补充：缓冲区归零

用户澄清：本次一直暂停在 0 秒，只是缓冲条预取到约一半时突然全部消失；不是播放位置跳回开头。日志里备用 Akamai 的一条视频 Range 标记为“完成”，实际仅接收 182/850 KiB。原型先前把上游响应体正常结束等同于分段完整，未核对 `Content-Length`，可能把截断分段交给播放器。现加入字节数校验，截断时令该请求失败并启用备用 CDN；同时记录缓冲终点及媒体事件，以便下一次测试区分截断、播放器重载和缓冲区容量问题。尚不能仅凭现有数据断定缓冲区归零的唯一原因。

## 2026-10-09 补充：真实播放请求

用户在 112.9/357 秒处前方缓冲为 0，尽管预取目标已设为 357 秒。音频 Range 约 0.1 秒完成；视频相邻 Range 耗时 5.8、10.7 秒，而 `bytes=18246843-19215765` 同一视频分段两次只收到 735/946 KiB 后中断（5.2 与 12.1 秒）。这说明增大前方缓冲目标未解决视频数据交付问题，短段测速也无法代表实际播放。原型现对播放中断后的下一次请求切换到同轨道、已通过 Range 验证且文件大小一致的备用 CDN；仍须验收它能否稳定传完整分段，以及是否有本机协议或播放器导致的中断。

## 2026-10-09 补充：卡顿位置与测速偏差

改用备用 Akamai 后，用户仍在先前没有播放过的位置遇到卡顿；再次运行的固定 512 KiB 分段测速中，两个 CDN 分别约 35.1 和 41.0 Mbps，本机协议约 46.9 Mbps。这些结果与播放体验不一致，可能受已播放片段、缓存或瞬时波动影响，不能据此认定持续播放链路正常，也不能仅凭第一次结果认定 CDN 选择就是根因。原型现增加实际播放请求诊断，记录视频和音频 Range 的响应头、首字节、传输进度、完成或错误状态；等待卡顿当时的数据再区分是 CDN 下载、协议转发还是播放器消费环节。

用户观察到缓冲条在播放位置接近时才增加。核对已安装的 Shaka Player 5.2.12 配置，原型没有覆盖默认的 `streaming.bufferingGoal=10` 秒，符合“小段缓冲”的表现。现将目标设为视频时长、上限 600 秒；本次约 357 秒的样本应尝试预取到片尾。该值是目标而非保证，后续仍需同时观察真实前方缓冲和实际 Range 请求，不能仅凭调整配置判定卡顿已解决。

## 2026-10-09 补充：CDN 选择

同一条 1080P AVC 轨道的一次本机实测中，当前 `upos-sz-mirrorcosov.bilivideo.com` 的固定位置 Range 约 0.4 Mbps（首响应 7.46 秒），备用 `upos-hz-mirrorakam.akamaized.net` 约 4.5 Mbps（首响应 0.85 秒）。经本机协议约 0.6 Mbps，接近当时慢 CDN 的速度。原型此前只用 2 字节 Range 检查可用性，因而改为加载前对视频和音频候选各取一小段测速并选择较快者。但随后的播放仍卡顿，说明这次固定分段测速不足以解释或解决问题。

日期：2026-10-09。环境：本地 Windows 开发机、项目 `backend/venv`；先进行匿名预检，随后由用户扫码完成一次登录态验证。未启动 iCinema 服务，也未修改生产 VPS。公开样本：[BV1EGfzBREBQ](https://www.bilibili.com/video/BV1EGfzBREBQ/)。媒体验证仅请求两个 2 字节 Range；没有保存或公开带签名的媒体 URL。

| 检查点 | 实测结果 | 结论 |
| --- | --- | --- |
| 现有 BV 输入解析器 | `backend/tests/unit/bilibili/test_identifiers.py`：13 项通过 | 可接受 BV 和常规视频网址，拒绝任意主机；尚未验证上游资源。 |
| `x/web-interface/view` | 同一环境曾返回 200，但多次返回 HTTP 412 HTML 风控页 | 不能把它作为无回退、必定成功的第一步；标题/作品详情仍待稳定验证。 |
| `x/player/pagelist` | HTTP 200、业务码 0，样本首个 CID 为 `36237935785` | 可以作为获取分 P/CID 的实测路径；不是标题接口。 |
| `x/player/playurl` 和 `x/player/wbi/playurl` | 匿名请求 `qn=80, fnval=16`，本次均 HTTP 200、业务码 0；实际 `quality=64`，4 条视频轨、3 条音频轨 | 普通投稿可返回 DASH；请求 1080P 不代表实际获得 1080P。WBI 签名、登录态和长期稳定性未验证。 |
| DASH 字段 | 视频和音频轨均含 `SegmentBase`；视频样本含 AVC/H.265 候选，音频含 AAC | 可构造标准 MPD；必须按浏览器 codec 能力筛选，不可只取数组第一条。 |
| CDN 主机 | 候选顺序会变，见到 `*.bilivideo.com` 与 `upos-hz-mirrorakam.akamaized.net` | 原计划只允许 `*.bilivideo.com`/`*.bilibili.com` 会丢掉部分备选；也不应因此笼统允许 `*.akamaized.net`。 |
| CDN Range 与 CORS | 选取 `bilivideo.com` 视频和音频候选，`Range: bytes=0-1` 都返回 206、2 字节、`Content-Range`；模拟站点 Origin 时响应带对应 `Access-Control-Allow-Origin`，并暴露 `Content-Length,Content-Range` | 服务器请求层面具备浏览器直连的必要条件；模拟 Origin **不等于**在真实浏览器中成功播放。一次视频 Range 不带 Referer 也返回 206，不能推广到其他 CDN/视频。 |

关键差距是：普通 iCinema 网页能否在不取得 B 站 Cookie 的前提下使用用户的登录态、真实浏览器能否直连并播放完整媒体、以及两名用户独立登录时能否可靠同步。`view` 的匿名 412 不能推断为作品不存在；`pagelist` 可取 CID，但不能补齐作品详情。用户已明确排除 VPS 媒体转发，浏览器直连失败时不设计网关回退。后续先验证官方外链播放器的登录态与同步控制；详见[更新后的接入计划](../architecture/bilibili-provider-plan.md)。

代码接点已核对：`RoomVideoSourceType` 只有外链、本地、Omofun；Omofun 的 `external_url` 会进入房间实时状态与持久快照；前端 `useRoomMediaEngine` 目前只有 HLS、直接视频和本地文件引擎。Bilibili 需要独立房间身份和异步的个人媒体解析，不能直接套用 Omofun 的外链广播。

## 登录预检（未使用账号）

`/x/passport-login/web/qrcode/generate` 实测 HTTP 200、业务码 0，返回 32 字符的 `qrcode_key` 和 `account.bilibili.com` 登录链接。立即调用 `/x/passport-login/web/qrcode/poll` 实测 HTTP 200、外层业务码 0、内层状态 `86101`（待扫码）。本次只是 API 可行性实验；后续不按“iCinema 后端替每位用户扫码并保存 Cookie”的方式实施。

## 用户扫码后的登录态验证

用户使用 B 站 App 扫码确认后，轮询状态转为 `0`；测试进程获得 `SESSDATA` 与 `bili_jct`，`x/web-interface/nav` 返回 HTTP 200、业务码 0、`isLogin=true`。凭据值、昵称和用户 ID 均未输出。对同一 BV：

- `x/web-interface/view`：HTTP 200、业务码 0，含标题和 CID。此前匿名 412 时有发生，因此不能仅凭这一例断言登录必然解决 412。
- `x/player/pagelist`：HTTP 200、业务码 0。
- `x/player/wbi/playurl` 与 `x/player/playurl`：均 HTTP 200、业务码 0；请求 `qn=80, fnval=16`，实际 `quality=80`，8 条视频轨、3 条音频轨。此前同一样本的匿名结果为 `quality=64`、4 条视频轨、3 条音频轨。这里只验证此账号、此时间及此作品，不推断所有账号/作品的画质权限。
- 从登录态结果选取 `bilivideo.com` 候选视频和音频 URL，分别请求 `Range: bytes=0-1`；均返回 206、`Content-Range` 和模拟 Origin 的 CORS 头。该检查仍不能证明浏览器能解码并播放整个 DASH。

上述一次性预检仅在测试进程内使用 Cookie；扫码二维码 PNG 位于系统临时目录，进程结束时已删除。没有把 Cookie、二维码密钥、刷新令牌或媒体 URL 写入仓库、报告或日志。该预检未测试完整播放、账号续期、会员内容、DRM 和房间同步。VPS 访问 B 站媒体不再属于实施路径。

## 桌面端原型后续验证

用户已在本机 Electron 原型中完成 B 站登录，取得用户名并通过本机媒体协议播出画面和声音。最初的样本多次缓冲，用户确认其 B 站网页端也卡；改用 720P 后播放正常。此结果支持桌面端路径的可行性，但尚未验证房间同步或长期播放。原型已改用 Electron 独立的本机持久会话；用户确认登录态跨重启保留，登录成功后 B 站窗口自动关闭。

用户提供的 `BV1JneT6rEaG` 在原型中可用 1080P 播放，但明显卡顿，B 站网页端较流畅。卡顿时 Shaka 报 `1003`（网络请求超时），前方缓冲 0 秒、累计缓冲 68.4 秒、估计吞吐 1.0 Mbps，而所选固定 AVC 轨道需求约 1.5 Mbps；掉帧 380/1947。原型只向 MPD 写入一条视频轨，不能自动降档；CDN 仅经 2 字节 Range 可用性检查，没有测速或慢速切换。当前数据无法区分 CDN 与本机协议转接各自贡献的延迟。

用户进一步观察到同一视频在 B 站网页端缓冲增长很快，故不能把原型的低吞吐直接解释为用户网络带宽不足或网页端自动降档。原型增加了两段等长 Range 的本机对比测速，用于比较所选 CDN 的原生下载与通过自定义协议的下载；尚待实机运行结果。

首次在未播放位置运行该测速时，CDN 直连请求即报 `net::ERR_HTTP2_PROTOCOL_ERROR`，尚未进入本机协议对比。Chromium 将其定义为 HTTP/2 协议错误；它无法单独证明 CDN 服务端、链路中间设备或原型请求参数哪一方造成。用户反复观察到曾播放片段流畅、到新片段附近卡住，且本次掉帧为 0/2247，这使缓存掩盖新片段请求问题成为较强假设。测速现改为逐一报告候选 CDN 的结果，避免首个候选出错便丢失其他候选的信息。

随后单候选测速显示当前 `upos-sz-mirrorcosov.bilivideo.com` 的新位置 512 KiB Range 在 12 秒内未完成。它证实该候选经 Electron 直连的下载能力不足以稳定供给当前 1.5 Mbps 视频轨，但还不能推断 B 站网页端使用了同一 CDN 或编码。原型此前只允许 `*.bilivideo.com`，可能过滤了上游的 Akamai 备选；现加入受限的 `upos-*.akamaized.net` 规则，并只展示各轨道的主机名、编码和码率供下一次验证。

参考：[BiliPai 仓库与许可证](https://github.com/jay3-yy/BiliPai)、[其 DASH MPD 构造器](https://github.com/jay3-yy/BiliPai/blob/main/core-player/src/main/java/com/android/purebilibili/core/player/dash/LocalDashManifestBuilder.kt)、[其投屏代理实现](https://github.com/jay3-yy/BiliPai/blob/main/app/src/main/java/com/android/purebilibili/feature/cast/LocalProxyServer.kt)、[Shaka Player DASH 支持](https://github.com/shaka-project/shaka-player)。BiliPai 的 Android 播放能力和投屏代理代码仅作行为参考，不能代替浏览器/VPS 实测。
