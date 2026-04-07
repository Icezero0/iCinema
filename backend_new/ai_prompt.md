# iCinema 后端重构（backend_new）继承 Prompt

你是我的 iCinema 后端重构协作助手，继续基于以下技术栈推进 `backend_new/` 项目开发：

- FastAPI
- SQLAlchemy async
- SQLite
- JWT
- WebSocket / realtime

---

## 一、项目当前阶段

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

## 二、全局约定

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

## 三、Room Domain 当前结论

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
- 这是一个**持久化设置状态**
- `room_video` 指在 room 中进行同步观影的对象影片
- `media` 指系统 media 模块管理的所有媒体资源文件，包括 image / emoji / video
- 这个字段不是“允许类型约束”，而是“当前选中的 type 持久化状态”
- `PLAYBACK_SOURCE_SET` 时应同步更新该字段

##### `sync_policy`
房间级、服务端负责的同步策略当前只保留：

- `AUTO_PAUSE`
- `DISABLED`

语义：
- `AUTO_PAUSE`：服务端根据房间内用户播放状态（尤其 `STALLING`）进行自动 pause / 自动恢复
- `DISABLED`：关闭服务端 auto pause 协调，但不影响手动 `play/pause/seek/source_set`

说明：
- `AUTO_SEEK / AUTO_SPEED / MANUAL` 不再属于房间级后端 `sync_policy`
- 这些应视为前端 / 用户侧的本地追赶策略，后端暂时可忽略其具体实现

##### `active_sync_permission`
- 不废除
- 它与 RBAC 的关系是：**基于 room role 的可配置控制阈值**
- 仍用于限制主动控制命令：
  - `PLAYBACK_SOURCE_SET`
  - `PLAYBACK_PLAY`
  - `PLAYBACK_PAUSE`
  - `PLAYBACK_SEEK`
- 不应该限制用户自己的播放状态上报 command

### 3. RoomService / RoomSettingsService
- 已解决递归调用问题
- `RoomService` 与 `RoomSettingsService` 不再互相实例化
- 现在通过 repo + membership service 自行完成检查与兜底补建

### 4. DB / migration
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

## 四、Realtime / WebSocket 当前设计

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

---

## 五、Realtime 当前分层与命名

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
  - `playback.py`

### 当前职责划分
- `manager`：只管理 websocket 连接、订阅、publish，不承载 room 业务语义
- `room_presence`：维护房间在线态（presence）
- `room_video_runtime`：维护房间 video source / playback / 用户播放状态等运行态
- `publisher`：把业务结果翻译成 ws event，并调用 publish
- `dispatcher`：顶层消息分发和错误包装
- `ws_router`：连接生命周期管理
- `state.py`：realtime runtime state model

---

## 六、room_presence 当前结论

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

### 当前已知问题
- send 失败导致 stale presence 的问题，已通过调整 `manager.disconnect()` 只清理 manager 自己状态、不碰 `active_room_id` 的方向修正
- `ws_router.finally -> presence_service.handle_disconnect()` 仍是 room presence 清理兜底点

---

## 七、room_video_runtime 当前结论

### 当前已实现的大方向
`room_video_runtime` 是房间级视频运行态服务，负责：

- `video_source`
- `playback`

并且后续应继续扩展为还负责：

- 房间内每个在线用户的播放状态
- stalling 用户集合
- 是否因 stall 自动暂停等房间级同步辅助状态

### 当前不负责：
- websocket 发送
- room presence
- 权限判断
- DB 持久化（除了上层 handler 调用 settings service 持久化 `selected_room_video_source_type`）

---

## 八、当前已确定的重要 realtime 规则

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

## 九、当前 state 设计

`state.py` 当前核心模型包括：

- `PresenceState`
- `VideoSourceState`
- `PlaybackState`
- `RoomSnapshot`

后续应扩展增加：

- `RoomUserPlaybackState`
- 房间全量用户播放状态 payload（如有需要）

### 语义约定
- `RoomSnapshot`：用于 `ROOM_ENTER` 初始化全量快照
- `PRESENCE`：只发 `PresenceState`
- `PLAYBACK_SOURCE_SET`：只发 `VideoSourceState`
- `PLAYBACK_PLAY / PAUSE / SEEK`：只发 `PlaybackState`
- 用户播放状态变化后，单独广播“房间全量用户播放状态”

---

## 十、当前 playback / source 主动控制命令权限

### 主动控制命令
这些命令仍然受 `active_sync_permission` 控制：

- `PLAYBACK_SOURCE_SET`
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

### 当前已明确去掉的错误逻辑
- 不再使用 `sync_policy` 限制手动 `play / pause / seek / source_set`
- `sync_policy = disabled` 不代表禁用手动同步控制
- `selected_room_video_source_type` 不是“允许类型限制”，而是“当前选中的 source type 持久化状态”

---

## 十一、用户播放状态模型（已讨论确定）

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

### 当前结论
- 不再使用 `STALL_BEGIN / STALL_END` 这种动作型 command
- 改为一个统一的状态上报型 command，例如：
  - `PLAYBACK_STATUS_REPORT`
- payload 中携带：
  - `status`
  - `reported_at_ms`
  - 可选 `position_seconds`
  - 可选 `error_code / error_message`

### 服务端处理方式
- 用户播放状态任意变化时，通过一个统一 command 上报
- 服务端更新该用户在 `room_video_runtime` 中的状态
- 然后向 room channel 广播**当前房间所有在线用户的全量播放状态**

### 广播事件
建议新增统一 event，例如：

- `PLAYBACK_USER_STATES`

payload 为房间当前全量用户播放状态

---

## 十二、AUTO_PAUSE 与其他同步策略的最终结论

### 当前核心判断
实际上几种同步策略中，只有 `AUTO_PAUSE` 是需要服务端控制的。

服务端负责：
- 提供房间 authoritative playback（事实进度）
- 在 `AUTO_PAUSE` 策略下，根据用户状态聚合来自动 pause / play

前端负责：
- 根据服务端事实进度做本地同步
- 是否 seek / speed / manual 追赶属于用户端策略，后端当前可忽略

### 因此最终房间级 `sync_policy`
只保留：
- `AUTO_PAUSE`
- `DISABLED`

其中：
- `AUTO_PAUSE`：服务端启用房间级 stall 聚合与自动 pause / 恢复
- `DISABLED`：服务端不做 auto pause 协调，但仍提供 authoritative playback，且不影响手动控制

---

## 十三、当前已知问题 / TODO LIST

下面是接下来需要继续完成的工作清单。

### A. Realtime 核心待办
1. 统一新增状态上报 command：
   - `PLAYBACK_STATUS_REPORT`

2. 统一新增房间全量用户播放状态 event：
   - `PLAYBACK_USER_STATES`

3. 扩展 `state.py`：
   - 增加 `RoomUserPlaybackState`
   - 增加房间全量用户播放状态 payload model

4. 扩展 `room_video_runtime.py`：
   - 维护 `user_playback_states`
   - 维护 stalling 用户集合
   - 维护“是否因 stall 自动暂停”的标记
   - 处理状态变化时的聚合逻辑

5. 在 `handlers/playback.py` 中新增：
   - `PLAYBACK_STATUS_REPORT` 的处理逻辑

6. 该 command 只要求：
   - 已认证
   - 已 enter room
   - 是房间成员
   - **不受** `active_sync_permission` 限制

7. `AUTO_PAUSE` 真正接入 realtime：
   - `READY/IDLE/ERROR -> STALLING`
     - 若房间当前在播放且 `sync_policy == AUTO_PAUSE`
     - 则自动 pause
   - `STALLING -> READY/IDLE/ERROR`
     - 若 stalling 集合清空，且这次 pause 是由 stall 引发
     - 则自动恢复 play

8. `DISABLED` 模式下：
   - 仍接收状态上报
   - 仍广播房间全量用户播放状态
   - 但不做服务端 auto pause / 恢复

### B. 事件广播待办
9. 为用户播放状态新增 publisher 方法：
   - `publish_playback_user_states(...)`

10. 用户播放状态变化时统一广播房间全量状态

11. 后续补齐业务联动广播：
   - `ROOM_SETTINGS`
   - `ROOM_INFO`
   - `ROOM_MEMBERS`
   - `MESSAGE`
   - `NOTIFICATION`

### C. settings / source 相关待办
12. `PLAYBACK_SOURCE_SET` 当前存在事务边界不够理想的问题：
   - settings 持久化先 commit
   - runtime 更新和 event 广播在后
   - 后续需考虑如何理顺为更干净的一条操作链

13. `selected_room_video_source_type` 已经明确为“当前选中的 source type 持久化状态”，后续所有 realtime 读取 settings 的地方继续统一使用该字段

### D. DB / migration 待办
14. 确认 `room_settings` 的 migration 已对齐当前设计：
   - `selected_room_video_source_type`
   - `sync_policy` 只允许 `auto_pause / disabled`
   - 旧值 `auto_seek / auto_speed` 迁移为 `disabled`

### E. 其他工程性待办
15. 增加 ws 关键日志：
   - auth timeout
   - room enter / leave
   - replaced session
   - playback control
   - playback status report
   - disconnect / send failure cleanup

16. 后续视需要补：
   - owner / manager 查看房间内所有用户播放状态的展示逻辑（优先 ws 广播，不做 HTTP 主动查询）

---

## 十四、后续协作要求

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
- 如果修改 realtime，请优先检查：
  - protocol / manager / room_presence / room_video_runtime / publisher / handlers / ws_router 是否一致
  - 是否仍符合“初始化走 RoomSnapshot，增量走局部 state”的原则
- 主动控制命令继续受 `active_sync_permission` 控制
- 用户播放状态上报 command 不受 `active_sync_permission` 限制
- `sync_policy` 只用于服务端 `AUTO_PAUSE` 逻辑，不再限制手动 playback control

---

如果要继续推进，下一步应优先从：

**`PLAYBACK_STATUS_REPORT + PLAYBACK_USER_STATES + room_video_runtime 的用户状态聚合与 AUTO_PAUSE`**

这一条线开始。