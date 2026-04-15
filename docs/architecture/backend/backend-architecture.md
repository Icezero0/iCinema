# iCinema 后端架构设计书

版本：v1  
状态：Draft  
适用范围：`backend`

## 1. 文档定位

本文档描述 iCinema 当前重构后后端的架构设计、模块职责、关键调用链和协作约定，面向：

- 前端开发人员：理解 HTTP 与 WebSocket 的职责边界、房间与实时状态模型
- 后端开发人员：理解目录结构、分层规则、事务约定、运行时约束

## 2. 目标与范围

### 2.1 后端目标

iCinema 后端负责承载以下核心能力：

- 用户注册、登录、JWT 鉴权
- 用户资料与头像管理
- 房间创建、查询、修改、删除
- 房间成员关系与加入申请流程
- 房间消息发送与历史查询
- 图片、贴纸、头像等媒体资源管理
- 系统通知与工作流通知
- WebSocket 实时在线状态与播放同步

### 2.2 本文档范围

本文档覆盖：

- 目录结构
- 分层设计
- 核心模块职责
- HTTP / WS 调用链
- 事务与提交约定
- 运行时约束

本文档不覆盖：

- 前端页面结构
- 部署平台细节
- 多实例扩展设计

## 3. 技术选型

当前后端技术栈如下：

- Web 框架：FastAPI
- ORM：SQLAlchemy Async
- 数据库：SQLite
- 数据迁移：Alembic
- 鉴权：JWT
- 实时通信：WebSocket
- 测试：pytest

系统当前采用“模块化单体 + 单实例内存态实时服务”的架构。

## 4. 目录结构

`backend` 主要目录如下：

```text
backend/
  app/
    api/
    core/
    db/
    modules/
    realtime/
    main.py
  alembic/
  jobs/
  tests/
  scripts/
```

### 4.1 `app/main.py`

应用入口，负责：

- 创建 FastAPI 应用
- 注册生命周期
- 初始化 realtime 组件
- 挂载 HTTP 路由与 WS 路由
- 注册异常处理器

### 4.2 `app/core`

基础设施层，负责：

- 配置加载
- 数据库引擎与 session
- 启动初始化
- 安全能力
- 异常定义与统一错误返回
- 通用校验逻辑

### 4.3 `app/db`

数据库基础定义，负责：

- `Base` 声明
- 聚合所有 ORM model，供 Alembic 与应用初始化使用

### 4.4 `app/api`

HTTP 接口层，负责：

- 对外暴露 REST API
- 依赖注入
- 参数解析
- 调用各模块 service

### 4.5 `app/modules`

业务模块层，按领域拆分，当前包括：

- `auth`
- `users`
- `rooms`
- `messages`
- `notifications`
- `media`

### 4.6 `app/realtime`

WebSocket 与在线运行时层，负责：

- 连接鉴权
- 消息协议
- 连接注册与订阅
- 房间在线状态
- 房间播放运行时状态
- 实时事件广播
- REST 与 WS 的状态联动

### 4.7 `alembic`

数据库迁移目录。

### 4.8 `jobs`

后台任务目录，当前主要用于清理过期图片资源。

### 4.9 `tests`

测试目录，覆盖：

- API 测试
- 业务模块单元测试
- realtime 单元测试

## 5. 分层设计

## 5.1 总体分层

系统主要分为五层：

1. 接口层
2. 业务层
3. 数据访问层
4. 运行时实时层
5. 基础设施层

### 5.1.1 接口层

包括：

- HTTP Router
- WebSocket Router

职责：

- 接收请求
- 注入依赖
- 调用业务逻辑
- 返回标准响应

接口层尽量保持轻量，不承载复杂业务规则。

### 5.1.2 业务层

以各模块 `service.py` 为主，职责包括：

- 权限校验
- 业务规则判断
- 跨 repository 编排
- 组织响应对象

### 5.1.3 数据访问层

以各模块 `repository.py` 为主，职责包括：

- 查询数据库
- 持久化 ORM 对象
- 维护查询预加载策略

Repository 不负责业务规则。

### 5.1.4 运行时实时层

`realtime/` 是独立于数据库模型的一层运行时状态系统，职责包括：

- 维护连接
- 维护房间在线状态
- 维护房间播放状态
- 按 channel 广播事件

### 5.1.5 基础设施层

包括：

- 配置
- 数据库引擎
- 安全工具
- 异常体系
- 启动初始化

## 5.2 模块内结构

大部分业务模块遵循以下结构：

- `models.py`
- `schemas.py`
- `repository.py`
- `service.py`

说明：

- `models.py`：ORM 实体定义
- `schemas.py`：HTTP 输入输出模型
- `repository.py`：数据库读写
- `service.py`：业务规则与流程编排

`rooms` 模块由于职责较重，进一步拆分为子域：

- `room`
- `membership`
- `settings`
- `join_request`

## 6. 应用启动流程

应用启动入口为 `app/main.py`。

启动流程如下：

1. 读取配置
2. 创建 FastAPI 应用
3. 初始化 realtime 组件并写入 `app.state`
4. 注册 CORS
5. 注册异常处理器
6. 挂载公共资源路由
7. 挂载 `/api/v1` HTTP 路由
8. 挂载 `/ws` WebSocket 路由
9. 在生命周期启动阶段执行运行时初始化

运行时初始化包括：

- 确保数据目录存在
- 确保上传目录存在
- 运行 Alembic `upgrade head`

## 7. 核心模块设计

## 7.1 auth

职责：

- 登录
- 刷新 token
- 当前用户识别

核心实现：

- `AuthService`
- `get_current_user`
- `decode_token / create_access_token / create_refresh_token`

约定：

- HTTP 鉴权使用 Bearer token
- WebSocket 鉴权使用连接后 `auth` 消息中的 access token

## 7.2 users

职责：

- 查询当前用户信息
- 修改当前用户资料
- 上传头像
- 查询当前用户可进入的房间集合
- 查询用户列表与用户详情

特点：

- 用户头像不直接存在 `users` 表中，而是通过媒体资源体系维护
- 返回给前端的是 `avatar_url`，而不是底层文件路径
- 提供 `GET /api/v1/users/me/rooms` 作为“我的房间”聚合接口

`GET /api/v1/users/me/rooms` 当前支持：

- 分页：`page`、`page_size`
- 角色过滤：`role=owner|manager|member`

返回摘要字段包括：

- `id`
- `name`
- `owner_id`
- `owner`
- `is_public`
- `my_role`

该接口用于前端首页和“我的房间”列表，不要求前端通过“房间列表 + 成员列表”自行拼装用户可进入房间集合。

## 7.3 rooms

职责：

- 房间管理
- 成员关系管理
- 房间设置管理
- 入房申请与邀请审批

子域划分：

- `room`：房间本体
- `membership`：房间成员与角色
- `settings`：同步策略、主动控制权限等
- `join_request`：加入申请与邀请流

房间权限通过 `RoomRole + RoomPermission` 组合实现。

`join_request` 子域当前既支持：

- 房间内上下文接口：`/api/v1/rooms/{room_id}/join-requests`
- 全局审批中心接口：`/api/v1/join-requests`

其中全局接口用于前端审批中心、首页审批摘要等场景。

## 7.4 messages

职责：

- 创建房间消息
- 查询历史消息

特点：

- 消息内容采用结构化 JSON 存储在 `messages.content`
- 消息片段支持 `text / emoji / image / sticker`
- 图片和贴纸资源只保存资源 ID，返回时补充 URL

## 7.5 media

职责：

- 头像、图片、贴纸资源上传
- 文件落盘
- 媒体资源数据库记录维护
- 图片过期处理
- 贴纸库维护
- emoji 目录与最近使用记录

特点：

- 文件存在文件系统中
- 元数据存在数据库中
- 资源访问通过 `/avatar/{storage_key}`、`/image/{storage_key}`、`/sticker/{storage_key}` 完成

## 7.6 notifications

职责：

- 获取通知列表
- 未读计数
- 标记已读
- 工作流触发通知创建

特点：

- 通知变更后通常只通过 WS 推送“有更新”信号
- 详细通知列表仍由 HTTP 获取

## 7.7 realtime

职责：

- WebSocket 连接管理
- 协议解析与校验
- 房间在线状态维护
- 房间播放运行时维护
- 实时事件分发与广播

realtime 层内部主要组件：

- `ws_router.py`
- `manager.py`
- `publisher.py`
- `protocol.py`
- `handlers/`
- `room_presence.py`
- `room_video_runtime.py`
- `rest_sync.py`

## 8. 核心调用链

## 8.1 HTTP 调用链

典型调用链如下：

1. HTTP 请求进入 Router
2. Router 注入 `db`、`current_user` 等依赖
3. Router 调用模块 Service
4. Service 做权限校验与业务处理
5. Service 调用 Repository 访问数据库
6. Service commit 或返回结果
7. Router 返回 schema

典型示例：

- 创建房间：`rooms router -> RoomService -> RoomRepository + membership/settings`
- 发送消息：`messages router -> MessageService -> MessageRepository + MediaService`
- 标记通知已读：`notifications router -> NotificationService`
- 查询我的房间：`users router -> UserService -> RoomRepository`
- 查询审批中心列表：`room_join_request router -> RoomJoinRequestService -> membership/join_request repository`

## 8.2 WebSocket 调用链

典型调用链如下：

1. 客户端连接 `/ws`
2. 首先发送 `auth`
3. `ws_router` 为每条消息创建临时 DB session
4. `RealtimeMessageHandler` 解析 envelope
5. 分发给 `AuthHandler / HeartbeatHandler / RoomCommandHandler / RoomVideoCommandHandler`
6. handler 更新数据库或运行时状态
7. 通过 `RealtimePublisher` 广播事件

## 8.3 REST 与实时联动链

系统采用“HTTP 改事实，WS 推状态”的模式。

典型联动包括：

- 房间信息更新后，广播 `room_info`
- 房间设置更新后，广播 `room_settings`
- 消息创建后，广播 `message`
- 通知状态变更后，广播 `notification`
- 删除房间或移除成员后，通过 `rest_sync` 关闭在线会话

## 9. 数据模型概览

当前核心数据对象包括：

- `User`
- `Room`
- `RoomSettings`
- `RoomMember`
- `RoomJoinRequest`
- `Message`
- `Notification`
- `MediaAsset`
- `UserAvatarAsset`
- `UserStickerLibraryItem`
- `MessageResourceRef`
- `UserEmojiUsage`

这些对象可大致分为三类：

- 身份与关系数据：`User`、`Room`、`RoomMember`
- 内容与工作流数据：`Message`、`Notification`、`RoomJoinRequest`
- 资源数据：`MediaAsset` 及其关联表

## 10. HTTP 与 WebSocket 职责划分

## 10.1 HTTP 负责持久化业务数据

HTTP 主要用于：

- 注册登录
- 用户资料查询与修改
- 我的房间摘要查询
- 房间创建与查询
- 房间设置查询与修改
- 成员与审批管理
- 消息写入与历史分页
- 媒体资源上传与资源列表读取
- 通知列表与已读状态管理

## 10.2 WebSocket 负责实时状态与广播

WebSocket 主要用于：

- 连接鉴权
- 房间 presence
- 房间会话切换
- 播放状态控制
- 播放运行时状态广播
- 新消息实时推送
- 通知变更信号

## 10.3 数据拉取策略

当前系统采用以下策略：

- 结构化、需要分页、需要鉴权的持久化数据以 HTTP 为主
- 高频、小体积、运行时在线状态以 WebSocket 为主
- 部分 WS 事件只推送“数据已变化”的信号，前端再回源 HTTP 获取详情

典型聚合型 HTTP 读取接口包括：

- `GET /api/v1/users/me/rooms`
  用于直接返回当前用户创建或加入的房间摘要
- `GET /api/v1/join-requests`
  用于直接返回当前用户待审批、我发起或与我相关的 join request 列表

## 11. 事务与提交约定

这是当前后端的重要协作约定。

### 11.1 命名约定

- `xxx_in_tx()`：参与调用方事务，不自行 `commit`
- `_xxx()`：内部 helper，不作为事务提交边界，不自行 `commit`
- 其他公开 service 方法：通常自行 `commit`

### 11.2 适用原则

该约定用于帮助调用方快速判断：

- 当前方法是否会直接落库
- 当前方法是否适合被更大的业务流程复用

### 11.3 维护要求

新增 service 方法时，应尽量遵循上述约定，避免出现“方法名看起来像纯 helper，实际内部 commit”的情况。

## 12. 权限模型

## 12.1 认证

- HTTP 使用 Bearer token
- WS 使用连接后 `auth` 消息中的 access token

## 12.2 房间角色

当前房间角色包括：

- `owner`
- `manager`
- `member`

## 12.3 房间权限

房间权限包括但不限于：

- 查看房间
- 更新房间
- 删除房间
- 查看成员
- 邀请用户
- 审核加入申请
- 管理成员
- 管理管理员
- 查看消息
- 发送消息

权限判断由 service 层完成。

## 12.4 主动同步权限

房间设置中的 `active_sync_permission` 控制谁可以主动操作房间播放：

- `owner_only`
- `owner_and_manager`
- `all_members`

## 12.5 审批中心范围约定

全局接口 `GET /api/v1/join-requests` 当前支持以下 `scope`：

- `pending_for_me`
  返回当前用户可审批的待处理申请
- `created_by_me`
  返回当前用户发起的申请或邀请
- `all_related_to_me`
  返回与当前用户相关，或当前用户有审批权限可见的申请

当前接口还支持：

- 分页：`page`、`page_size`
- 过滤：`status`、`room_id`、`initiator_user_id`、`target_user_id`
- 排序：`sort_by=created_at|updated_at`

返回结构除 join request 本体外，还直接带有最少够用的关联对象：

- `room`
- `initiator`
- `target`
- `room_action_by`

## 13. 实时运行时设计

## 13.1 连接管理

`RealtimeManager` 负责维护：

- `connections`
- `user_connections`
- `channel_connections`

每个 WS 连接在鉴权成功后会得到唯一 `connection_id`。

## 13.2 Channel 模型

当前 channel 分为两类：

- 用户级 channel：`user:{user_id}`
- 房间级 channel：`room:{room_id}`

作用：

- 用户级 channel 用于通知用户本人的通知变化
- 房间级 channel 用于广播房间级实时事件

## 13.3 Presence 模型

`RoomPresenceService` 维护：

- 房间内在线用户
- 用户在房间中的有效连接
- 当前连接的 `active_room_id`

当前约束：

- 单个连接同一时刻只能激活一个房间
- 同一用户在同一房间只保留一个有效连接

## 13.4 房间播放运行时

`RoomVideoRuntimeService` 维护：

- 当前房间视频源
- 当前房间播放状态
- 每个用户的播放器状态
- stalling 用户集合
- 自动暂停/恢复的 hold reason

这些状态均保存在内存中，不持久化到数据库。

## 14. 文件存储与媒体约定

## 14.1 存储方式

媒体采用“文件系统 + 数据库元数据”模式：

- 文件内容存磁盘
- 元数据存数据库

### 14.2 资源类型

当前资源类型包括：

- avatar
- image
- sticker
- video

其中 `video` 类型已在枚举中预留，但当前 HTTP 上传与公共访问主要覆盖 avatar / image / sticker。

### 14.3 访问路径

公共资源通过以下路由访问：

- `/avatar/{storage_key}`
- `/image/{storage_key}`
- `/sticker/{storage_key}`

### 14.4 图片过期策略

- 图片资源当前有逻辑过期时间
- 资源访问时会做 lazy expire
- 后台任务会定期清理已过期图片文件

## 15. 错误模型

系统定义统一业务异常 `AppError` 体系。

当前主要错误码包括：

- `bad_request`
- `not_found`
- `unauthorized`
- `forbidden`
- `conflict`

HTTP 返回格式：

```json
{
  "error": {
    "code": "forbidden",
    "message": "You do not have permission to perform this action"
  }
}
```

WS 错误格式见 `ws-protocol.md`。

## 16. 测试策略

当前测试主要分为三层：

- API 测试：验证 HTTP 接口行为
- 模块单元测试：验证 service / repository 规则
- realtime 单元测试：验证 WS 协议、presence、播放同步、REST 联动

维护要求：

- 新增重要 HTTP 行为时，优先补 API 测试
- 新增重要实时逻辑时，优先补 realtime 测试
- 影响跨模块联动的改动，应补一条端到端风格的行为测试

## 17. 运行时约束与非目标

## 17.1 单实例约束

当前 realtime 在线状态和播放运行时状态保存在进程内存中，系统当前面向单实例运行。

## 17.2 非多房间订阅模型

当前一个连接只维护一个激活房间会话，不支持一个连接同时持有多个房间在线会话。

## 17.3 非事件溯源模型

当前 realtime 事件不提供持久化回放、断点续传、事件重放能力，客户端应以最新状态为准。

## 17.4 非分布式事务模型

文件系统写入、数据库写入、实时广播之间不是分布式原子事务，系统通过代码约定、异常处理和补充测试来保证整体一致性。

## 18. 面向前后端协作的约定

## 18.1 前端协作约定

- 持久化业务数据优先从 HTTP 获取
- 运行时在线状态优先从 WS 获取
- 收到 `room_info / room_settings / room_members / notification` 等信号型事件后，前端应主动回源 HTTP 拉最新数据
- 收到 `session_closed` 后应立即清理对应房间本地状态

在接口使用上，建议优先采用以下聚合接口而不是前端自行拼装：

- “我的房间”使用 `GET /api/v1/users/me/rooms`
- 审批中心与审批摘要使用 `GET /api/v1/join-requests`

## 18.2 后端协作约定

- Router 尽量保持薄
- 权限判断放在 service 层
- Repository 不承载业务规则
- 新增 service 方法时遵守提交命名约定
- 新增影响在线状态的 HTTP 接口时，需同时考虑是否补充 realtime 广播或会话清理

新增聚合查询接口时，优先遵循以下原则：

- 在 service 层定义明确的查询语义，而不是把复杂拼装留给前端
- 在 repository 层完成分页、排序和主要过滤
- 返回结构尽量直接带前端渲染所需的最小关联信息，减少 N+1 HTTP 请求

## 18.3 文档协作约定

后端接口与协议文档当前分为两部分：

- HTTP：`docs/architecture/backend/openapi.json`
- WebSocket：`docs/architecture/backend/ws-protocol.md`

当后端改动影响接口或实时协议时，应同步更新对应文档。

## 19. 后续维护建议

在当前架构不大改的前提下，后续维护优先事项建议为：

1. 保持 HTTP 与 WS 文档同步
2. 补齐关键业务日志
3. 为跨 REST / realtime 联动补充测试
4. 保持命名约定与模块边界一致

本文档的重点不是约束未来演进方向，而是帮助团队在当前实现基础上稳定协作与维护。
