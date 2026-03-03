# iCinema 后端重构（backend_new）进度保存 Prompt（用于在新对话继续）

你是我的“iCinema 后端重构协作助手（FastAPI/SQLAlchemy async/SQLite/JWT/WS）”。  
请基于以下上下文，继续协助我在 `backend_new/` 中从零重构后端（技术栈不变），并保持与旧库 `../data/iCinema.db` 的兼容（过渡期），同时逐步完成 API/WS 规范化。

---

## 0. 当前环境与路径约定

- 项目根：`D:\project\icinema\backend_new`
- 旧数据库：`../data/iCinema.db`（已确认实际路径：`D:\project\icinema\data\iCinema.db`）
- 上传目录：`../data/upload`
- 头像目录：`../data/upload/avatars`
- 当前用户表已有数据：`users` 里存在 `id=1, email='00icezero00@gmail.com', username='Icezero'`
- 之前测试：SQLite 中 email 大小写敏感（`00Icezero00@gmail.com` 查不到，`00icezero00@gmail.com` 能查到）

---

## 1. 已完成事项（骨架 + 可运行）

### 1.1 FastAPI 启动成功
- `GET /health` 返回：`{"status":"ok"}`

### 1.2 登录成功（JSON body）
- `POST /api/v1/auth/login` 用 JSON 登录成功，返回 `access_token / refresh_token`
- 注意：登录接口最初用 form-urlencoded 会报 Pydantic 解析错误（现在已明确用 JSON）

### 1.3 兼容旧库：移除/忽略 `is_active`
- 旧库 `users` 表没有 `is_active` 列
- 曾在 `AuthService` 中因 `user.is_active` 触发 500，已删除/不使用该字段
- 曾在 `UserMeResponse` schema 中因 `is_active` 必填导致 500，已移除该字段（暂不实装 is_active 功能）

### 1.4 `GET /api/v1/users/me` 已可用（Bearer token）
- 之前返回包含：
  - `id, email, username, auto_accept`
- 头像字段策略已调整（见 3）

---

## 2. 配置（.env 内容）

当前 `.env`（已在项目中）：

APP_NAME=iCinema Backend v2
APP_ENV=development
DEBUG=true

JWT_SECRET_KEY=...（已配置）
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

DATA_DIR=../data
DB_FILENAME=iCinema.db

UPLOAD_DIR=../data/upload
AVATAR_SUBDIR=avatars

说明：
- Settings 使用 Pydantic Settings（env_file=.env），默认值存在仅为 fallback
- `get_settings()` 使用 `@lru_cache`，启动时读取一次 env；改 env 需重启服务生效

---

## 3. 头像存储与 API 设计（已定最终方向）

### 3.1 不再使用 /static 或 /media 前缀
最终决定：只使用一个资源路由前缀 `/avatar`

目标：
- DB 只保存 `avatar_key`（文件名或 key），不保存任何路径
- 对外访问：`GET /avatar/{avatar_key}` 返回图片文件
- API 返回给前端：只返回 `avatar_url`，不返回 `avatar_key`（前端无需 key）

### 3.2 数据库迁移已完成：新增 `avatar_key` 并从旧 `avatar_path` 提取
- 已将旧库 `users.avatar_path`（例如 `/avatars/xxx.jpg`）解析成 `avatar_key=xxx.jpg`
- 已执行迁移（新增列 + 填充数据）
- 迁移脚本已整理（见 6）

### 3.3 Schema 计算字段踩坑 & 解决
- 想只返回 `avatar_url`，不返回 `avatar_key`，但 `computed_field` 需要内部访问 key
- 直接访问 `self.avatar_key` 会报错（schema 未声明字段）
- 解决方案：在 schema 中声明 `avatar_key: Optional[str] = Field(exclude=True)`（读取 ORM 属性但不输出）
- `avatar_url` 用 `settings.avatar_public_prefix + '/' + avatar_key` 拼出

---

## 4. 当前后端主要结构（backend_new/app）

- app/main.py：创建 FastAPI、CORS、异常处理、路由挂载、health
- app/core/config.py：Settings（含 data/upload 目录推导、database_url 推导）
- app/core/database.py：Async engine + sessionmaker + get_db（Depends 用于请求级 session）
- app/core/security.py：JWT + passlib bcrypt（verify/hash/token）
- app/core/exceptions.py：AppError/UnauthorizedError/ConflictError 等 + handler
- app/db/base.py：SQLAlchemy Base
- app/modules/auth：schemas/service/deps（get_current_user 使用 Bearer token）
- app/modules/users：models/schemas/repository/service/avatar_service
- app/api/v1：router.py 聚合；auth.py（register/login）；users.py（me/patch/avatar）
- app/realtime：ws_router + protocol（当前是最小占位 echo，WS 文档需要另写）

注意：
- 应补充 package 的 `__init__.py`（避免某些环境 import 异常）
- zip 中出现过 `__pycache__`，应 gitignore

---

## 5. 已知旧库 users 表字段（兼容期参考）

旧库 users 列（从 SQL 日志确认）：
- id
- email
- username
- hashed_password
- avatar_path（旧字段：无效，将来不用）
- auto_accept
- created_at
（无 is_active、无 updated_at）

新代码兼容：
- ORM/Repo/Auth 使用 `hashed_password`
- 不使用 is_active
- 已新增 `avatar_key`（DB 内部字段）

---

## 6. 迁移脚本（SQLite，幂等可重复执行）

脚本目标：
- 若 users 表无 `avatar_key` 列则新增：`ALTER TABLE users ADD COLUMN avatar_key TEXT;`
- 把 `avatar_path` 末尾 filename 写入 `avatar_key`
- 默认只填充 `avatar_key` 为空的行，避免覆盖已有值
- 输出迁移统计

（脚本由助手给出完整版本，可直接保存为 scripts/migrate_avatar_key.py）

---

## 7. 当前 API 验证状态

- /health ✅
- /api/v1/auth/login ✅（JSON body）
- /api/v1/users/me ✅（Bearer token）
- 接下来要验证/继续构建：
  - PATCH /api/v1/users/me（partial update）
  - PATCH /api/v1/users/me/avatar（上传文件，写 avatar_key）
  - GET /avatar/{key}（文件读取接口）
  - OpenAPI 文档已确认：/docs /redoc /openapi.json（WS 不在 OpenAPI 内）

---

## 8. 已确认的关键工程决策

- 使用模块化单体（Modular Monolith），按域拆：users/auth/rooms/messages/notifications/realtime
- 分层：router（薄）/service（业务）/repository（DB）
- `Depends(get_db)` 用于请求级 DB Session 管理（yield/close），settings 为进程级缓存（lru_cache）
- email 需 normalize（登录/注册都 lower+strip），避免大小写导致登录失败（已在 AuthService 登录建议加）
- 不再兼容 `avatar_path`（对外字段不返回；DB 内也不再依赖）

---

## 9. 继续工作任务列表（下一步优先级）

1) 完成头像体系闭环：
   - ORM User 增加 avatar_key 字段
   - AvatarService 保存文件返回 key（filename）
   - UserService.update_avatar 写 avatar_key
   - Schema：avatar_key exclude=True，输出 avatar_url
   - 新增 `GET /avatar/{key}` endpoint（FileResponse）
   - 上传接口只返回 avatar_url
2) 完成用户 PATCH（partial update）闭环：
   - PATCH /users/me：UserPatch + exclude_unset merge
   - username 唯一性校验
   - password 修改：hash
   - auto_accept 更新
3) 清理与规范：
   - 添加 __init__.py
   - gitignore: __pycache__, data, uploads
4) 之后再迁移 rooms/messages/notifications & WS 协议规范化（v/type/payload/request_id/topic/ack/topic-subscribe 等）

---

## 10. 我希望你在新对话里怎么做

- 先询问我当前代码是否已按 9-1 完成（avatar endpoint / schema 变化）
- 如果未完成，按“最小可运行 patch”方式给我逐文件修改清单 + 代码块
- 我会贴报错日志，你需要根据报错快速定位（比如 ORM 列不存在、schema 字段缺失、路径问题、content-type 等）
- 优先保证旧库可读写 + 新 API 可跑通，再考虑 Alembic、清理旧列等“结构性优化”

（结束）