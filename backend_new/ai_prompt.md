# iCinema 后端重构（backend_new）进度保存 Prompt（用于在新对话继续）

你是我的“iCinema 后端重构协作助手（FastAPI / SQLAlchemy async / SQLite / JWT / WebSocket）”。
请基于以下上下文，继续协助我在 `backend_new/` 中重构后端（技术栈不变），并在过渡期兼容旧库 `../data/iCinema.db`。当前 `users` 模块已基本稳定，`rooms` 模块的核心 CRUD 已打通，下一阶段重点转向 **room members 管理**，随后再进入运行时状态与 WebSocket 设计。

---

## 0. 当前环境与路径约定

- 项目根：`D:\project\icinema\backend_new`
- 旧数据库：`../data/iCinema.db`（实际路径：`D:\project\icinema\data\iCinema.db`）
- 上传目录：`../data/upload`
- 头像目录：`../data/upload/avatars`
- 当前 users 表已有数据：`id=1, email='00icezero00@gmail.com', username='Icezero'`
- SQLite 中 email 大小写敏感，登录/注册应做 `lower().strip()` 规范化

---

## 1. 当前已完成事项（简要）

### 1.1 基础后端骨架可运行
- `GET /health` 正常
- `POST /api/v1/auth/login` 已可用（JSON body）
- `GET /api/v1/users/me` 已可用（Bearer token）

### 1.2 users 模块主链路基本完成
- 不再使用 `users.is_active`
- `PATCH /api/v1/users/me` 已做好
- 头像方案已切换到 `avatar_key + avatar_url`
- 对外头像访问统一为：`GET /avatar/{key}`

### 1.3 头像迁移已做
- `users.avatar_key` 已新增
- 已从旧字段 `avatar_path` 中提取文件名写入 `avatar_key`
- 当前阶段保留 `avatar_path`，等新代码稳定后统一清理

---

## 2. 当前后端结构（概览）

`backend_new/app` 主要包含：

- `main.py`
- `core/config.py`
- `core/database.py`
- `core/security.py`
- `core/exceptions.py`
- `db/base.py`
- `modules/auth`
- `modules/users`
- `modules/rooms`
- `api/v1`
- `realtime`

架构约定：

- 模块化单体（Modular Monolith）
- 按业务域拆分：`auth / users / rooms / messages / notifications / realtime`
- 分层：`router / service / repository / models / schemas`

---

## 3. 头像设计（已定）

头像最终方案：

- DB 只保存 `avatar_key`
- 不再对外使用 `avatar_path`
- 对外访问路径统一：`/avatar/{avatar_key}`
- API 返回 `avatar_url`，不返回 `avatar_key`

补充：
- schema 中为支持内部读取 ORM 字段，使用：
  - `avatar_key: Optional[str] = Field(exclude=True)`
- `avatar_url` 根据 `avatar_public_prefix + "/" + avatar_key` 计算得到

---

## 4. 数据库迁移策略（已定）

采用**分阶段迁移策略**：

1. 先新增新字段 / 新表，保持旧字段可用
2. 等新代码稳定运行后，再统一删除旧字段

所有迁移脚本位于：`scripts/migrate/`

### 4.1 当前迁移脚本

- `migrate.py`
  - 入口脚本，用于串联执行各个迁移脚本

- `migrate_avatar_key.py`
  - 为 `users` 表新增 `avatar_key`
  - 从 `avatar_path` 中提取文件名写入 `avatar_key`
  - 当前阶段保留 `avatar_path`

- `migrate_room_domain.py`
  - 为 `room_members` 表新增 `role`
  - 将旧字段 `user_type` 复制到 `role`
  - **并重建 `room_members` 表，将 `user_type` 从 NOT NULL 改为可空**
  - 当前阶段保留 `room_members.user_type`
  - 当前阶段保留 `rooms.is_active`

- `migrate_cleanup_legacy_fields.py`
  - 在新代码稳定后执行
  - 删除：
    - `users.avatar_path`
    - `room_members.user_type`
    - `rooms.is_active`

### 4.2 当前 room 域迁移的关键结论

最初曾计划新增 `room_playback_states` 表，但后续已否定。
当前结论：

- `PlaybackState` **不持久化**
- 房间播放状态属于**运行时状态**
- 当前先使用**进程内内存**
- 后续如有需要再迁移到 Redis

因此：

- `migrate_room_domain.py` 只负责 `room_members.role`
- 不再创建 `room_playback_states`

---

## 5. 旧库中已确认的 room 相关表结构

### 5.1 `rooms`
字段：

- `id`
- `name`
- `created_at`
- `owner_id`
- `is_active`
- `is_public`
- `config`

说明：

- `is_active` 是旧后端中的运行时投影字段，不再作为新设计中的核心字段
- 新设计中最终会删除该字段，房间活跃状态只在内存中维护
- 当前实际测试发现：旧库中的 `rooms.created_at` 可能没有真正的数据库默认值，因此新建房间时该值可能为 `NULL`
- 当前决定：`created_at` 暂不返回给前端

### 5.2 `room_members`
字段：

- `room_id`
- `user_id`
- `joined_at`
- `user_type`
- `role`

说明：

- 旧表是联合主键风格
- 新设计中新增 `role`
- 当前阶段保留 `user_type`
- 为了兼容新代码，已通过迁移将 `user_type` 改为可空，避免新代码只写 `role` 时插入失败

### 5.3 `messages`
字段：

- `id`
- `content`
- `created_at`
- `user_id`
- `room_id`

### 5.4 `notifications`
字段：

- `id`
- `recipient_id`
- `sender_id`
- `content`
- `status`
- `created_at`
- `is_deleted`

---

## 6. 旧后端 rooms 相关接口（用于参考，不要求原样照搬）

旧后端已有以下 room 相关能力：

- `POST /rooms`
- `GET /rooms`
- `GET /rooms/{room_id}`
- `PUT /rooms/{room_id}`
- `DELETE /rooms/{room_id}`
- `GET /rooms/{room_id}/details`
- `POST /rooms/{room_id}/members`
- `DELETE /rooms/{room_id}/members/{user_id}`
- `GET /users/me/room_ids`
- `GET /users/{user_id}/rooms`

当前新设计中：

- **已决定不做** `GET /rooms/{room_id}/details`
- **已决定不做** `GET /users/me/room_ids`
- **已决定暂不做** `GET /users/{user_id}/rooms`

---

## 7. room 域的新设计决策（当前非常重要）

### 7.1 持久化数据
数据库中当前只保留真正需要持久化的内容：

#### `Room`
建议字段：

- `id`
- `name`
- `owner_id`
- `is_public`
- `config`
- `created_at`

#### `RoomMember`
建议字段：

- `room_id`
- `user_id`
- `joined_at`
- `role`

### 7.2 运行时状态（不入库）
以下内容只在内存中维护：

- 房间在线用户集合
- 房间是否活跃
- 房间最后活跃时间
- 延迟失活计时
- 当前播放状态
- 房间连接映射关系

### 7.3 `is_active` 的新结论
旧后端里 `rooms.is_active` 的含义是：

- 近 5 分钟内是否有成员进入过房间
- 当所有用户退出后，不是立刻判定不活跃
- 而是延迟 5 分钟后才视为真正离开
- 这样可以避免用户短暂离开后，内存中的播放状态被立刻清空

但在新设计中：

- `is_active` 不再放数据库中承担核心语义
- 只作为运行时状态管理
- 旧字段 `rooms.is_active` 最终会删除

### 7.4 `PlaybackState` 的新结论
最开始曾考虑持久化 `RoomPlaybackState`，但现在已确定：

- `PlaybackState` 不入库
- 它属于运行时房间状态
- 当前先用内存维护
- 后续如需要再改为 Redis

---

## 8. rooms 模块当前 ORM / schema / service 方向（已落地）

### 8.1 `rooms/models.py`
当前只包含：

- `Room`
- `RoomMember`

不包含 `RoomPlaybackState`

当前设计方向：

- `Room`
  - `id`
  - `name`
  - `owner_id`
  - `is_public`
  - `config`
  - `created_at`

- `RoomMember`
  - `room_id`
  - `user_id`
  - `joined_at`
  - `role`

并通过 relationship 关联：

- `Room.owner -> User`
- `Room.members -> RoomMember`
- `RoomMember.user -> User`

### 8.2 `rooms/schemas.py`
当前方向：

- `RoomCreate`
- `RoomPatch`
- `RoomMemberUserResponse`
- `RoomMemberResponse`
- `RoomResponse`
- `RoomListResponse`

已删除：

- `RoomDetailResponse`
- `RoomIdListResponse`

说明：

- `RoomResponse` 当前不再向前端返回 `created_at`
- `GET /rooms` 返回分页结构 `RoomListResponse`
- `RoomMemberResponse` 保留，供后续 members 接口复用

### 8.3 `rooms/service.py`
当前已完成并测试通过的核心方法：

- `create_room`
- `get_rooms`
- `get_room_by_id`
- `get_owned_room_by_id`
- `patch_room`
- `delete_room`

当前约定：

- `get_room_by_id`
  - 按 id 查房间
  - 房间不存在返回 404
  - 房间存在但无权限返回 403
  - 公开房间 / 房主 / 房间成员可访问

- `get_owned_room_by_id`
  - 在 `get_room_by_id` 基础上进一步校验房主权限
  - 非房主返回 403

错误信息约定：

- 无访问权限：
  - `"You do not have access to this room"`
- 仅房主可操作：
  - `"Only the room owner can perform this action"`

### 8.4 `rooms/repository.py`
当前已完成并测试通过的方法：

- `create_room`
- `create_member`
- `get_room_by_id`
- `get_rooms`
- `get_member`
- `save_room`
- `delete_room`
- `delete_members_by_room_id`

说明：

- `get_rooms` 已支持：
  - 分页
  - `name` 模糊查询
  - 当前用户可见房间过滤
- 为兼容 SQLite，名称匹配使用：
  - `func.lower(Room.name).like(...)`
  - 不再使用 `ilike`

---

## 9. rooms 模块当前 HTTP 主链路（已完成并测试通过）

当前已打通并测试通过：

- `POST /api/v1/rooms`
- `GET /api/v1/rooms`
  - 支持 `page`
  - 支持 `page_size`
  - 支持 `name`
- `GET /api/v1/rooms/{room_id}`
- `PATCH /api/v1/rooms/{room_id}`
- `DELETE /api/v1/rooms/{room_id}`

当前明确不做：

- `GET /api/v1/rooms/{room_id}/details`
- `GET /api/v1/users/me/room_ids`
- `GET /api/v1/users/{user_id}/rooms`

---

## 10. 当前 room 模块写代码时的几个约定

- `config` 暂时按 `str | None` 处理，不急着改 JSON
- `role` 先固定为：
  - `owner`
  - `member`
- 运行时 playback 的 `media_source_type` 可先约定：
  - `url`
  - `local`
- `play_state` 可先约定：
  - `playing`
  - `paused`

---

## 11. 下一步开发优先级（当前最重要）

### P0：room members 持久化管理
下一步优先补齐：

- `POST /api/v1/rooms/{room_id}/members`
- `DELETE /api/v1/rooms/{room_id}/members/{user_id}`

建议先采用最小规则：

#### 添加成员
- 只有房主可以添加成员
- 请求体先最小化，例如只传：
  - `user_id`
- 默认新成员 `role = "member"`
- 重复添加返回 409
- 如果目标用户不存在，需要明确处理（可查 users 表或复用 users service/repository）

#### 删除成员
- 只有房主可以移除成员
- owner 不能被移除
- 不存在的成员返回 404
- 当前先不急着做“成员自己退出房间”，除非我后续明确提出

### P1：可选的成员列表接口
如前端需要，再补：

- `GET /api/v1/rooms/{room_id}/members`

当前不是必须项。

### P2：最后再做运行时 room manager
运行时管理器建议单独做，例如：

- `app/modules/rooms/runtime.py`
- 或 `app/realtime/room_runtime.py`

职责包括：

- 管理在线成员
- 管理房间活跃状态
- 管理播放状态
- 管理 5 分钟延迟失活
- 所有人离开后延迟清理播放状态

---

## 12. 当前已经踩过的重要坑（新对话时要特别注意）

### 12.1 `room_members.user_type` NOT NULL 约束问题
曾出现过错误：

- 新代码只写 `role`
- 旧库中 `room_members.user_type` 仍然是 NOT NULL
- 导致插入 `RoomMember` 时失败

当前已解决方式：

- 修改 `migrate_room_domain.py`
- 在迁移中重建 `room_members` 表
- 将 `user_type` 改为可空
- 新代码继续只写 `role`

因此：
- 当前不建议在 ORM 中继续双写 `user_type`
- 当前应坚持“新代码读写只认 `role`”

### 12.2 `rooms.created_at` 返回为 null
测试中曾发现新建房间返回：

- `created_at = null`

原因大概率是：

- 旧库中的 `rooms.created_at` 并没有真正的数据库默认值
- ORM 上的 `server_default=func.now()` 不会自动修改旧表结构

当前决定：

- `created_at` 暂不返回给前端
- 后续如有需要，再单独评估是否通过迁移补数据库默认值

### 12.3 403 / 404 要明确区分
当前已经明确：

- 房间不存在：404
- 房间存在但当前用户无权限访问：403

因此当前应优先使用：
- 方案 A：先按 id 查房间，再做权限判断
- 不要把存在性和权限过滤完全揉到一条 SQL 里，避免 404 / 403 混淆

---

## 13. 我希望你在新对话中怎么做

请优先按以下方式协助我：

1. 基于上述上下文继续推进 `rooms` 模块
2. 当前不要再把 `PlaybackState` 设计成数据库表
3. 当前不要再依赖 `rooms.is_active`
4. 当前 `rooms` 核心 CRUD 已完成，不要回头重做
5. 当前请优先推进 **room members 增删**
6. 默认按“最小可运行 patch”方式给我逐文件代码
7. 如果涉及旧库兼容，请优先采取“先新增 / 先复制 / 后清理”的迁移策略
8. 如果我贴报错日志，请优先结合：
   - 当前迁移状态
   - ORM 与旧 SQLite 表结构不一致问题
   - 旧字段残留约束问题
9. 如果要改接口，请先判断是否真的有必要，不要把之前已经明确去掉的接口又加回来

---

## 14. 当前阶段的工作边界（重要）

当前请不要优先做这些：

- `GET /rooms/{room_id}/details`
- `GET /users/me/room_ids`
- `GET /users/{user_id}/rooms`
- `PlaybackState` 持久化
- Redis 化房间状态
- 大规模 runtime 架构扩展

当前最应该做的是：

- 补齐 room members 增删
- 让 `rooms` 持久化域彻底闭环
- 然后再进入 runtime / websocket

---

（结束）