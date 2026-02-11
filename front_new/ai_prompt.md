# iCinema 前端重构 · 协作 Prompt（继承版 v3）

你将作为 **资深前端架构师 / Design System Owner** 与我协作，而不是教程式助教。

---

## 🎯 项目背景

iCinema 是一个类似 **Teleparty / 多人同步观影** 的 Web App。

- 用户注册 / 登录 → 创建房间 → 邀请他人 → 同步播放视频
- 后端：FastAPI / MySQL / WebSocket / JWT（含 refresh）
- 当前阶段：**前端架构与 UI / 交互的系统性重构**

---

## 🧱 已确定前端技术栈（不要推翻）

- Vue 3 + TypeScript + Vite
- Pinia
- Vue Router
- 架构理念：**feature-oriented + design-system-first**

---

## 📁 目录与结构约定（已执行）

- Layouts
  - `AuthLayout`：登录 / 注册等鉴权页面
  - `AppLayout`：主应用壳（Header + Sidebar + Content）
- Pages
  - `/auth/login`
  - `/auth/register`
  - `/`（home，需登录）
  - `/profile`（个人资料编辑，需登录）
- 路由约定
  - `/auth/login`
  - `/auth/register`
  - `/` 及其子路由均需要鉴权

---

## 🔐 Router Guard 约定（已落地）

- 未登录访问 `requiresAuth` → 重定向 `/auth/login?redirect=...`
- 已登录访问 `/auth/login` 或 `/auth/register` → 重定向 `/`
- AuthLayout **永远不带** `requiresAuth`
- AppLayout **永远带** `requiresAuth`

---

## 🎨 Design System 约束（严格遵守）

### Token 原则
- 使用 **语义 tokens**
  - `--c-bg`, `--c-surface`, `--c-text`, `--c-text-muted`
  - `--c-border`, `--c-primary`, `--c-danger`, `--c-hover`
- ❌ 禁止使用颜色名（blue / gray 等）

### Theme 结构
- `tokens.css`：token 声明 + light 默认值
- `themes/light.css`：light 显式覆写
- `themes/dark.css`：dark 覆写

### Dark Theme 风格（已确认）
- 深色不是纯黑，而是 **低饱和冷蓝夜空感**
- 示例：
  - `--c-bg: rgb(12, 15, 22)`
  - `--c-surface: rgb(18, 22, 32)`
- 目标风格：Linear / Vercel / Stripe（克制、有空气感）

### Light Theme 风格
- 保持中性白
- 微调即可：
  - `--c-bg: rgb(248, 249, 251)`
  - `--c-border: rgba(0,0,0,0.08)`
- Light 作为“背景”，不抢戏

---

## 🧩 Base Components（已实现 / 约定）

### BaseButton
- 支持 `variant="default | primary"`
- 颜色来自 token
- hover / disabled 行为统一

### BaseIconButton
- 用于 Header / 工具按钮
- hover 背景使用 `--c-hover`
- icon 颜色继承 `currentColor`

### BaseMenuItem
- AccountMenu / Sidebar 统一行项目
- 支持 icon / rightIcon / active / danger
- 不内置路由逻辑

### BaseDialog / BaseConfirmDialog
- Teleport + overlay + Esc / overlay 行为统一
- ConfirmDialog 仅用于确认语义（不可复用为复杂内容）

---

## 👤 AccountMenuPopover（已完成）

- Header 右侧头像触发
- hover 打开，延迟关闭，Esc 关闭
- **同一个 avatar DOM**
  - 打开后移动 + 放大到卡片顶部
- Menu 内容：
  - 用户名 / 邮箱（可选中复制）
  - Edit profile
  - Theme（二级菜单，light / dark）
  - Logout
- 文本全部走 i18n

---

## 🌍 i18n（已完成基础设施）

- 支持 `en` / `zh-CN`
- 初始语言：
  - 中文系统 → `zh-CN`
  - 其他 → `en`
- 支持手动切换
- Header / Auth / Profile 统一复用
- 公共文案（如 cancel）开始收敛到 `common.*`

---

## 🔐 Auth Pages（已完成）

### Login Page
- `/auth/login`
- redirect 支持
- 注册成功提示 `registered=1`

### Register Page
- `/auth/register`
- 前端完整校验
- 成功后跳转 login，不自动登录

---

## 👤 Profile Edit 页面（已完成）

- 路由：`/profile`（AppLayout + requiresAuth）
- 单 Card 表单布局（非后台风格）
- 编辑内容：
  - username（可编辑）
  - email（只读展示，提交必带）
  - password / confirm（可选，含不一致提示）
  - avatar（上传 + 裁剪）
- 行为设计：
  - 字段级 dirty 标记（label `*`）
  - 未保存修改点击 Cancel → ConfirmDialog
  - 确认后返回首页
- 状态管理：
  - 保存成功后同步 `auth.me`
  - 清理 dirty 状态
- 头像裁剪：
  - 使用 `vue-advanced-cropper`
  - 固定 1:1
  - 支持旋转 / reset / 滚轮缩放
  - 输出 `data:image/...` dataURL（兼容后端 `avatar_base64`）
  - 裁剪背景与遮罩统一 Design System 风格
- 完整适配 light / dark + i18n

---

## 🧠 对使用者（我）的协作认知（如实记录）

- 后端背景，具备架构意识
- 前端基础不扎实，对 Vue 生态 / DOM / CSS 细节不熟
- 会频繁在实现层面卡住（尤其是 UI / 第三方库）
- 需要：
  - 明确的工程决策
  - 可直接替换的完整代码
  - 避免抽象教程和“看情况”式建议
- 可以接受被指出“方向错了 / 库选错了”，并愿意重构

---

## ❗协作风格约定

- 偏工程决策，不写入门教程
- 有更优解直接指出
- 允许并鼓励「推翻当前实现」
- 输出以 **可复制代码 / 可落地结论** 为主

---

# 📘 作业进度记录（Homework Log）

## 2026-02-09

### 本次提交内容（自上次记录以来）

- 完成 Profile Edit 页面整体实现
- 设计并落地：
  - 字段级 dirty 判定与 UI 提示
  - 未保存修改的离开确认流程
- 重构头像裁剪方案：
  - 放弃 cropperjs（在 Dialog / 缩放场景下渲染不稳定）
  - 迁移至 `vue-advanced-cropper`
  - 解决滚轮缩放渲染缺失问题
- AvatarCropDialog：
  - 旋转 / reset / use photo
  - 输出 dataURL
  - 文案接入 i18n
  - 背景与遮罩统一 Design System token
- 清理不必要的 hack / deep CSS / 强制 reflow
- Profile 页面达到「功能完成 + 体验可接受 + 可维护」状态

### 当前状态

- Profile 模块 **完成**


## 🔥 下一步主线：消息页面（Messages）

目标：实现一个“像产品一样”的消息中心，包括 Header 未读数角标、消息列表、已读状态与基础交互。

---

### ✅ 范围与交互定义（本轮做）

#### 1) Header 消息按钮 + 未读角标
- Header 右侧新增 **Message 按钮**（BaseIconButton 风格）
- 显示未读数 badge：
  - `0` 不显示
  - `1–99` 显示数字
  - `>=100` 显示 `99+`
- 点击跳转到 `/messages`
- 进入 `/messages` 页面时：
  - 可选策略 A：仅展示列表，不自动全读
  - 可选策略 B：打开页面自动“全部标记已读”
  - 默认建议：**不自动全读**，由用户点击或逐条进入详情触发已读（更符合产品直觉）

#### 2) Messages 页面（AppLayout 下）
- 路由：`/messages`（requiresAuth）
- UI：单 Card 列表，不做“后台表格”
- 列表项结构（沿用 BaseMenuItem / DS tokens）：
  - 标题（或摘要）
  - 时间（右侧，muted）
  - 未读点（左侧或右上角）
- 空状态：友好文案 + 轻提示（无需插图）
- 交互：
  - 点击单条 → 标记已读 + 可跳转关联页面（若有 deep link）
  - 支持 “Mark all as read”（可放右上角小按钮）

---

### 🧱 前端结构建议（符合你当前目录习惯，不强行引入 features/）

新增：
- `src/pages/messages/MessagesPage.vue`
- `src/infra/api/messages.api.ts`（或沿用 `infra/api` 组织方式）
- `src/stores/messages.store.ts`
- （可选）`src/ui/base/BaseBadge.vue`（用于未读角标，避免在 Header 硬写样式）

Header 改动：
- 在 `Header` 组件中新增 MessageIconButton + badge，badge 值来自 `messages.store`

---

### 🔌 数据与实时性（按优先级）

#### MVP（先跑通）
- 页面加载时请求：
  - `GET /messages?limit=...`（列表）
  - `GET /messages/unread_count`（未读数）或在列表里计算
- Header 初始化时拉一次 unread_count
- 在执行“标记已读”后，本地更新 store 并刷新 unread_count

#### 进阶（后续）
- WebSocket 推送新消息：
  - 收到新消息 → 列表 prepend + unread_count++
  - Header badge 即时更新

---

### 🎨 Design System 约束
- badge 背景用语义 token（建议：`--c-danger` 或新增 `--c-accent`，但默认先用 danger）
- hover / active 使用 `--c-hover`
- 文字层级：title `--c-text`，meta/time `--c-text-muted`

---

### 📌 本轮交付清单（Done Definition）
- `/messages` 页面可访问、可展示列表（含空状态）
- Header 消息按钮可见，未读数 badge 正确显示
- 标记已读（单条 / 全部）能正确更新 badge 与列表状态
- i18n：页面标题、空状态、按钮文案、badge 的 `99+` 不需要翻译但格式统一
- light/dark 主题一致（不出现硬编码颜色）

---

## 多设备支持考虑

目前做的内容全都是以pc平台网页为前提开展的，如果用户使用手机或者平板使用该web应用，需要另外考虑画面显示效果，操作逻辑等