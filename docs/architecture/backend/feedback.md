# 站内反馈与站点权限

本文记录 iCinema 站内反馈模块的后端设计、前端入口和权限边界。

## 目标

站内反馈用于让普通用户在站内提交问题、建议、体验反馈和其他信息。反馈可以携带多张截图，管理员可以在专用管理页面查看、筛选和更新处理状态。

该模块不依赖 GitHub Issue，也不复用房间管理员权限。房间权限仍只作用于单个房间；反馈管理属于站点级能力。

## 站点角色与权限

站点权限位于 `backend/app/modules/site`。

- `SiteRole.USER`：普通站点用户。
- `SiteRole.ADMIN`：站点管理员。
- `SitePermission.CREATE_FEEDBACK`：提交反馈。
- `SitePermission.VIEW_OWN_FEEDBACK`：查看自己的反馈。
- `SitePermission.VIEW_ALL_FEEDBACK`：查看全站反馈。
- `SitePermission.UPDATE_FEEDBACK`：更新反馈处理状态和备注。
- `SitePermission.DELETE_FEEDBACK`：预留的删除权限。

当前默认新用户为 `user`。如需开放反馈管理页，需要把对应用户的 `users.site_role` 设置为 `admin`。

## 数据模型

反馈模型位于 `backend/app/modules/feedback/models.py`。核心表为 `feedbacks`，截图使用 `feedback_screenshots` 关联表保存一对多关系。

- `creator_id`：反馈提交者。
- `handled_by_id`：最近一次处理人。
- `feedback_type`：`bug`、`suggestion`、`experience`、`other`。
- `page`：反馈关联页面，例如 `home`、`room`、`contact`、`other`。
- `title` / `description`：反馈标题与描述。
- `status`：`open`、`reviewing`、`resolved`、`closed`。
- `admin_note`：管理员处理备注。
- `handled_at`：处理时间。

`feedback_screenshots` 字段包括：

- `feedback_id`：所属反馈。
- `asset_id`：截图资源。
- `sort_order`：截图顺序。

## 图片资源

反馈截图新增媒体类型 `feedback_image`，不复用普通聊天图片的生命周期策略。单条反馈当前最多上传 6 张截图。

- 支持格式：PNG、JPEG、WebP。
- 入口：`MediaService.create_feedback_image_asset_in_tx`。
- 保存目录：`settings.feedback_image_dir_path`。
- `expires_at` 为 `None`，不会按普通 `image` 的一个月生命周期自动过期。
- 读取走受保护接口，只有反馈提交者或具备 `VIEW_ALL_FEEDBACK` 的站点管理员可以访问。

## API

反馈接口挂载在 `/api/v1/feedback`。

- `POST /feedback`：提交反馈，支持 multipart 表单和可选多张截图，字段名为 `screenshots`。
- `GET /feedback`：获取当前用户自己的反馈列表。
- `GET /feedback/{feedback_id}`：获取单条反馈；提交者和站点管理员可访问。
- `GET /feedback/admin`：管理员获取全站反馈列表。
- `PATCH /feedback/admin/{feedback_id}`：管理员更新状态和处理备注。
- `GET /feedback/assets/{asset_id}`：读取反馈截图文件。

错误原因：

- `site_permission_denied`：缺少站点级权限。
- `feedback_not_found`：反馈不存在。
- `feedback_permission_denied`：无权访问该反馈或截图。

## 前端

前端联系页为 `联系与反馈`，位于 `frontend/src/pages/contact/ContactPage.vue`。

用户可以选择反馈类型、关联页面、填写标题与描述，并上传多张截图。截图选择区使用固定方格 grid，已选择图片显示为预览图，加号上传入口始终保持在最后。

管理员页面位于 `frontend/src/pages/feedback-admin/FeedbackAdminPage.vue`。侧边栏仅在当前用户包含 `view_all_feedback` 权限时显示 `反馈管理` 入口。截图通过前端 API 获取 Blob 后打开，避免绕过鉴权请求直接访问受保护资源。

## 测试

后端测试覆盖：

- 站点权限映射。
- 反馈模型关系。
- 用户提交反馈和截图。
- 用户只查看自己的反馈。
- 管理员查看和更新反馈。
- 非管理员访问管理接口被拒绝。
- 截图资源仅提交者和管理员可读取。

推荐运行：

```bat
backend\test_backend.bat tests\unit\modules\site\test_permissions.py tests\unit\modules\feedback\test_feedback_model.py tests\api\test_feedback_api.py tests\api\test_auth_and_users_api.py tests\unit\modules\media\test_media_service.py
```
