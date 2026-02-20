# Backend TODO List（Profile / Users + Realtime / WS）

## 1) 将“更新个人资料”接口由 PUT 改为 PATCH（优先级：最高）
**现状**
- 当前 OpenAPI 为 `PUT /users/me`，请求体 `UserUpdate` 中 `email` 为 required。
- 前端 Profile 页面是“部分字段更新”场景：常见仅改 `username` / `password` / `avatar`，邮箱在 UI 层通常不可编辑。

**问题**
- PUT + email required 会迫使前端每次更新都提交 email（即便不改），不符合“部分更新”语义，也增加出错面（422 / 数据被覆盖风险）。
- 若未来字段增加（auto_accept 等），PUT 的“全量提交”更容易出现旧值覆盖新值的问题。

**目标**
- 支持真正的 partial update：前端只提交变更字段，未提交字段保持不变。

**建议改动**
- 新增或替换为：`PATCH /users/me`
  - Request body 使用 `UserPatch`（所有字段可选，不要 required）
  - 返回 `UserDetailsResponse` 或 `User`（保持与 `GET /users/me` 对齐）
- `PUT /users/me` 处理策略：
  - ✅ 推荐：保留一段时间做兼容，但标记 deprecated（文档注明将下线）
  - 或：直接移除（若你们没有外部依赖）

**实现思路**
- Pydantic Schema：`UserPatch` 所有字段 `Optional[...] = None`
- Service 层：
  - 仅对 `payload` 中非 `None` 字段进行更新（partial merge）
  - 对关键字段做业务校验（username 唯一性等）
- DB 更新方式：
  - 明确区分 “缺失字段” vs “字段显式置空(null)”（如果允许清空 username）
  - 推荐：用 `exclude_unset=True` 提取实际提交字段；只有这些字段参与 update

**验收标准**
- PATCH 仅传 `{ "username": "new" }` 可以成功更新，不需要 email
- PATCH 不传 password 时不会改密码
- PATCH 不传 avatar 时不会改头像
- 未提交字段不会被覆盖为默认值 / null


## 2) 头像更新方式梳理：avatar_base64 vs multipart（建议标准化）
**现状**
- OpenAPI `UserUpdate` 包含 `avatar_base64` 字段（base64 直传）。

**风险**
- base64 会放大请求体积（约 33%），且占用 CPU/内存编码解码，移动端/弱网体验差。

**建议**
- 推荐提供 `POST /users/me/avatar`（multipart/form-data）或 `PATCH /users/me/avatar`：
  - 接收 file
  - 服务端保存后返回新的 `avatar_path`
- 若必须继续支持 base64：
  - 限制最大尺寸（例如 1MB/2MB）
  - 明确接受格式（data URL vs pure base64）
  - 做图片类型校验与安全处理（内容嗅探、防 SVG 注入等）

**验收标准**
- 前端可用文件上传接口完成头像更新，返回可直接展示的 `avatar_path`


## 3) Email 修改策略（明确产品规则 + 后端约束）
**现状**
- 前端计划 v1 将 email 设为不可编辑（只读）。

**建议**
- 如果后端仍允许改 email：
  - 明确是否需要二次验证（发送验证邮件、重新登录等）
  - 否则可先禁用 email 更新（PATCH/PUT 忽略 email 或拒绝更新）

**验收标准**
- API 行为与产品策略一致，避免“前端禁了、后端允许”导致的不一致


## 4) 返回结构统一（建议对齐 GET /users/me）
**建议**
- `PATCH /users/me` 返回结构尽量与 `GET /users/me` 一致（包含 avatar_path / auto_accept 等）
- 方便前端直接 `auth.me = response`，无需额外再 getMe

**验收标准**
- 更新后前端无需额外请求即可刷新 UI（用户名、头像即时更新）


## 5) OpenAPI 文档同步与兼容说明
- 在 OpenAPI 中新增 `PATCH /users/me`，标记 `PUT /users/me` 为 deprecated（如保留）
- 更新 schema：`UserPatch`（全部 optional）
- 写明字段语义：`null` 是否表示清空、缺失是否表示不变

**验收标准**
- 前后端对字段是否可空、是否可缺失有明确共识，减少联调歧义


# Realtime / WebSocket TODO List（Rooms / Messages / Playback）

## 6) WS 消息 Envelope 统一（优先级：高）
**现状**
- 目前 WS 事件多数为 `{ type, payload }`
- 认证阶段客户端发送为 `{ token }`（不符合统一 envelope）

**问题**
- 客户端需要为认证写特殊分支，不利于协议扩展与复用（后续 refresh / reauth / multi-device 更麻烦）

**目标**
- 客户端/服务端所有消息统一使用同一种结构，减少 special case

**建议改动**
- 统一为：`{ v: 1, type: string, payload?: object, request_id?: string, topic?: string, ts?: string }`
- 认证改为：
  - server -> `{ type: "auth_required", payload: { timeout: 30 } }`
  - client -> `{ type: "auth", payload: { token } }`

**验收标准**
- WS 全链路仅解析 `type` 即可完成路由，不需要针对认证消息做特殊 JSON 结构判断


## 7) 明确 WS 认证主路径（Web 优先）（优先级：高）
**现状**
- 同时存在 “Header Bearer token” 与 “连接后 token message” 两条路径

**问题**
- 浏览器原生 WebSocket 无法自定义 Authorization header（Web 端不可用），导致设计语义不一致

**目标**
- 明确一条 Web 可用的标准做法，降低协议复杂度

**建议**
- 推荐固定使用 “连接后 auth 事件” 作为标准路径（配合第 6 条的统一 envelope）
- 如果未来需要 URL query token，作为明确的备选策略并写入文档（安全注意事项）

**验收标准**
- 文档明确：Web 客户端如何认证、失败如何处理（token 过期 / 无效）


## 8) 房间订阅（enter/leave）升级为“可恢复的订阅会话模型”（优先级：高）
**现状**
- enter_room / leave_room 负责加入/退出房间并维护在线成员
- 断线重连后需要客户端自行恢复订阅状态

**问题**
- 客户端需要保存并恢复订阅列表；重连后状态可能不一致，debug 成本高

**目标**
- 让订阅状态可查询、可恢复、可批量处理

**建议改动**
- 增加会话状态查询事件（任选其一）：
  - `rooms.subscriptions.get` -> 返回当前连接订阅的 room 列表与状态
  - 或在 `connection_established` payload 中返回订阅状态（若服务端保留会话上下文）
- 支持批量订阅（可选但推荐）：
  - `rooms.subscribe` payload: `{ room_ids: [...] }`
  - `rooms.unsubscribe` payload: `{ room_ids: [...] }`
- 重连策略定义清晰：是否自动恢复订阅，或需要客户端显式重订阅

**验收标准**
- 客户端在断线重连后能可靠恢复到正确的 room 订阅状态（无需复杂分支逻辑）


## 9) Chat 消息一致性：定义 ack / 幂等 / 去重语义（优先级：高）
**现状**
- 发送消息目前走 REST create；WS 负责广播 `room_message`

**问题**
- 设计层面缺少“确认语义”：客户端如何确认消息已持久化、重试如何避免重复、pending 如何对齐

**目标**
- 让消息发送具备幂等性与可对账性，确保重试不重复、列表不抖动

**建议改动**
- 引入 `client_msg_id`（UUID）：
  - REST create：客户端提交 `client_msg_id`
  - REST response：回传 `id + client_msg_id + created_at`
  - WS 广播：包含 `client_msg_id`（至少发送者可见；或对所有人可见以便去重）
- 可选补充 WS ack 事件（用于纯 WS send 或增强 UX）：
  - `message.ack` payload: `{ client_msg_id, server_id, created_at }`

**验收标准**
- 同一条消息在网络重试/重复提交下不会生成重复记录（或前端可可靠去重）
- 客户端可从 pending -> sent 的状态机稳定对齐


## 10) WS 事件命名规范化（优先级：中）
**现状**
- 事件命名混合（room_message / room_entered / room_left 等），扩展后容易变乱

**目标**
- 形成稳定的领域事件命名约定，便于前后端协作与版本演进

**建议**
- 采用点分层级命名（示例）：
  - `auth.required`, `auth.success`, `auth.error`
  - `room.entered`, `room.left`, `room.enter_error`
  - `message.created`
  - `room.member_joined`, `room.member_left`
  - `room.read_updated`
- 文档维护“事件字典”（Event Catalog）

**验收标准**
- 新增事件不再随意命名；事件能按 domain 快速检索与归档


## 11) Notifications 与 Messages 的实时推送边界明确（优先级：中）
**现状**
- 前端已明确 Notification vs Message 分离
- 后端需明确：系统通知是否复用同一条 WS，还是拆分连接

**目标**
- 避免后续把 chat 未读、系统通知、播放同步混在一起导致权限/扩展复杂

**建议**
- 小规模：同一 WS，按 type 区分（简化连接）
- 可扩展：按域拆分 WS endpoint（例如 `/ws` vs `/ws/notifications`），并在文档中明确

**验收标准**
- 文档明确每类实时事件属于哪个 channel/endpoint；权限与订阅边界一致


## 12) 协议版本化 + 错误模型统一（优先级：中）
**现状**
- WS 事件缺少版本号与统一的错误结构

**目标**
- 支持协议演进，减少旧客户端被新事件/字段破坏

**建议**
- Envelope 加 `v`（协议版本），初始为 `1`
- 统一错误结构：
  - `{ type: "error", payload: { code, message, details?, request_id?, topic? } }`
- 对关键请求型事件引入 `request_id`（客户端生成），用于链路追踪与错误定位

**验收标准**
- WS 文档包含：版本字段、错误码表、错误 payload 结构示例


## 13)（可选）统一“请求-响应型 WS 操作”的语义（优先级：低-中）
**场景**
- enter_room/leave_room、订阅列表查询、read state 更新等可能需要明确的请求/响应配对

**建议**
- 所有“请求型事件”都带 `request_id`
- 响应事件回带同一 `request_id`，便于客户端 resolve/reject

**验收标准**
- 客户端不需要靠时间/状态猜测请求是否成功；可按 request_id 完成一次操作闭环


## 14) 单连接下的“逻辑通道（topic）订阅模型”（折中方案，优先级：高）
**动机**
- 保持“单 WS 连接”的简单与稳定，同时获得“多连接/多端点”的隔离、按需与可控能力

**目标**
- 一条连接上实现多业务域隔离：chat / playback / notifications / presence 等互不干扰
- 客户端只接收自己订阅的消息，减少不必要推送与处理
- 为未来拆分多端点/多服务预留演进路径（topic 规则可复用）

**建议改动（协议层）**
- Envelope 顶层新增 `topic` 字段（见第 6 条）
- 增加订阅/取消订阅事件：
  - client -> `subscribe` payload: `{ topics: string[] }`
  - client -> `unsubscribe` payload: `{ topics: string[] }`
  - server -> `subscribed` / `unsubscribed`（可选，带 request_id）
- 服务端推送事件必须携带 `topic`，并且仅推给订阅者：
  - 示例 topic 规范（建议）：
    - `room:{roomId}:chat`
    - `room:{roomId}:playback`
    - `room:{roomId}:presence`
    - `user:{userId}:notifications`（或 `user:me:notifications`）

**与 enter_room/leave_room 的关系（不推翻现有设计）**
- `enter_room/leave_room` 继续作为“房间会话层”（权限校验、在线成员/presence 基础）
- `subscribe/unsubscribe` 作为“事件流选择层”（在已进入房间后细分 chat/playback 等事件）
- 断线重连后的恢复策略：
  - 连接重建后，服务端可要求客户端重新发送 subscribe（简单）
  - 或服务端在 `connection_established` 后提示恢复订阅（更智能）

**验收标准**
- 进入房间但未订阅 `room:{id}:chat` 时，不会收到 chat 事件
- 退出房间/取消订阅后，不再收到相关 topic 的推送
- 单连接下可同时订阅多个 room 的不同域 topic（例如仅订阅所有 room 的 notifications/presence）
- 为未来拆分多端点时，topic 命名与事件 schema 仍可复用（迁移成本低）
