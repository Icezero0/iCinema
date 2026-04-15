# iCinema 后端重构（backend_new）继承 Prompt

你是我的 iCinema 后端重构协作助手，继续基于以下技术栈推进 `backend_new/` 项目开发：

- FastAPI
- SQLAlchemy async
- SQLite
- JWT
- WebSocket / realtime

---

## 一、协作原则

后续协作时，请严格遵守：

- 不回退到旧版 realtime 设计
- 不把前端协议改成 subscribe / unsubscribe channel
- 不把 room 业务语义重新塞回 `manager`
- 继续保持：
  - `WsMessage`
  - `ChannelKey`
  - `manager.publish(channel=..., message=WsMessage)`
  - `dispatcher + handlers/` 分层
  - `state.py` 承载 runtime state model
- 若修改 realtime，请优先检查：
  - `protocol / manager / room_presence / room_video_runtime / publisher / handlers / ws_router` 是否一致
  - 是否仍符合“初始化走 `RoomSnapshot`，增量走局部 state”的原则
- 主动控制命令继续受 `active_sync_permission` 控制
- 用户播放状态上报 command 不受 `active_sync_permission` 限制
- `sync_policy` 只用于服务端 `AUTO_PAUSE` 逻辑，不再限制手动 playback control

---

## 二、项目当前阶段

当前 backend_new 已基本完成或稳定的模块包括：

- users
- rooms
- membership
- RBAC
- notification
- RoomJoinRequest workflow
- room settings
- message 基础能力
- realtime / websocket 基础骨架

当前重点已经进入：

- room presence 与 room video runtime 的细化
- playback / source runtime 的实现
- 用户播放状态上报与房间级同步逻辑
- realtime 与 message / room / notification / membership 的后续联动

---

## 三、全局约定

### 1. 分层约定
- repo 层不 commit
- service 层控制事务
- helper 不 commit
- API 层不做复杂业务拼装
- 写操作后如果要返回 ORM 对象，必须 commit 后重新查询并 preload/selectinload，避免 MissingGreenlet

### 2. 命名约定
- `find_xxx`：返回对象或 `None`
- `get_xxx`：返回对象，查不到抛异常
- `get_xxxs` / `get_users`：列表或分页查询
- username 允许重复，不设计 `find_user_by_username`

### 3. 业务约定
- emoji 外部化（QFace）
- sticker 必须属于用户 library
- image 不校验 ownership
- join request 行为受 `join_audit_mode` 控制

---

## 四、Room Domain 当前结论

### 1. Room 主表
- 使用 `visibility` 替代旧 `is_public`
- 使用 `join_audit_mode`
- 不再使用旧 `config`

### 2. Room Settings
位于 `app/modules/rooms/settings/`，独立表，不混入 room 主表。

当前字段语义已经收敛为：

- `selected_room_video_source_type`
- `sync_policy`
- `active_sync_permission`

#### 字段含义

##### `selected_room_video_source_type`
- 表示房间当前**选中的 room video source type**
- 是一个**持久化设置状态**
- `room_video` 指在 room 中进行同步观影的对象影片
- 这个字段不是“允许类型约束”，而是“当前选中的 type 持久化状态”
- `ROOM_VIDEO_SOURCE_SET` 时应同步更新该字段

##### `sync_policy`
房间级、服务端负责的同步策略当前只保留：

- `AUTO_PAUSE`
- `DISABLED`

语义：
- `AUTO_PAUSE`：服务端根据房间内用户播放状态（尤其 `STALLING`）进行自动 pause / 自动恢复
- `DISABLED`：关闭服务端 auto pause 协调，但不影响手动 `play/pause/seek/source_set`

说明：
- `AUTO_SEEK / AUTO_SPEED / MANUAL` 不再属于房间级后端 `sync_policy`
- 这些应视为前端 / 用户侧的本地追赶策略，后端暂时忽略其具体实现

##### `active_sync_permission`
- 不废除
- 它与 RBAC 的关系是：**基于 room role 的可配置控制阈值**
- 仍用于限制主动控制命令：
  - `ROOM_VIDEO_SOURCE_SET`
  - `PLAYBACK_PLAY`
  - `PLAYBACK_PAUSE`
  - `PLAYBACK_SEEK`
- 不应该限制用户自己的播放状态上报 command

### 3. 命名统一结论
以下命名已达成一致，应继续沿用：

- `RoomMediaSourceType` → `RoomVideoSourceType`
- `PLAYBACK_SOURCE_SET` → `ROOM_VIDEO_SOURCE_SET`
- 用户播放状态：
  - command：`USER_PLAYER_STATUS`
  - event：`USER_PLAYER_STATES`

说明：
- `playback_play / pause / seek` 这三个名字保留，不继续改
- `ROOM_VIDEO_SOURCE_SET` 表示：**设置并替换房间当前完整的 room video source state**
  - `source_type`
  - 以及与该 type 对应的 source value：
    - `external_url`
    - 或 `file_hash`
- 不拆成两个 command/event；无论是切换 type，还是 type 不变但替换具体值，都视为一次完整 source replacement

### 4. RoomService / RoomSettingsService
- 已解决递归调用问题
- `RoomService` 与 `RoomSettingsService` 不再互相实例化
- 现在通过 repo + membership service 自行完成检查与兜底补建
- `RoomSettingsService` 应提供明确方法，例如：
  - `set_selected_room_video_source_type(...)`
- handler 不应直接穿透到 `RoomSettingsService.repo`

### 5. DB / migration
`room_settings` 已迁移到新字段：

- `selected_room_video_source_type`

并且 `sync_policy` 的 DB 约束需要与最新设计保持一致：

- 只允许 `auto_pause`
- `disabled`

如果旧数据中有：

- `auto_seek`
- `auto_speed`

都应迁移归并为：

- `disabled`

---

## 五、Realtime / WebSocket 当前设计

### 1. 总体设计
- 单个 tab 一条 websocket 连接
- 内部使用通用 channel 模型
- room 和 user 都是 channel
- 前端协议不直接暴露 subscribe / unsubscribe
- 前端只发送业务动作：
  - `AUTH`
  - `HEARTBEAT`
  - `COMMAND(...)`

### 2. 顶层协议
统一消息模型：

`WsMessage(v, type, payload)`

当前消息类型：
- `AUTH`
- `HEARTBEAT`
- `COMMAND`
- `EVENT`
- `ERROR`
- `ACK`

约定：
- client 不发 ACK
- COMMAND 必须带 `request_id`
- server 用 ACK / ERROR 回应 command
- `ROOM_ENTER` 的 ACK.data 返回完整 `RoomSnapshot`

### 3. 当前重要命令 / 事件
#### command
- `ROOM_ENTER`
- `ROOM_LEAVE`
- `ROOM_VIDEO_SOURCE_SET`
- `PLAYBACK_PLAY`
- `PLAYBACK_PAUSE`
- `PLAYBACK_SEEK`
- `USER_PLAYER_STATUS`

#### event
- `PRESENCE`
- `SESSION`
- `ROOM_VIDEO_SOURCE_SET`
- `PLAYBACK_PLAY`
- `PLAYBACK_PAUSE`
- `PLAYBACK_SEEK`
- `USER_PLAYER_STATES`
- 以及后续 room/message/notification 相关事件

---

## 六、Realtime 当前分层与命名

目录核心文件：

- `app/realtime/bootstrap.py`
- `app/realtime/constants.py`
- `app/realtime/channels.py`
- `app/realtime/protocol.py`
- `app/realtime/state.py`
- `app/realtime/auth.py`
- `app/realtime/manager.py`
- `app/realtime/publisher.py`
- `app/realtime/ws_router.py`
- `app/realtime/room_presence.py`
- `app/realtime/room_video_runtime.py`
- `app/realtime/handlers/`
  - `dispatcher.py`
  - `auth.py`
  - `heartbeat.py`
  - `room.py`
  - `room_video.py`

### 当前职责划分
- `manager`：只管理 websocket 连接、订阅、publish，不承载 room 业务语义
- `room_presence`：维护房间在线态（presence）
- `room_video_runtime`：维护房间 video source / playback / 用户播放状态等运行态
- `publisher`：把业务结果翻译成 ws event，并调用 publish
- `dispatcher`：顶层消息分发和错误包装
- `ws_router`：连接生命周期管理
- `state.py`：realtime runtime state model
- `handlers/room_video.py`：
  - 当前主入口 handler
  - 负责 room video runtime 相关 command
  - 旧的 `handlers/playback.py` 视为废弃残留，不应继续使用

---

## 七、room_presence 当前结论

`room_presence` 当前语义边界基本正确，应继续保持它只负责：

- 房间在线态
- 单房间单活跃连接
- room channel 的 subscribe / unsubscribe
- disconnect 时的 presence 清理

### 只管这些，不再负责：
- `RoomSnapshot` 组装
- video source / playback
- 用户播放状态
- 权限判断

### 当前已知结论
- `ws_router.finally -> presence_service.handle_disconnect()` 仍是 room presence 清理兜底点
- `PRESENCE` 不能被 `USER_PLAYER_STATES` 替代
  - `PRESENCE` 表示“谁在线 / 谁在房间里”
  - `USER_PLAYER_STATES` 表示“这些用户的播放器状态是什么”
  - 两者语义不同，不应合并

---

## 八、room_video_runtime 当前结论

`room_video_runtime` 是房间级视频运行态服务，负责：

- `room_video_source`
- `playback`
- 房间内每个在线用户的播放状态
- stalling 用户集合
- 是否因 stall 自动暂停等房间级同步辅助状态

### 当前不负责：
- websocket 发送
- room presence
- 权限判断
- DB 持久化（除上层 handler 调 `RoomSettingsService` 持久化 `selected_room_video_source_type`）

### 当前 runtime 命名收口方向
建议统一为：
- `RoomVideoSourceState`
- `room_video_source`
- `get_room_video_source()`
- `set_room_video_source()`

若局部仍残留 `VideoSourceState / video_source` 命名，应在不影响逻辑的前提下继续向上述命名收口。

---

## 九、当前已确定的重要 realtime 规则

### 1. user channel 与 room channel
- 连接注册成功后自动订阅对应 `user_channel(user_id)`
- 房间在线态通过 room channel 广播

### 2. 单房间单活跃连接
- 同一房间内，一个用户同一时刻只允许一个 active room connection
- 新连接进入同一房间时，旧连接会被替换
- 旧连接收到 `SESSION(reason="entered_elsewhere")`
- 旧连接退出该 room channel，但不必关闭整条 websocket

### 3. presence 广播策略
- `ROOM_ENTER`
  - 当前连接通过 `ACK.data` 获取完整 snapshot
  - 房间内其他连接收到 `PRESENCE`
  - 广播时排除当前连接
- `ROOM_LEAVE`
  - 当前连接只收 ACK
  - 其他连接收到 `PRESENCE`
- `disconnect`
  - 后端兜底清理 presence，并广播 `PRESENCE`

### 4. 未认证连接
- websocket 建立后先 accept
- 未认证时发送 COMMAND 不会执行，会收到 ERROR
- 连接建立后必须在配置时间内完成 AUTH
- 超时后服务端主动关闭连接
- 认证超时时间来自：
  - `WS_AUTH_TIMEOUT_SECONDS`

---

## 十、当前 state 设计

`state.py` 当前核心模型应包括：

- `PresenceState`
- `RoomVideoSourceState`
- `PlaybackState`
- `RoomSnapshot`

并扩展为：

- `RoomUserPlayerState`
- `UserPlayerStatesState`

### 语义约定
- `RoomSnapshot`：用于 `ROOM_ENTER` 初始化全量快照
- `PRESENCE`：只发 `PresenceState`
- `ROOM_VIDEO_SOURCE_SET`：只发 `RoomVideoSourceState`
- `PLAYBACK_PLAY / PAUSE / SEEK`：只发 `PlaybackState`
- 用户播放状态变化后，单独广播：
  - `USER_PLAYER_STATES`

---

## 十一、当前 playback / source 主动控制命令权限

### 主动控制命令
这些命令仍然受 `active_sync_permission` 控制：

- `ROOM_VIDEO_SOURCE_SET`
- `PLAYBACK_PLAY`
- `PLAYBACK_PAUSE`
- `PLAYBACK_SEEK`

### 权限逻辑
- `OWNER_ONLY`
- `OWNER_AND_MANAGER`
- `ALL_MEMBERS`

也就是说：
- 仍然有权限控制
- 改后不是取消权限控制，而是只保留 `active_sync_permission` 这一层

### 已明确去掉的错误逻辑
- 不再使用 `sync_policy` 限制手动 `play / pause / seek / source_set`
- `sync_policy = disabled` 不代表禁用手动同步控制
- `selected_room_video_source_type` 不是“允许类型限制”，而是“当前选中的 source type 持久化状态”

---

## 十二、用户播放状态模型（已讨论并开始接入）

房间内每个在线用户的播放状态统一建模为：

- `READY`
- `STALLING`
- `ERROR`
- `IDLE`

语义：

- `READY`：准备就绪可播放，不论当前房间是播放还是暂停，只要本地随时可播放下一帧
- `STALLING`：视频加载卡顿
- `ERROR`：视频加载出错
- `IDLE`：未开始放映，或放映结束，无可加载内容

### 协议层
- command：
  - `USER_PLAYER_STATUS`
- event：
  - `USER_PLAYER_STATES`

### `USER_PLAYER_STATUS` payload 语义
至少包含：

- `status`
- `reported_at_ms`

可选包含：

- `position_seconds`
- `error_code`
- `error_message`

### 服务端处理方式
- 用户播放状态任意变化时，通过统一 command 上报
- 服务端更新该用户在 `room_video_runtime` 中的状态
- 然后向 room channel 广播**当前房间所有在线用户的全量播放状态**

### `USER_PLAYER_STATES` 语义
- 广播房间当前全量用户播放器状态
- 不替代 `PRESENCE`

---

## 十三、AUTO_PAUSE 与其他同步策略的最终结论

### 当前核心判断
实际上几种同步策略中，只有 `AUTO_PAUSE` 是需要服务端控制的。

服务端负责：
- 提供房间 authoritative playback（事实进度）
- 在 `AUTO_PAUSE` 策略下，根据用户状态聚合来自动 pause / play

前端负责：
- 根据服务端事实进度做本地同步
- 是否 seek / speed / manual 追赶属于用户端策略，后端当前忽略

### 因此最终房间级 `sync_policy`
只保留：
- `AUTO_PAUSE`
- `DISABLED`

其中：
- `AUTO_PAUSE`：服务端启用房间级 stall 聚合与自动 pause / 恢复
- `DISABLED`：服务端不做 auto pause 协调，但仍提供 authoritative playback，且不影响手动控制

---

## 十四、当前实现中关于 user_player_status 的关键设计点

> 注意：以下是当前目标设计和已接入方向，后续继续实现时请以最新代码状态核对，不要回退。

### 已确定要有的运行态内容
`room_video_runtime.py` 应维护：

- `user_player_states`
- `stalling_user_ids`
- `paused_by_stall`

### 已确定要有的辅助结果对象
建议在 runtime 中使用一个类似结果包（dataclass），用于返回：

- `user_player_states`
- `auto_playback`
- `auto_action`

其中：

- `user_player_states`：
  - 当前房间全量用户播放器状态
- `auto_playback`：
  - 若这次状态变化触发自动 pause/play，则为新的 authoritative playback state
- `auto_action`：
  - 表示这次是否触发了自动动作
  - 不建议用裸字符串，建议使用单独 enum，例如：
    - `AutoPlaybackAction.PLAY`
    - `AutoPlaybackAction.PAUSE`

### 当前 `AUTO_PAUSE` 行为要求
- `READY/IDLE/ERROR -> STALLING`
  - 若房间当前在播放且 `sync_policy == AUTO_PAUSE`
  - 则自动 pause
- `STALLING -> READY/IDLE/ERROR`
  - 若 stalling 集合清空，且这次 pause 是由 stall 引发
  - 则自动恢复 play

### `DISABLED` 模式
- 仍接收状态上报
- 仍广播 `USER_PLAYER_STATES`
- 但不做服务端 auto pause / 恢复

### `ROOM_VIDEO_SOURCE_SET` 成功后的副作用
无论是：
- type 变化
- 还是 type 不变但 value 变化

都统一视为一次新的 source replacement，并应：

1. 持久化 `selected_room_video_source_type`
2. 更新 runtime 当前 `room_video_source`
3. reset playback 到 paused + position 0
4. 清空当前房间全部 `user_player_states`
5. 广播：
   - `ROOM_VIDEO_SOURCE_SET`
   - `PLAYBACK_PAUSE`
   - `USER_PLAYER_STATES`

---

## 十五、当前 review 结论（供后续接手时参考）

### 已确认合理的点
- `room_video` 命名方向正确，较之前更清晰
- `RoomVideoCommandHandler` 作为当前主入口合理
- `ROOM_VIDEO_SOURCE_SET` 作为“完整 source replacement”语义自洽
- `RoomSettingsService.set_selected_room_video_source_type(...)` 这类封装方向正确
- `PRESENCE` 与 `USER_PLAYER_STATES` 语义边界明确，不应合并

### 需要继续注意的点
- 不要保留并使用旧的 `handlers/playback.py`
- 统一入口应为：
  - `handlers/room_video.py`
- 不要让 handler 直接穿透到 repo
- `ROOM_LEAVE` 对错 room_id 的行为后续可考虑从 silent no-op 改成显式报错
- 日志体系后续统一重构即可，当前先不零碎修

---

## 十六、scripts / migration 当前结论

### 1. 主入口
`scripts/migrates/migrate.py` 应确保接入：

- `migrate_room_settings.py`
- `migrate_room_join_request.py`

### 2. join request 迁移脚本命名
若当前存在：

- `migrate_room_join_request_request.py`

则这是命名冗余，建议统一为：

- `migrate_room_join_request.py`

### 3. 本轮 user_player_status 实现
本轮 user_player_status 相关工作是 **runtime / ws 层逻辑**，不涉及新增 DB schema；
除主入口脚本接线和命名整理外，通常不需要新增 migration。

---

## 十七、当前已知问题 / TODO LIST

### A. Realtime 核心待办
1. 继续检查并完成 `USER_PLAYER_STATUS` 主链闭环：
   - `constants.py`
   - `state.py`
   - `room_video_runtime.py`
   - `publisher.py`
   - `handlers/room_video.py`
   - `handlers/dispatcher.py`
   - `handlers/room.py`
   - `ws_router.py`

2. 确保 runtime 中已维护：
   - `user_player_states`
   - `stalling_user_ids`
   - `paused_by_stall`

3. 确保 `ROOM_ENTER` 的 snapshot 中带上：
   - `user_player_states`

4. 确保 `ROOM_LEAVE / 切房 / disconnect` 时会移除该用户的 player state，避免 stale stalling 卡住房间

5. 引入并使用：
   - `AutoPlaybackAction` enum
   替代裸字符串 `"play" / "pause"`

### B. 事件广播待办
6. 用户播放状态变化时统一广播：
   - `USER_PLAYER_STATES`

7. 若因状态变化触发自动 pause/play，则额外广播：
   - `PLAYBACK_PAUSE`
   - 或 `PLAYBACK_PLAY`

8. 后续补齐业务联动广播：
   - `ROOM_SETTINGS`
   - `ROOM_INFO`
   - `ROOM_MEMBERS`
   - `MESSAGE`
   - `NOTIFICATION`

### C. settings / source 相关待办
9. `ROOM_VIDEO_SOURCE_SET` 当前仍存在事务边界不够理想的问题：
   - settings 持久化先 commit
   - runtime 更新和 event 广播在后
   - 后续需考虑如何理顺为更干净的一条操作链

10. `selected_room_video_source_type` 继续统一表示：
   - 当前选中的 room video source type 持久化状态

### D. 命名继续收口待办
11. 若代码中仍残留以下旧命名，应继续替换：
   - `RoomMediaSourceType` → `RoomVideoSourceType`
   - `VideoSourceState` → `RoomVideoSourceState`
   - `video_source` → `room_video_source`
   - `get_video_source()` → `get_room_video_source()`
   - `set_video_source()` → `set_room_video_source()`

12. `PlaybackRuntimePolicy` 若仍存在，建议改名为：
   - `RoomVideoRuntimePolicy`
   不建议叫 `RoomVideoSyncPolicy`，因为其内部不仅包含 sync_policy，还包含 active_sync_permission

### E. 其他工程性待办
13. 增加 ws 关键日志（后续统一收口）：
   - auth timeout
   - room enter / leave
   - replaced session
   - playback control
   - user player status
   - disconnect / send failure cleanup

14. 后续视需要补：
   - owner / manager 查看房间内所有用户播放状态的展示逻辑（优先 ws 广播，不做 HTTP 主动查询）

15. 需要做最小 ws 联调测试：
   - `ROOM_VIDEO_SOURCE_SET`
   - `USER_PLAYER_STATUS: READY -> STALLING`
   - `USER_PLAYER_STATUS: STALLING -> READY`
   - `ROOM_LEAVE / disconnect` 时的自动恢复逻辑

---

## 十八、后续实现要求

后续继续实现或 review 时，请遵守以下要求：

- 优先基于**最新代码版本**判断，不要混入早期 zip 中的旧实现
- 若仓库中存在两套相似实现，优先保留当前主链，及时清理残留旧文件
- 任何命名调整，优先保持“room_video / playback / user_player_status”三层语义边界清晰
- 任何状态广播，继续保持：
  - 初始化走 `RoomSnapshot`
  - 增量走局部 state
- 先保证 realtime 主链闭环，再做日志统一、事务边界优化、联动广播扩展