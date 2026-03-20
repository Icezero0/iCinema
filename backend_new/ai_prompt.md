# iCinema 后端重构（backend_new）进度保存 Prompt（v5，用于新对话继承）

你是我的 **iCinema 后端重构协作助手（FastAPI / SQLAlchemy async / SQLite / JWT / WebSocket）**。
请基于以下上下文继续协助我在 `backend_new/` 中推进后端重构。

当前阶段：

* users / rooms / membership / RBAC 已稳定
* RoomJoinRequest（membership workflow）已完成（model + repo + service + API），核心流程已跑通
* notification 模块正在重构，旧设计已废弃，新设计已拍板
* remove member API 已调整为 REST 风格，并修复了“执行 DELETE 但未 commit 导致最终 ROLLBACK”的问题

下一阶段主线：
**完成 notification 新结构对齐，并把 notification 接入 RoomJoinRequest workflow**
然后再做：
**WebSocket 实时推送**

---

# 0. 当前环境与路径约定

项目根：
D:\project\icinema\backend_new

数据库：
../data/iCinema.db

上传目录：
../data/upload

测试用户：
id=1
email=00icezero00@gmail.com

SQLite 注意：
email 查询统一 strip().lower()

策略：
旧库兼容 + 渐进迁移
但 **notification 表这次允许直接 drop 重建**，旧数据无所谓

---

# 1. 全局命名规范（必须遵守）

service：

find_xxx → 返回对象或 None  
get_xxx → 查不到抛 NotFoundError  
get_xxxs → 列表/分页  

禁止：
get_xxx_or_404

repo / service / schema / model 字段命名需要统一，不要一边叫 sender 一边叫 actor，一边叫 recipient_id 一边叫 recipient_user_id。

---

# 2. 异常体系

app/core/exceptions.py：

BadRequestError  
UnauthorizedError  
ForbiddenError  
NotFoundError  
ConflictError  

---

# 3. 参数校验

schema → 格式 / trim / 基础校验  
service → 业务规则  

PATCH：
未传 → 不更新  
空字符串 → schema 拦截  

---

# 4. created_at / updated_at 规范

created_at：

数据库：
DEFAULT CURRENT_TIMESTAMP

ORM：
server_default=func.now()

Python：
不手动传

updated_at：

SQLite 使用 trigger 自动更新  
ORM 使用 onupdate=func.now()（辅助）

---

# 5. rooms 域结构

modules/rooms：

models.py（未拆，避免循环依赖）  
constants.py  
permissions.py  
room/  
membership/  
join_request/  

---

# 6. RBAC 权限体系

角色：

owner  
manager  
member  

权限统一使用：

MANAGE_MEMBERS  
MANAGE_MANAGERS  

当前权限表：

- owner：VIEW_ROOM / UPDATE_ROOM / DELETE_ROOM / VIEW_MEMBERS / INVITE_USER / REVIEW_JOIN_REQUEST / MANAGE_MEMBERS / MANAGE_MANAGERS
- manager：UPDATE_ROOM / VIEW_ROOM / VIEW_MEMBERS / INVITE_USER / REVIEW_JOIN_REQUEST / MANAGE_MEMBERS
- member：VIEW_ROOM / INVITE_USER / VIEW_MEMBERS

删除成员规则已明确：

- owner 不能被删除
- manager 只能由 owner 删除（即需要 MANAGE_MANAGERS）
- member 可由 owner / manager 删除（即需要 MANAGE_MEMBERS）
- 不能删除自己

---

# 7. RoomMembership 当前状态

RoomMembershipService 已整理为统一风格，包含：

- find_room_member
- find_room_role
- get_room_members
- add_room_member
- remove_room_member

remove_room_member 之前出现的问题：

- SQL DELETE 实际执行了
- 但 service 中没有 commit
- 请求最终返回 204，但 session 结束时发生 ROLLBACK
- 已确认问题本质：**写操作必须显式 commit，否则不会真正落库**

现状：

- remove member API 已改为 REST 风格：
  DELETE /rooms/{room_id}/members/{target_user_id}
- 建议返回 204 No Content
- service 写操作后必须 commit

后续如果需要“按权限找房间中哪些人可审批/可管理”，这个能力应优先放在 **membership/service**，不要放在 join_request/service。
更推荐通用方法名：
`get_room_user_ids_by_permission(...)`
而不是写死 `get_room_reviewer_user_ids(...)`

---

# 8. RoomJoinRequest（核心设计）

表名：

room_join_requests

## 8.1 核心字段

room_id  
initiator_user_id  
target_user_id  

source：
apply / invite / member_invite  

status：
pending / approved / rejected / cancelled  

## 8.2 双侧状态机

room_action：
pending / approved / rejected  

target_action：
pending / approved / rejected  

## 8.3 审批记录

room_action_by_user_id

## 8.4 状态收敛规则 finalize

1. 任一方 rejected → status = rejected  
2. 双方 approved → status = approved + add_member  
3. 否则保持 pending  

## 8.5 约束

(room_id, target_user_id) 在 pending 状态下唯一

---

# 9. RoomJoinRequest service 当前结构

对外方法：

create_apply_request  
create_invite_request  
get_join_request_by_id  
get_accessible_join_request_by_id  
get_room_join_requests  
approve_request  
reject_request  

内部：

_approve_by_target  
_approve_by_room  
_reject_by_target  
_reject_by_room  
_finalize  

当前实现特点：

- create_apply_request / create_invite_request 已跑通
- approve / reject / finalize 已跑通
- finalize 中 approved 时会自动 add_room_member
- API 层创建类接口（apply / invite）只返回 200 OK，不返回对象
- approve / reject 如果返回 ORM，则必须 commit 后重新查询，避免 MissingGreenlet

---

# 10. API 设计现状

rooms 侧：

GET    /rooms  
POST   /rooms  
GET    /rooms/{room_id}  
PATCH  /rooms/{room_id}  
DELETE /rooms/{room_id}  

GET    /rooms/{room_id}/members  
DELETE /rooms/{room_id}/members/{target_user_id}

GET    /rooms/{room_id}/join-requests  
POST   /rooms/{room_id}/join-requests/apply  
POST   /rooms/{room_id}/join-requests/invite  

join_requests 侧：

GET    /join-requests/{id}  
POST   /join-requests/{id}/approve  
POST   /join-requests/{id}/reject  

通知侧：

GET    /notifications  
GET    /notifications/unread-count  
POST   /notifications/{notification_id}/read  
POST   /notifications/read-all  

当前 notification API 中：
- delete_notification 路由应去掉（新表没有 is_deleted）
- read-all 建议直接返回 204，无需手动构造 Response

---

# 11. notification 模块：旧设计已废弃

旧 notification 设计里有这些字段/概念，现已废弃：

recipient_id  
sender_id  
title  
content  
is_deleted  
event_key  
payload  
subtype  

本次设计明确：
**notification 不负责表达“具体发生了什么”，只表示“某个流程对象有了新进展”。**
用户看到通知后，进入对应流程页面查看详情。

所以：
- 不需要 event_key
- 不需要 payload
- 不需要 subtype
- 不需要在 notification 表里存 title/content
- 不需要软删除 is_deleted

---

# 12. notification 新表结构（已拍板）

notifications 表仅保留以下字段：

id

recipient_user_id

actor_user_id nullable

notification_type

related_type

related_id

is_read

read_at

created_at

说明：

- recipient_user_id：通知接收人
- actor_user_id：触发这次流程变动的人，可空
- notification_type：当前保留 system / workflow
- related_type：当前已确定会用 ROOM_JOIN_REQUEST，后续可扩展
- related_id：关联的业务对象 id
- is_read / read_at：已读状态
- created_at：创建时间

notification 的语义：
- 一条通知只代表“该 related object 有新进展”
- 不区分 apply_created / approved / rejected 等细粒度事件
- 前端显示可做成泛化文案，例如“流程有新进展”，具体内容到流程页看

---

# 13. notification constants 当前状态

目前可保持：

from enum import StrEnum

class NotificationType(StrEnum):
    SYSTEM = "system"
    WORKFLOW = "workflow"

class NotificationRelatedType(StrEnum):
    ROOM_JOIN_REQUEST = "room_join_request"

目前 constants 不需要改动。
以后若真做系统公告 / 私聊，再按需扩展 RelatedType。

---

# 14. notification model / schema / repo / service 对齐原则

## 14.1 model

需要使用：

- recipient_user_id
- actor_user_id
- notification_type
- related_type
- related_id
- is_read
- read_at
- created_at

relationship 命名统一为：

- recipient
- actor

不要再保留 sender 命名。

## 14.2 schema

NotificationCreate / NotificationResponse 需要同步新字段：

- recipient_user_id
- actor_user_id
- notification_type
- related_type
- related_id
- is_read
- read_at
- created_at

删除：

- title
- content

校验规则简化为：
- related_type 和 related_id 要么同时为空，要么同时存在
- 不再写 “SYSTEM 不能有 related / WORKFLOW 必须有 related” 这种旧规则
  因为以后 system 通知也可能关联 announcement / direct_message

## 14.3 repository

需要统一改为新字段：

- recipient_user_id
- actor_user_id

删除所有旧字段相关逻辑：

- title
- content
- is_deleted

mark_all_as_read 必须同时写：
- is_read = True
- read_at = func.now()

find/get 方法命名尽量遵守：
- find_xxx 返回对象或 None

## 14.4 service

NotificationService 也要同步新字段。

特别注意：
`NotificationService.create_notification()` **不要自己 commit**
原因：
RoomJoinRequest workflow 接通知时，应该由调用方（如 RoomJoinRequestService）统一控制事务边界。

旧的 delete_notification 逻辑应删除，因为新表没有 is_deleted。

---

# 15. RoomJoinRequest 与 notification 的联动规则（已拍板）

通知不表达细粒度事件，只表达“该流程有新进展”。

因此通知点规则改为：

## 15.1 create_apply_request

申请人发起申请后：
通知房间侧 **所有有 REVIEW_JOIN_REQUEST 权限的人**

## 15.2 create_invite_request

发起邀请后：
通知 **target_user**

## 15.3 流程最终 approved / rejected

仅通知：
**target_user**

不通知：
initiator_user

说明：
- 邀请人是否收到结果通知，不重要，不需要做
- 通知文案不区分“通过/拒绝”，统一只表示该流程对象有新进展
- 具体状态到流程页查看

---

# 16. 关于 RoomJoinRequestService 中的存在性校验

在 create_invite_request 开头出现的：

await self.room_service.get_room_by_id(db, room_id)
await self.user_service.get_user_by_id(db, target_user_id)

语义是：
- 提前确认 room 存在
- 提前确认 target user 存在
- 若不存在，显式抛出 NotFoundError
- 避免后续把“不存在”误报成“Forbidden”或数据库外键异常

讨论结论：
- `get_room_by_id` 的显式校验价值较高，建议保留
- `get_user_by_id` 理论上可优化，但当前阶段更重视错误语义清晰，暂可保留

---

# 17. 当前已明确的技术坑

## MissingGreenlet

原因：
Pydantic 序列化触发 SQLAlchemy lazy load

解决：
- 所有返回 ORM → 必须 preload / selectinload
- 写操作后若要返回 ORM → commit 后重新查询再返回

## DELETE 后 204 但数据没变

原因：
- SQL 执行了
- 但 service 中未 commit
- 请求结束时 session 自动 rollback

解决：
- 所有写操作必须明确 commit

---

# 18. 当前完成情况

已完成：

- users
- rooms
- membership
- RBAC
- RoomJoinRequest workflow 主流程
- join request API
- remove member API 改为 DELETE /rooms/{room_id}/members/{target_user_id}
- remove member 的事务问题已定位并修复思路明确

正在进行：

- notification 模块按新表结构重构
- notification model / schema / repo / service 对齐
- RoomJoinRequest workflow 接 notification

---

# 19. 下一阶段任务（优先级）

## 第一优先级

完成 notification 领域新结构改造：

- migration 脚本
- models.py
- schemas.py
- repository.py
- service.py
- notifications API 对齐

## 第二优先级

把 notification 接入 RoomJoinRequestService：

- create_apply_request → 通知所有审批人
- create_invite_request → 通知 target_user
- finalize(approved/rejected) → 仅通知 target_user

## 第三优先级

完成通知列表 / 未读数联调测试

## 第四优先级

接 WebSocket 实时推送：

- 新通知实时推送
- 未读数实时更新
- join request 流程更新时的实时同步

---

# 20. 当前对话目标

接下来重点不是再讨论 notification 的表结构，而是：

1. 把 notification 模块剩余代码全部对齐到新设计
2. 把 RoomJoinRequestService 与 notification 接上
3. 跑通 apply / invite / approve / reject 场景下的通知写入
4. 再继续 WebSocket