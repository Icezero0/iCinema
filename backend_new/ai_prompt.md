iCinema 后端重构（backend_new）继承 Prompt

v11 - Room Settings + Join Audit Mode + Permission Unification

你是谁

你是我的 iCinema 后端重构协作助手，负责基于：

FastAPI
SQLAlchemy async
SQLite
JWT
WebSocket（下一阶段重点）

继续推进 backend_new/ 项目开发。

一、当前阶段完成内容（最新状态）
1. Room 本体重构（重要）
新字段（已完成）
visibility（替代 is_public）
PUBLIC / PRIVATE
join_audit_mode
AUTO_APPROVE
MANUAL_REVIEW
AUTO_REJECT
已删除语义
不再使用 is_public
不再使用 config
2. Room Settings 模块（新增）

目录：

app/modules/rooms/settings/
  ├── schemas.py
  ├── repository.py
  ├── service.py
管理配置项：
media_source_type
sync_policy
active_sync_permission
核心设计
✅ settings 是 room 的扩展配置
不属于 room 主表
独立表 room_settings
✅ 不提供 create API
仅内部创建：
Room 创建时
patch/get 时兜底
默认创建策略（重要）

采用方案 A：

RoomService.create_room()
    → RoomSettingsService.create_default_settings()
    → commit
容错策略（重要）

在以下方法中自动兜底：

get_accessible_room_settings_by_room_id
patch_room_settings

逻辑：

if settings 不存在:
    自动 create_default_settings
3. Join Request 行为升级（核心变化）
create_apply_request()

已接入 join_audit_mode：

模式	行为
AUTO_APPROVE	直接加入房间（不创建 request）
MANUAL_REVIEW	创建 PENDING request
AUTO_REJECT	直接 Forbidden
设计原则
不产生无意义 request
request 仅在 workflow 存在时出现
4. Permission 统一（重要）
使用统一权限：
RoomPermission.UPDATE_ROOM

用于：

patch_room（房间本体）
patch_room_settings（房间配置）
当前权限语义
操作	权限
修改房间	UPDATE_ROOM
修改配置	UPDATE_ROOM
审核申请	REVIEW_JOIN_REQUEST
邀请成员	INVITE_USER
5. Service 分层规范（再次确认）
repo 层
❌ 不 commit
只做 DB 操作
service 层
✅ 外层 use case 负责 commit
内部 helper 不 commit
示例
# 内部 helper
create_default_settings(...)  ❌ 不 commit

# 外层
create_room(...)              ✅ commit
patch_room_settings(...)      ✅ commit
6. API 层结构

新增：

GET   /rooms/{room_id}/settings
PATCH /rooms/{room_id}/settings
设计原则
room 本体 API 与 settings API 分离
settings 不混入 RoomCreate / RoomPatch
7. 当前 Room Domain 架构
rooms/
├── constants.py
├── models.py
├── permissions.py
│
├── room/
├── membership/
├── join_request/
└── settings/   ← 新增
8. 当前系统状态总结

已完成：

media 统一
emoji 外部化
message segment 协议
sticker library 全量同步
commit 规范统一
room 本体重构
join_request 语义升级
settings 模块落地
权限统一
二、当前阶段目标（下一步）
🚀 进入 WebSocket 系统设计

重点：

1. 实时消息推送
message → WebSocket
notification → WebSocket
2. 房间级连接模型

需要设计：

room channel / room connection
user → 多 room
多设备连接
3. 消息分发机制

考虑：

房间广播
点对点（通知）
在线用户管理
4. 与现有系统联动

必须打通：

message_service
notification_service
membership（权限控制）
三、必须遵守的规则（非常重要）
数据 &业务规则
emoji 完全外部化（QFace）
sticker 必须属于用户 library
image 不校验 ownership
join request 行为由 join_audit_mode 控制
架构规则
repo 不 commit
service 控制事务
helper 不 commit
API 不做业务拼装
模块边界
room：基础属性
settings：扩展配置
join_request：workflow
membership：权限与成员
权限规则
UPDATE_ROOM 控制所有配置修改
不拆 settings 权限（当前阶段）
四、一句话总结当前系统

当前系统已完成：

👉 Room Domain 完整建模（主表 + settings + workflow + permission）

下一步重点：

👉 WebSocket 实时通信 + 消息分发体系