# iCinema Front New TODO List

## 目标

当前 `front_new` 已完成：

- App shell（layout / theme / i18n / base ui）
- Auth 模块
- Profile 模块
- Notifications 模块基础能力

下一阶段目标不是继续零散补页面，而是把 iCinema 的核心主链路完整迁入新架构：

`登录 -> 房间列表 -> 进入房间 -> 消息/成员/设置 -> WebSocket 实时 -> 同步观影`

---

## 总体原则

- 继续坚持 `feature-oriented + design-system-first`
- 不直接平移旧 `frontend/src/views/Home.vue` 和 `frontend/src/views/Room.vue`
- 先稳定 HTTP 页面结构与 store 边界，再接入 WebSocket
- WebSocket 只负责实时状态和变更信号，完整数据优先回源 HTTP
- 旧前端的 `cookie + sessionStorage + 页面内 fetch` 方案不要带回新前端

---

## Phase 1: Room Domain HTTP 基础层

目标：先把房间域从“只有零碎 API”补到“能支撑页面开发”。

### API 层

- [ ] 扩展 `src/infra/api/rooms.api.ts`
- [ ] 补齐 `getRooms`
- [ ] 补齐 `createRoom`
- [ ] 补齐 `patchRoom`
- [ ] 补齐 `deleteRoom`
- [ ] 补齐 `getRoomMembers`
- [ ] 补齐 `applyRoomJoinRequest`
- [ ] 补齐 `inviteRoomJoinRequest`
- [ ] 补齐 `removeRoomMember`
- [ ] 补齐 `getRoomJoinRequests`
- [ ] 新增 `src/infra/api/messages.api.ts`
- [ ] 补齐 `getRoomMessages`
- [ ] 补齐 `createRoomMessage`
- [ ] 视情况补 `src/infra/api/room-settings.api.ts`，承接 `/rooms/{room_id}/settings`

### 类型层

- [ ] 基于 `openapi.json` 校准房间、成员、消息、设置相关类型
- [ ] 不再扩散手写 `any` 响应结构
- [ ] 明确 `RoomResponse / RoomMemberResponse / MessageResponse` 的前端领域映射

---

## Phase 2: Store 与 Feature 边界

目标：在进入页面开发前，先确定状态管理边界，避免后面重复拆分。

### 建议新增 store

- [ ] `src/stores/rooms.store.ts`
- [ ] `src/stores/room-detail.store.ts`
- [ ] `src/stores/messages.store.ts`

### store 职责建议

- `rooms.store`
  - [ ] 房间列表
  - [ ] 创建房间
  - [ ] 公共房间 / 我的房间筛选
  - [ ] 列表分页或 load more

- `room-detail.store`
  - [ ] 当前房间信息
  - [ ] 成员列表
  - [ ] join requests
  - [ ] room settings
  - [ ] 当前用户在房间内的权限

- `messages.store`
  - [ ] 历史消息列表
  - [ ] 分页加载
  - [ ] 发送消息
  - [ ] 后续承接实时消息追加

### 实体缓存

- [ ] 继续复用 `entities.store`
- [ ] 确认用户 / 房间 hydration 的触发点
- [ ] 避免页面内重复查用户、重复查房间

---

## Phase 3: Home 重建

目标：替换旧前端 `Home.vue` 的大页面逻辑，但拆成清晰模块。

### 页面结构

- [ ] 重做 `src/pages/home/HomePage.vue`
- [ ] 将页面拆成 feature 组件，而不是继续堆进单文件

### 建议组件

- [ ] `features/rooms/home/MyRoomsSection.vue`
- [ ] `features/rooms/home/PublicRoomsSection.vue`
- [ ] `features/rooms/home/CreateRoomDialog.vue`
- [ ] `features/rooms/home/RoomListItem.vue`

### 页面能力

- [ ] 展示“我的房间”
- [ ] 展示“公共房间”
- [ ] 创建房间
- [ ] 申请加入公共房间
- [ ] 已加入房间可直接进入
- [ ] 与 Header unread badge 保持联动

### Layout / 导航补全

- [ ] 补全 `AppSidebar.vue`
- [ ] 增加实际导航入口，而不是占位链接
- [ ] 统一首页、通知页、资料页的导航体验

---

## Phase 4: Room Page 骨架先落地

目标：先做“HTTP 可用版房间页”，不要一开始就把实时播放和聊天全部揉进去。

### 路由

- [ ] 新增房间详情路由，例如 `/rooms/:id`
- [ ] 明确该路由归属 `AppLayout`

### 页面结构

- [ ] 新增 `src/pages/room/RoomPage.vue`
- [ ] 页面只负责组合，不直接承载所有业务

### 建议组件

- [ ] `features/room/header/RoomHeader.vue`
- [ ] `features/room/members/RoomMembersPanel.vue`
- [ ] `features/room/settings/RoomSettingsPanel.vue`
- [ ] `features/room/messages/RoomMessagesPanel.vue`
- [ ] `features/room/video/RoomVideoSourcePanel.vue`

### 第一阶段只做 HTTP 能力

- [ ] 房间基础信息读取
- [ ] 成员列表读取
- [ ] 房间设置读取与修改
- [ ] join request 列表查看
- [ ] 历史消息分页读取
- [ ] 发送消息 HTTP 提交

---

## Phase 5: Messages Feature 正式落地

目标：把 `Notification` 和 `Message` 在新前端彻底分离。

### 能力范围

- [ ] 房间消息列表
- [ ] 输入框与发送流程
- [ ] 历史消息分页
- [ ] 文本消息优先
- [ ] 预留 emoji / image / sticker 的消息片段扩展位

### UI / 交互要求

- [ ] 消息列表滚动行为稳定
- [ ] 新消息追加时不破坏用户查看历史的位置
- [ ] 输入框和发送按钮状态明确
- [ ] 保持与 Notifications 不同的视觉语义

### 数据边界

- [ ] Message 只出现在 Room feature 下
- [ ] Notification page 不承担聊天职责

---

## Phase 6: WebSocket 基础设施重做

目标：不要复用旧前端松散的 WS 处理方式，直接按后端新协议重做。

后端协议见：

- `docs/architecture/backend/ws-protocol.md`

### 重构 `src/infra/realtime/wsClient.ts`

- [ ] 支持连接建立
- [ ] 支持认证握手 `auth`
- [ ] 支持 `heartbeat`
- [ ] 支持统一 envelope 解析
- [ ] 支持 `command` 发送
- [ ] 支持 `request_id -> ack/error` 匹配
- [ ] 支持事件订阅与退订
- [ ] 支持断线重连
- [ ] 支持 token 失效后的统一降级处理

### 建议新增

- [ ] `src/infra/realtime/wsProtocol.ts`
- [ ] `src/infra/realtime/roomRealtimeService.ts`

### 页面不应直接做的事

- [ ] 不在页面里手拼 WS 消息结构
- [ ] 不在页面里自己维护 request_id 映射
- [ ] 不在页面里直接区分 `ack / event / error`

---

## Phase 7: 房间实时能力接入

目标：在页面骨架稳定后，再把实时行为分层接进来。

### 第一批实时能力

- [ ] `room_enter`
- [ ] `room_leave`
- [ ] `message` event 追加消息
- [ ] `room_members` signal 后回源 HTTP 刷新成员
- [ ] `room_info` signal 后回源 HTTP 刷新房间信息
- [ ] `notification` signal 后刷新 unread count / notifications list
- [ ] `session_closed` 统一清理本地 room state

### 第二批实时能力

- [ ] `room_user_presence`
- [ ] 在线成员状态展示
- [ ] 用户进入 / 离开动画或提示

---

## Phase 8: 同步观影能力回归

目标：恢复 iCinema 的核心特色，但建立在新架构上，而不是回到旧 `Room.vue` 模式。

### 视频相关模块

- [ ] `features/room/video/RoomVideoPlayer.vue`
- [ ] `features/room/video/RoomPlaybackControls.vue`
- [ ] `features/room/video/useRoomPlayback.ts` 或同等抽象

### WebSocket 命令接入

- [ ] `room_video_source_set`
- [ ] `playback_play`
- [ ] `playback_pause`
- [ ] `playback_seek`
- [ ] `user_player_status`

### 运行时状态

- [ ] 房间视频源状态
- [ ] 房间播放状态
- [ ] 用户播放器状态聚合
- [ ] stalling / ready / error 展示

### 策略层

- [ ] 处理 `sync_policy`
- [ ] 处理 `active_sync_permission`
- [ ] 对 `session_closed`、被移出房间、房间删除给出明确反馈

---

## Phase 9: Mobile 与 UX 收尾

目标：在新架构稳定后补齐移动端体验，而不是提前在业务混乱时做大量响应式微调。

### 需要完成

- [ ] Home 页移动端布局
- [ ] Room 页移动端布局
- [ ] Header / Sidebar 在移动端的交互方案
- [ ] 消息区滚动与输入法弹起适配
- [ ] 视频区域与控制区域在小屏下的层次关系

### 设计要求

- [ ] 继续沿用当前 design system tokens
- [ ] 不回退到旧前端那种页面内散落样式变量
- [ ] 不把移动端逻辑塞成一整个超大组件

---

## 推荐执行顺序

按优先级，建议严格按下面顺序推进：

1. [ ] 补齐 room / message / settings API 层
2. [ ] 定义 rooms.store / room-detail.store / messages.store
3. [ ] 重做 HomePage 与房间列表能力
4. [ ] 新增 `/rooms/:id` 路由与 RoomPage 骨架
5. [ ] 完成成员、设置、历史消息的 HTTP 页面
6. [ ] 重做 wsClient，接入后端统一协议
7. [ ] 接入房间实时消息、presence、signal refresh
8. [ ] 接入视频源和播放同步
9. [ ] 最后做移动端打磨和交互收尾

---

## 当前不建议做的事

- [ ] 不要把旧 `frontend` 的 `Home.vue` 整页复制进来
- [ ] 不要把旧 `frontend` 的 `Room.vue` 整页复制进来
- [ ] 不要先做复杂动画再补数据流
- [ ] 不要先做“播放器全量重构”再把房间 HTTP 骨架立起来
- [ ] 不要让 WebSocket 成为页面状态的唯一来源

---

## 里程碑定义

### Milestone A

- [ ] 登录后可以进入新首页
- [ ] 可以查看房间列表
- [ ] 可以创建房间
- [ ] 可以申请加入房间

### Milestone B

- [ ] 可以进入房间详情页
- [ ] 可以看成员、改设置、看历史消息、发消息

### Milestone C

- [ ] WebSocket 稳定连接
- [ ] 实时消息和成员变化可用

### Milestone D

- [ ] 播放源切换、播放、暂停、seek 同步可用
- [ ] iCinema 核心同步观影体验回归

