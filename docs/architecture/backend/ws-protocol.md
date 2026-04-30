# iCinema WebSocket 协议文档

版本：v1  
状态：Draft  
适用范围：`backend_new/app/realtime`

## 1. 文档目标

本文档描述 iCinema 当前后端实现中的 WebSocket 协议约定，面向：

- 前端开发人员：用于实现连接、鉴权、入房、播放控制、实时消息处理
- 后端开发人员：用于维护协议兼容性、事件命名与消息结构

## 2. 连接信息

### 2.1 Endpoint

- WebSocket 地址：`/ws`

### 2.2 认证方式

- 连接建立后，客户端必须先发送一条 `auth` 消息
- 服务端不依赖 WebSocket Header Bearer 鉴权
- 鉴权超时时间由后端配置 `WS_AUTH_TIMEOUT_SECONDS` 控制，默认 10 秒

### 2.3 连接生命周期

连接生命周期如下：

1. 客户端连接 `/ws`
2. 服务端接受连接
3. 客户端发送 `auth` 消息
4. 鉴权通过后，客户端可继续发送 `heartbeat` 与 `command`
5. 连接断开后，服务端会清理在线状态、房间订阅状态和播放运行时状态

## 3. 消息总结构

所有消息均采用统一 envelope：

```json
{
  "v": 1,
  "type": "auth | heartbeat | command | event | error | ack",
  "payload": {}
}
```

字段说明：

- `v`：协议版本，当前固定为 `1`
- `type`：消息类型
- `payload`：消息体，不同类型对应不同结构

## 4. 客户端到服务端消息

### 4.1 auth

用于连接后鉴权。

```json
{
  "v": 1,
  "type": "auth",
  "payload": {
    "token": "<access_token>"
  }
}
```

说明：

- `token` 必须为 HTTP 侧登录得到的 `access_token`
- `refresh_token` 不能用于 WS 鉴权
- 同一连接重复发送 `auth`，服务端会返回普通 `ack`，不会重复创建连接上下文

### 4.2 heartbeat

用于连接保活。

```json
{
  "v": 1,
  "type": "heartbeat",
  "payload": {
    "action": "ping"
  }
}
```

说明：

- 当前客户端只允许发送 `ping`
- 服务端收到后会回 `pong`

### 4.3 command

用于发送业务命令。

```json
{
  "v": 1,
  "type": "command",
  "payload": {
    "request_id": "req-123",
    "action": "room_enter",
    "data": {}
  }
}
```

字段说明：

- `request_id`：客户端生成的请求唯一标识，服务端会在 `ack` 或 `error` 中带回
- `action`：命令动作
- `data`：动作参数

## 5. 服务端到客户端消息

### 5.1 ack

表示请求处理成功。

```json
{
  "v": 1,
  "type": "ack",
  "payload": {
    "request_id": "req-123",
    "data": {}
  }
}
```

说明：

- `auth` 成功时也会返回 `ack`
- 部分命令的 `ack.data` 为空
- 部分命令会返回快照或最新状态

### 5.2 event

表示服务端主动推送事件。

```json
{
  "v": 1,
  "type": "event",
  "payload": {
    "event": "message",
    "data": {}
  }
}
```

### 5.3 error

表示请求处理失败或 payload 非法。

```json
{
  "v": 1,
  "type": "error",
  "payload": {
    "request_id": "req-123",
    "code": "bad_request",
    "reason": "room_id_is_required",
    "message": "room_id is required",
    "details": null
  }
}
```

字段说明：

- `code`：粗粒度错误类别，用于区分鉴权、权限、参数、资源不存在等大类。
- `reason`：稳定的 snake_case 业务原因，前端应优先用它作为 i18n key。
- `message`：后端兜底文案，主要用于开发调试或前端未配置 i18n 时展示。
- `details`：可选结构化细节。payload 校验失败时会包含 `errors` 列表；普通业务错误通常为 `null`。

WS 错误 `reason` 与 HTTP 错误共用后端登记表 `app.core.error_reasons.ErrorReason`。新增 WS 业务错误时，应先登记 `ErrorReason`，再在 handler 或 service 中引用，避免前后端 i18n key 漂移。

完整登记表见 `error-reasons.md`。

### 5.4 heartbeat pong

```json
{
  "v": 1,
  "type": "heartbeat",
  "payload": {
    "action": "pong"
  }
}
```

## 6. 消息类型枚举

### 6.1 顶层 `type`

- `auth`
- `heartbeat`
- `command`
- `event`
- `error`
- `ack`

### 6.2 `command.action`

- `room_enter`
- `room_leave`
- `room_presence_get`
- `room_video_runtime_get`
- `playback_pause`
- `playback_play`
- `playback_seek`
- `room_video_source_set`
- `user_resource_status`

### 6.3 `event`

- `notification`
- `room_info`
- `room_settings`
- `room_members`
- `room_user_presence`
- `session_closed`
- `message`
- `playback_pause`
- `playback_play`
- `playback_seek`
- `room_video_source_set`
- `user_resource_states`

### 6.4 `error.code`

- `unauthorized`
- `forbidden`
- `not_found`
- `bad_request`
- `invalid_payload`
- `internal_error`

## 7. 核心数据结构

### 7.1 RoomSnapshot

用于 `room_enter` 成功后的 `ack.data`。

```json
{
  "room_id": 1,
  "present_user_ids": [1, 2],
  "room_video_source": {
    "room_id": 1,
    "source_type": "external_url",
    "external_url": "https://example.com/video.m3u8",
    "file_hash": null
  },
  "playback": {
    "room_id": 1,
    "status": "paused",
    "position_seconds": 0,
    "anchor_ts_ms": 1710000000000,
    "playback_rate": 1.0
  },
  "user_resource_states": {
    "room_id": 1,
    "user_resource_states": []
  }
}
```

字段说明：

- `present_user_ids`：当前房间在线用户 ID 列表
- `room_video_source`：当前房间视频源状态，可为空
- `playback`：当前房间播放状态，可为空
- `user_resource_states`：房间内用户资源健康状态聚合

### 7.2 PresenceState

用于 `room_user_presence` 事件。

```json
{
  "room_id": 1,
  "present_user_ids": [1, 2, 3]
}
```

### 7.3 RoomVideoSourceState

用于 `room_video_source_set` 相关响应与事件。

```json
{
  "room_id": 1,
  "source_type": "external_url",
  "external_url": "https://example.com/video.mp4",
  "file_hash": null
}
```

字段说明：

- `source_type`：`external_url` 或 `local_file`
- `external_url`：外部视频地址
- `file_hash`：本地文件哈希，当前仅在 `local_file` 模式下使用

### 7.4 PlaybackState

用于播放、暂停、拖拽相关响应与事件。

```json
{
  "room_id": 1,
  "status": "playing",
  "position_seconds": 32.5,
  "anchor_ts_ms": 1710000000000,
  "playback_rate": 1.0
}
```

字段说明：

- `status`：`playing` 或 `paused`
- `position_seconds`：参考播放进度
- `anchor_ts_ms`：客户端用于估算实际播放位置的时间锚点
- `playback_rate`：播放速度

### 7.5 UserResourceStatesState

用于聚合房间内各用户的资源健康状态。

```json
{
  "room_id": 1,
  "user_resource_states": [
    {
      "room_id": 1,
      "user_id": 2,
      "status": "ready",
      "reported_at_ms": 1710000000000,
      "position_seconds": 31.9,
      "error_code": null,
      "error_message": null
    }
  ]
}
```

单个用户状态 `status` 取值：

- `ready`
- `stalling`
- `error`

说明：

- 该状态描述资源加载健康情况，不描述播放器播放态。
- 前端播放器播放态由前端自行维护为 `idle` / `paused` / `playing`。
- 旧的资源状态 `idle` 已废弃，后端不再接受。

## 8. 命令说明

### 8.1 `room_enter`

进入房间并订阅该房间实时事件。

请求：

```json
{
  "v": 1,
  "type": "command",
  "payload": {
    "request_id": "req-room-enter",
    "action": "room_enter",
    "data": {
      "room_id": 1
    }
  }
}
```

成功响应：

- 返回 `ack`
- `ack.payload.data` 为 `RoomSnapshot`

服务端行为：

- 校验房间存在
- 校验当前用户是房间成员
- 若当前连接已在其他房间，会先离开旧房间
- 若同一用户在该房间已有旧连接，旧连接会收到 `session_closed`
- 新连接会订阅该房间的 room channel
- 其他在线成员会收到新的 `room_user_presence`

### 8.2 `room_leave`

离开当前房间。

请求：

```json
{
  "v": 1,
  "type": "command",
  "payload": {
    "request_id": "req-room-leave",
    "action": "room_leave",
    "data": {
      "room_id": 1
    }
  }
}
```

成功响应：

- 返回 `ack`
- `ack.payload.data` 为空

服务端行为：

- 清理该连接的房间 presence
- 更新聚合资源健康状态
- 必要时触发自动恢复播放
- 向其他成员广播 `room_user_presence`

### 8.3 `room_presence_get`

主动查询当前连接所在房间的在线成员状态。

请求：

```json
{
  "v": 1,
  "type": "command",
  "payload": {
    "request_id": "req-room-presence",
    "action": "room_presence_get",
    "data": null
  }
}
```

成功响应：

- `ack.data.presence`

响应示例：

```json
{
  "presence": {
    "room_id": 1,
    "present_user_ids": [1, 2, 3]
  }
}
```

说明：

- 当前连接必须已经进入房间。
- 该命令只返回 presence runtime，不返回播放同步 runtime。
- 该命令无广播副作用。

### 8.4 `room_video_runtime_get`

主动查询当前连接所在房间的播放同步运行时。

请求：

```json
{
  "v": 1,
  "type": "command",
  "payload": {
    "request_id": "req-room-video-runtime",
    "action": "room_video_runtime_get",
    "data": null
  }
}
```

成功响应：

- `ack.data.room_video_source`
- `ack.data.playback`
- `ack.data.user_resource_states`

响应示例：

```json
{
  "room_video_source": {
    "room_id": 1,
    "source_type": "external_url",
    "external_url": "https://example.com/video.mp4",
    "file_hash": null
  },
  "playback": {
    "room_id": 1,
    "status": "paused",
    "position_seconds": 12.5,
    "anchor_ts_ms": 1710000000000,
    "playback_rate": 1.0
  },
  "user_resource_states": {
    "room_id": 1,
    "user_resource_states": []
  }
}
```

说明：

- 当前连接必须已经进入房间。
- `room_video_source` 和 `playback` 在未设置视频源前可为空。
- 该命令只返回播放同步 runtime，不返回 presence runtime。
- 该命令无广播副作用。

### 8.5 `room_video_source_set`

设置房间当前视频源。

请求示例一：外链模式

```json
{
  "v": 1,
  "type": "command",
  "payload": {
    "request_id": "req-set-source",
    "action": "room_video_source_set",
    "data": {
      "source_type": "external_url",
      "external_url": "https://example.com/video.mp4",
      "anchor_ts_ms": 1710000000000
    }
  }
}
```

请求示例二：本地文件模式

```json
{
  "v": 1,
  "type": "command",
  "payload": {
    "request_id": "req-set-source",
    "action": "room_video_source_set",
    "data": {
      "source_type": "local_file",
      "file_hash": "abc123",
      "anchor_ts_ms": 1710000000000
    }
  }
}
```

参数约束：

- `source_type=external_url` 时必须提供 `external_url`，不能提供 `file_hash`
- `source_type=local_file` 时必须提供 `file_hash`，不能提供 `external_url`
- 当前连接必须已经进入房间
- 当前用户必须满足房间的主动同步权限要求

成功响应：

- `ack.data.room_video_source`
- `ack.data.playback`
- `ack.data.user_resource_states`

副作用：

- 广播 `room_video_source_set`
- 广播 `playback_pause`
- 广播 `user_resource_states`

### 8.6 `playback_play`

请求：

```json
{
  "v": 1,
  "type": "command",
  "payload": {
    "request_id": "req-play",
    "action": "playback_play",
    "data": {
      "position_seconds": 12.5,
      "anchor_ts_ms": 1710000000000,
      "playback_rate": 1.0
    }
  }
}
```

成功响应：

- `ack.data.playback`

注意：

- 当前连接必须已经进入房间
- 当前用户必须满足主动同步权限
- 在 `auto_sync` 模式下，如果仍有用户处于 `stalling`，服务端会拒绝恢复播放

### 8.7 `playback_pause`

请求结构与 `playback_play` 类似：

```json
{
  "v": 1,
  "type": "command",
  "payload": {
    "request_id": "req-pause",
    "action": "playback_pause",
    "data": {
      "position_seconds": 12.5,
      "anchor_ts_ms": 1710000000000,
      "playback_rate": 1.0
    }
  }
}
```

成功响应：

- `ack.data.playback`

副作用：

- 广播 `playback_pause`

### 8.8 `playback_seek`

请求：

```json
{
  "v": 1,
  "type": "command",
  "payload": {
    "request_id": "req-seek",
    "action": "playback_seek",
    "data": {
      "position_seconds": 120.0,
      "anchor_ts_ms": 1710000000000
    }
  }
}
```

成功响应：

- `ack.data.playback`

副作用：

- 广播 `playback_seek`

说明：

- 当前实现中，seek 后房间播放状态会进入 `paused`

### 8.9 `user_resource_status`

用于客户端上报本地资源健康状态。

请求：

```json
{
  "v": 1,
  "type": "command",
  "payload": {
    "request_id": "req-resource-status",
    "action": "user_resource_status",
    "data": {
      "status": "ready",
      "reported_at_ms": 1710000000000,
      "position_seconds": 31.9,
      "error_code": null,
      "error_message": null
    }
  }
}
```

字段说明：

- `status` 必填，取值见 7.5
- `reported_at_ms` 必填
- `position_seconds` 可选
- `error_code`、`error_message` 可选

成功响应：

- `ack.data.user_resource_states`
- 如触发自动暂停或自动恢复播放，还会额外带上：
  - `ack.data.playback`
  - `ack.data.auto_action`

副作用：

- 广播 `user_resource_states`
- 在 `auto_sync` 模式下，可能额外广播 `playback_pause` 或 `playback_play`

## 9. 事件说明

### 9.1 `notification`

通知用户其通知列表有变化。

特点：

- 推送到用户级 channel
- 当前事件仅表示“有更新”，不直接携带通知列表数据
- 客户端应自行调用 HTTP `/api/v1/notifications` 或 `/api/v1/notifications/unread-count` 获取最新数据

### 9.2 `room_info`

通知房间基本信息已变化。

特点：

- 推送到房间级 channel
- 不直接携带完整房间对象
- 客户端应自行调用 HTTP `/api/v1/rooms/{room_id}` 获取最新房间信息

### 9.3 `room_settings`

通知房间设置已变化。

特点：

- 不直接携带完整设置对象
- 客户端应自行调用 HTTP `/api/v1/rooms/{room_id}/settings` 获取最新设置

### 9.4 `room_members`

通知房间成员列表已变化。

特点：

- 不直接携带完整成员列表
- 客户端应自行调用 HTTP `/api/v1/rooms/{room_id}/members` 获取最新成员数据

### 9.5 `room_user_presence`

通知房间在线用户列表变化。

`event.data` 为 `PresenceState`。

### 9.6 `session_closed`

通知当前连接在某个房间中的会话被服务端关闭。

```json
{
  "room_id": 1,
  "reason": "entered_elsewhere"
}
```

当前可能的 `reason`：

- `entered_elsewhere`
- `left_room`
- `removed_from_room`
- `room_deleted`

该事件的 `reason` 登记在 `app.realtime.constants.SessionCloseReason`，不与错误 `ErrorReason` 混用。

客户端收到后应：

- 停止将当前连接视为该房间有效会话
- 清理本地房间态
- 必要时提示用户刷新或跳转

### 9.7 `message`

通知房间新消息。

`event.data` 结构与 HTTP `MessageResponse` 一致。

### 9.8 播放相关事件

以下事件 `data` 结构分别对应 `PlaybackState` 或 `RoomVideoSourceState` / `UserResourceStatesState`：

- `playback_play`
- `playback_pause`
- `playback_seek`
- `room_video_source_set`
- `user_resource_states`

## 10. 权限与状态约束

### 10.1 入房约束

- 用户必须是房间成员
- 当前实现中，一个连接同一时刻只允许有一个 `active_room_id`
- 同一用户在同一房间只能保留一个有效连接会话

### 10.2 视频控制约束

视频控制命令要求：

- 当前连接已进入房间
- 用户在该房间中存在角色
- 用户满足房间 `active_sync_permission`

`active_sync_permission` 取值：

- `owner_only`
- `owner_and_manager`
- `all_members`

### 10.3 自动同步约束

房间 `sync_policy=auto_sync` 时：

- 用户进入 `stalling` 可能触发房间自动暂停
- 所有 stalling 用户恢复后可能触发房间自动恢复播放
- 手动暂停或手动 seek 会改变自动恢复条件

房间 `sync_policy=disabled` 时：

- 不启用上述自动暂停/恢复逻辑

## 11. 错误处理建议

客户端应统一处理以下情况：

- `error` 消息中的业务错误
- WebSocket 关闭
- 认证超时
- 收到 `session_closed`

推荐处理策略：

1. 以 `request_id` 关联请求与响应
2. 对 `invalid_payload` 直接视为客户端实现错误
3. 对 `unauthorized` 触发重新登录或 token 刷新流程
4. 对 `session_closed` 清理对应房间本地状态

## 12. 与 HTTP 的职责划分

当前协议采用“WS 推通知号，HTTP 拉完整数据”的设计：

- 房间信息变更：WS 收到 `room_info`，再用 HTTP 拉详情
- 房间设置变更：WS 收到 `room_settings`，再用 HTTP 拉详情
- 房间成员变更：WS 收到 `room_members`，再用 HTTP 拉列表
- 通知变更：WS 收到 `notification`，再用 HTTP 拉通知
- 消息新增：WS 直接推完整 `MessageResponse`
- 播放同步：WS 直接推运行时状态

## 13. 当前实现边界

### 13.1 单实例约束

当前在线状态、房间 presence、播放运行时状态均保存在后端进程内存中，适用于单实例部署。

### 13.2 单连接单房间会话

当前单个 WebSocket 连接只能激活一个房间会话，不支持同一连接同时进入多个房间。

### 13.3 事件幂等

当前协议未提供单独的消息幂等键与事件重放机制，客户端应以最新状态覆盖本地状态，不依赖事件重放。
