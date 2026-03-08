# 数据库迁移步骤

本项目在后端重构过程中对数据库结构进行了调整。  
迁移采用 **分阶段迁移策略**：

1. 先新增新字段 / 新表，保持旧字段仍然可用
2. 等新代码稳定运行后，再统一删除旧字段

所有迁移脚本位于 `scripts/migrate/` 目录。

## 迁移脚本

- 入口脚本migrate.py,用于串联执行各个迁移脚本
  - migrate_avatar_key.py
    - 为 `users` 表新增 `avatar_key` 字段
    - 将原 `avatar_path` 中的文件名提取出来写入 `avatar_key`
    - 例如：`/avatars/xxx.jpg` -> `xxx.jpg`
    - 当前阶段保留 `avatar_path` 字段，待新代码稳定运行后再统一删除旧字段

  - migrate_room_domain.py
    - 为 `room_members` 表新增 `role` 字段
    - 将原 `user_type` 字段内容复制到 `role`
    - 当前阶段保留 `room_members.user_type` 字段，待新代码稳定运行后再统一删除旧字段
    - 当前阶段保留 `rooms.is_active` 字段，待运行时房间状态方案稳定后再统一删除旧字段
  
- 迁移清理脚本migrate_cleanup_legacy_fields.py
  - 上述迁移脚本执行后，确认系统运行没有问题后，再执行该脚本清理剩余内容
  - 删除以下字段
    - users.avatar_path
    - room_members.user_type
    - rooms.is_active
