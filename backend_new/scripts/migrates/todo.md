# 数据库迁移步骤

本项目在后端重构过程中对数据库结构进行了调整。  
迁移采用 **分阶段迁移策略**：

1. 先新增新字段 / 新表，保持旧字段仍然可用
2. 等新代码稳定运行后，再统一删除旧字段

所有迁移脚本位于 `scripts/migrates/` 目录。

## 迁移脚本

- 入口脚本 `migrate.py`，用于串联执行各个迁移脚本
  - `migrate_user_domain.py`
    - 为 `users` 表新增 `avatar_key` 字段
    - 将原 `avatar_path` 中的文件名提取出来写入 `avatar_key`
    - 例如：`/avatars/xxx.jpg` -> `xxx.jpg`
    - 当前阶段保留 `avatar_path` 字段，待新代码稳定运行后再统一删除旧字段

  - `migrate_room_domain.py`
    - 为 `room_members` 表新增 `role` 字段
    - 将原 `user_type` 字段内容复制到 `role`
    - 当前阶段保留 `room_members.user_type` 字段，待新代码稳定运行后再统一删除旧字段
    - 当前阶段保留 `rooms.is_active` 字段，待运行时房间状态方案稳定后再统一删除旧字段

  - `migrate_room_settings.py`
    - 创建或重建 `room_settings` 表
    - 回填每个房间的默认房间设置

  - `migrate_room_join_request.py`
    - 创建 `room_join_requests` 表及其索引/触发器

  - `migrate_notification_domain.py`
    - 重建 `notifications` 表及其索引

  - `migrate_message_domain.py`
    - 创建或重建 `messages` 表
    - 将旧文本消息迁移为新的结构化消息内容

  - `migrate_media_assets.py`
    - 创建媒体资源相关表：
      - `media_assets`
      - `user_avatar_assets`
      - `user_sticker_library_items`
      - `message_resource_refs`
      - `user_emoji_usages`
    - 清理旧的本地 emoji 表与错误索引
    - 迁移历史头像资源关系
  
- 迁移清理脚本 `migrate_cleanup_legacy_fields.py`
  - 上述迁移脚本执行后，确认系统运行没有问题后，再执行该脚本清理剩余内容
  - 删除以下字段
    - users.avatar_path
    - room_members.user_type
    - rooms.is_active
