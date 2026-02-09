# Backend TODO List（Profile / Users）

## 1) 将“更新个人资料”接口由 PUT 改为 PATCH（优先级：最高）
**现状**
- 当前 OpenAPI 为 `PUT /users/me`，请求体 `UserUpdate` 中 `email` 为 required。
- 前端 Profile 页面是“部分字段更新”场景：常见仅改 `username` / `password` / `avatar`，邮箱在 UI 层通常不可编辑。

**问题**
- PUT + email required 会迫使前端每次更新都提交 email（即便不改），不符合“部分更新”语义，也增加出错面（422 / 数据被覆盖风险）。
- 若未来字段增加（auto_accept 等），PUT 的“全量提交”更容易出现旧值覆盖新值的问题。

**目标**
- 支持真正的 partial update：前端只提交变更字段，未提交字段保持不变。

**建议改动**
- 新增或替换为：`PATCH /users/me`
  - Request body 使用 `UserPatch`（所有字段可选，不要 required）
  - 返回 `UserDetailsResponse` 或 `User`（保持与 `GET /users/me` 对齐）
- `PUT /users/me` 处理策略：
  - ✅ 推荐：保留一段时间做兼容，但标记 deprecated（文档注明将下线）
  - 或：直接移除（若你们没有外部依赖）

**实现思路**
- Pydantic Schema：`UserPatch` 所有字段 `Optional[...] = None`
- Service 层：
  - 仅对 `payload` 中非 `None` 字段进行更新（partial merge）
  - 对关键字段做业务校验（username 唯一性等）
- DB 更新方式：
  - 明确区分 “缺失字段” vs “字段显式置空(null)”（如果允许清空 username）
  - 推荐：用 `exclude_unset=True` 提取实际提交字段；只有这些字段参与 update

**验收标准**
- PATCH 仅传 `{ "username": "new" }` 可以成功更新，不需要 email
- PATCH 不传 password 时不会改密码
- PATCH 不传 avatar 时不会改头像
- 未提交字段不会被覆盖为默认值 / null


## 2) 头像更新方式梳理：avatar_base64 vs multipart（建议标准化）
**现状**
- OpenAPI `UserUpdate` 包含 `avatar_base64` 字段（base64 直传）。

**风险**
- base64 会放大请求体积（约 33%），且占用 CPU/内存编码解码，移动端/弱网体验差。

**建议**
- 推荐提供 `POST /users/me/avatar`（multipart/form-data）或 `PATCH /users/me/avatar`：
  - 接收 file
  - 服务端保存后返回新的 `avatar_path`
- 若必须继续支持 base64：
  - 限制最大尺寸（例如 1MB/2MB）
  - 明确接受格式（data URL vs pure base64）
  - 做图片类型校验与安全处理（内容嗅探、防 SVG 注入等）

**验收标准**
- 前端可用文件上传接口完成头像更新，返回可直接展示的 `avatar_path`


## 3) Email 修改策略（明确产品规则 + 后端约束）
**现状**
- 前端计划 v1 将 email 设为不可编辑（只读）。

**建议**
- 如果后端仍允许改 email：
  - 明确是否需要二次验证（发送验证邮件、重新登录等）
  - 否则可先禁用 email 更新（PATCH/PUT 忽略 email 或拒绝更新）

**验收标准**
- API 行为与产品策略一致，避免“前端禁了、后端允许”导致的不一致


## 4) 返回结构统一（建议对齐 GET /users/me）
**建议**
- `PATCH /users/me` 返回结构尽量与 `GET /users/me` 一致（包含 avatar_path / auto_accept 等）
- 方便前端直接 `auth.me = response`，无需额外再 getMe

**验收标准**
- 更新后前端无需额外请求即可刷新 UI（用户名、头像即时更新）


## 5) OpenAPI 文档同步与兼容说明
- 在 OpenAPI 中新增 `PATCH /users/me`，标记 `PUT /users/me` 为 deprecated（如保留）
- 更新 schema：`UserPatch`（全部 optional）
- 写明字段语义：`null` 是否表示清空、缺失是否表示不变

**验收标准**
- 前后端对字段是否可空、是否可缺失有明确共识，减少联调歧义
