# Error Reason 登记表

版本：v1  
状态：Draft  
适用范围：HTTP 与 WebSocket 错误响应

## 1. 文档定位

本文档登记后端统一错误响应中的 `error.reason`。

`reason` 是稳定的 snake_case 业务原因，前端应优先使用它作为 i18n key。后端代码中的权威登记位置是：

```text
backend/app/core/error_reasons.py
```

新增错误原因时，应先在 `ErrorReason` 中登记，再在业务代码中引用。业务代码禁止直接写 `reason="..."` 裸字符串。

## 2. 错误响应格式

HTTP 错误响应：

```json
{
  "error": {
    "code": "bad_request",
    "reason": "invalid_image_id",
    "message": "Invalid image id",
    "details": {
      "image_id": 123
    }
  }
}
```

WS 错误响应：

```json
{
  "v": 1,
  "type": "error",
  "payload": {
    "request_id": "req-123",
    "code": "bad_request",
    "reason": "invalid_websocket_payload",
    "message": "Invalid websocket payload",
    "details": {
      "errors": []
    }
  }
}
```

字段说明：

- `code`：粗粒度错误类别，主要用于协议层或 HTTP 状态语义。
- `reason`：稳定业务原因，前端 i18n 和分支处理优先使用该字段。
- `message`：后端兜底文案，主要用于调试。
- `details`：可选结构化细节，只包含安全、必要的信息。

## 3. Core

| Reason | 语义 | 常见 details |
| --- | --- | --- |
| `app_error` | 通用业务错误兜底原因。通常只在未显式指定 reason 时使用。 | `null` |
| `request_validation_failed` | HTTP 请求参数、路径参数、query、body 等 FastAPI/Pydantic 校验失败。 | `errors` |

## 4. Auth / User

| Reason | 语义 | 常见 details |
| --- | --- | --- |
| `authentication_required` | WS command 需要先完成认证。 | `null` |
| `email_already_exists` | 注册用户时邮箱已存在。 | `field` |
| `invalid_credentials` | 登录邮箱或密码错误。 | `null` |
| `invalid_refresh_token` | refresh token 无效或已过期。 | `null` |
| `invalid_token` | token 无效或已过期。 | `null` |
| `invalid_token_payload` | token payload 缺少必要字段或字段格式错误。 | `field`, `constraint` |
| `invalid_token_type` | token 类型不符合当前接口要求。 | `expected`, `actual` |
| `missing_authorization_token` | HTTP 请求缺少认证 token。 | `null` |
| `user_not_found` | 用户不存在。 | `user_id` |

## 5. Room / Membership / Join Request

| Reason | 语义 | 常见 details |
| --- | --- | --- |
| `cannot_remove_self_from_room` | 成员移除接口不允许移除自己。 | `room_id`, `user_id` |
| `invalid_room_id` | WS command 中的 `room_id` 不是正整数。 | `field`, `constraint` |
| `invalid_room_member_role` | 房间成员角色数据非法。 | `room_id`, `user_id`, `role` |
| `join_request_already_handled` | 入房请求已处理，不能重复审批。 | `request_id`, `status` |
| `join_request_not_found` | 入房请求不存在。 | `request_id` |
| `join_request_target_action_forbidden` | 当前用户不能作为目标用户处理该入房请求。 | `request_id`, `target_user_id` |
| `missing_room_id` | WS command 缺少 `room_id`。 | `field`, `constraint` |
| `owner_cannot_be_removed_from_room` | 房主不能被移出自己创建的房间。 | `room_id`, `user_id` |
| `owner_cannot_leave_room` | 房主不能退出自己创建的房间，只能删除房间。 | `room_id`, `user_id` |
| `owner_role_cannot_be_changed` | 房主角色不能被设置或解除管理员。 | `room_id`, `user_id` |
| `pending_join_request_already_exists` | 目标用户已有待处理入房请求。 | `room_id`, `target_user_id`, `request_id` |
| `room_enter_forbidden` | 当前用户不是房间成员，不能进入房间 WS 会话。 | `room_id` |
| `room_member_not_found` | 房间成员关系不存在。 | `room_id`, `user_id` |
| `room_not_accepting_join_requests` | 房间当前不接受入房申请。 | `room_id`, `join_audit_mode` |
| `room_not_entered` | WS 当前连接还没有进入房间，不能执行依赖房间上下文的操作。 | `null` |
| `room_not_found` | 房间不存在。 | `room_id` |
| `room_permission_denied` | 当前用户没有执行该房间操作所需权限。 | `room_id`, `permission`, `role` |
| `room_settings_not_found` | 房间设置不存在。 | `room_id` |
| `user_already_room_member` | 用户已经是房间成员。 | `room_id`, `user_id` |

## 6. Media / Sticker / Emoji

| Reason | 语义 | 常见 details |
| --- | --- | --- |
| `duplicate_sticker_ids` | 更新贴纸库排序时 payload 中存在重复贴纸 id。 | `null` |
| `empty_avatar_file` | 上传的头像文件为空。 | `field`, `constraint` |
| `empty_media_file` | 上传的媒体文件为空。 | `asset_type` |
| `image_not_found` | 图片不存在，或不是 image 类型，或已不可用。 | `image_id` |
| `image_unavailable` | 图片已过期、被删除或不可用于消息发送。 | `image_id` |
| `invalid_emoji_id` | emoji id 不存在或不可用。 | `emoji_id` |
| `invalid_image_id` | 消息中的 image id 无效或不是 image 类型。 | `image_id` |
| `invalid_media_storage_key` | 媒体 storage key 含非法路径片段。 | `asset_type` |
| `invalid_sticker_id` | 消息中的 sticker id 无效或不是可用 sticker。 | `sticker_id` |
| `media_asset_not_found` | 媒体资源不存在或不可服务。 | `asset_id`, `asset_type` |
| `media_file_not_found` | 媒体元数据存在，但本地文件不存在。 | `asset_id`, `asset_type` |
| `pagination_not_allowed_with_all` | `all=true` 查询贴纸库时不能同时传分页参数。 | `all`, `has_page`, `has_page_size` |
| `sticker_library_payload_contains_invalid_items` | 更新贴纸库时 payload 包含不属于当前用户贴纸库的贴纸。 | `null` |
| `sticker_not_found` | sticker 不存在或不可用。 | `sticker_id` |
| `sticker_not_in_user_library` | 发送消息时引用的 sticker 不在当前用户贴纸库中。 | `sticker_id` |
| `unsupported_avatar_file_type` | 头像文件 MIME 类型不支持。 | `field`, `content_type`, `allowed_content_types` |
| `unsupported_media_asset_type` | 媒体资源类型不支持。 | `asset_type`, `asset_id` |
| `unsupported_media_file_extension` | 媒体文件扩展名不支持。 | `asset_type`, `extension`, `content_type` |
| `unsupported_media_file_type` | 媒体文件 MIME 类型不支持。 | `asset_type`, `content_type` |
| `unsupported_upload_media_type` | 当前上传类型不支持。 | `asset_type` |

## 7. Message / Notification

| Reason | 语义 | 常见 details |
| --- | --- | --- |
| `message_not_found` | 消息创建后回读失败或消息不存在。 | `message_id` |
| `notification_not_found` | 通知不存在。 | `notification_id` |
| `notification_permission_denied` | 当前用户不能访问该通知。 | `notification_id` |
| `notification_related_fields_incomplete` | 创建通知时 `related_type` 和 `related_id` 没有同时提供。 | `has_related_type`, `has_related_id` |

## 8. WebSocket Protocol / Playback Runtime

| Reason | 语义 | 常见 details |
| --- | --- | --- |
| `field_not_allowed_for_source_type` | 当前播放源类型不允许传入某字段。 | `field`, `source_type` |
| `invalid_heartbeat_action` | heartbeat action 不是 `ping`。 | `field`, `expected`, `actual` |
| `invalid_integer_field` | WS command 中某字段不是合法整数。 | `field`, `constraint` |
| `invalid_number_field` | WS command 中某字段不是合法数字。 | `field`, `constraint` |
| `invalid_resource_health_status` | 资源健康状态不在允许枚举内。 | `field`, `allowed_values` |
| `invalid_source_type` | 播放源类型不在允许枚举内。 | `field`, `allowed_values` |
| `invalid_string_field` | WS command 中某字符串字段为空或类型错误。 | `field`, `constraint` |
| `invalid_websocket_payload` | WS 消息 payload 结构校验失败。 | `errors` |
| `missing_resource_health_status` | 上报资源健康状态时缺少 `status`。 | `field`, `constraint` |
| `missing_source_type` | 设置播放源时缺少 `source_type`。 | `field`, `constraint` |
| `playback_resume_blocked_by_stalling_users` | 自动同步模式下仍有用户卡顿，不能恢复播放。 | `room_id`, `stalling_user_ids` |
| `room_video_control_forbidden` | 当前用户不能控制该房间播放状态。 | `room_id` |
| `room_video_control_permission_denied` | 当前用户角色不满足房间播放控制权限。 | `role`, `required_permission` |
| `room_video_source_not_set` | 当前房间还没有设置播放源，不能执行播放控制。 | `room_id` |
| `unsupported_client_message_type` | 客户端发送了服务端不接受的 WS message type。 | `type` |
| `unsupported_command_action` | 客户端发送了未知 WS command action。 | `action` |
| `unsupported_room_command_action` | room handler 不支持该 command action。 | `action` |
| `unsupported_room_video_command_action` | room video handler 不支持该 command action。 | `action` |

## 9. 非错误 reason

以下 `reason` 用于 WS 事件 payload，不属于 `ErrorReason`，登记在：

```text
backend/app/realtime/constants.py
```

| Reason | 场景 |
| --- | --- |
| `entered_elsewhere` | 同一用户在同一房间建立了新的有效会话，旧会话被关闭。 |
| `left_room` | 用户通过 HTTP 成员关系接口退出房间，房间会话被关闭。 |
| `removed_from_room` | 用户被房间管理者移出房间，房间会话被关闭。 |
| `room_deleted` | 房间被删除，房间内所有会话被关闭。 |

## 10. 维护约定

- 新增 `error.reason` 时必须先更新 `ErrorReason`。
- 新增 `ErrorReason` 后应同步更新本文档。
- 业务代码应引用 `ErrorReason.X`，不要直接写字符串。
- 如果新增的是事件原因而不是错误原因，应登记到对应业务常量中，不要放进 `ErrorReason`。
- `details` 只放前端展示、分支处理或排查必要的信息，不放 token、密码、文件绝对路径等敏感信息。
