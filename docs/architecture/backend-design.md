# iCinema 后端系统设计

版本：v0.1  
状态：Draft

---

# 1 文档定位

本文档描述 iCinema 后端系统的整体设计，定义后端的模块划分、分层结构、核心数据对象、接口组织方式与实时通信职责。

本文档聚焦后端层面的系统设计，不展开前端页面、组件结构与交互细节。

---

# 2 后端目标

后端系统负责承载 iCinema 的核心业务逻辑与状态管理，主要包括：

- 用户认证与用户资料管理
- 房间与成员关系管理
- 房间消息存储与查询
- 房间播放状态维护
- WebSocket 实时事件通信
- 资源访问接口

后端对外提供 HTTP API 与 WebSocket 两类能力，以支撑前端的业务操作与实时同步。

---

# 3 技术栈

后端采用以下技术栈：

- FastAPI
- SQLAlchemy Async
- SQLite
- JWT
- WebSocket

系统采用模块化单体架构，在单一服务进程内组织多个业务模块。

---

# 4 系统结构

后端以 FastAPI 应用为入口，按照业务领域拆分模块，并通过统一配置、数据库访问层、异常处理层与认证机制进行支撑。

整体结构包括：

- 应用入口层
- 核心基础设施层
- 业务模块层
- 实时通信层

---

# 5 模块划分

后端模块按业务领域划分。

## 5.1 auth

负责认证相关能力，包括：

- 登录
- 注册
- token 签发
- 当前用户识别

## 5.2 users

负责用户资料相关能力，包括：

- 当前用户信息查询
- 用户信息修改
- 用户头像上传与访问

## 5.3 rooms

负责房间相关能力，包括：

- 房间创建
- 房间信息查询
- 房间成员关系管理
- 房间播放状态维护

## 5.4 messages

负责房间消息相关能力，包括：

- 消息发送
- 消息存储
- 消息历史查询

## 5.5 realtime

负责 WebSocket 实时通信能力，包括：

- 连接建立
- 房间事件分发
- 消息广播
- 播放状态同步

---

# 6 分层结构

每个业务模块内部采用统一的分层结构：

- router
- service
- repository
- models
- schemas

## 6.1 router

router 层负责：

- 定义接口路径
- 接收请求参数
- 调用 service
- 返回响应对象

router 层不承载复杂业务逻辑。

## 6.2 service

service 层负责：

- 业务规则处理
- 权限校验
- 多对象协同逻辑
- 调用 repository 完成数据读写

service 层是业务逻辑的主要承载层。

## 6.3 repository

repository 层负责：

- 数据库查询
- 数据持久化
- ORM 对象读写

repository 层不处理业务规则。

## 6.4 models

models 层定义数据库实体对象，用于描述系统核心数据结构。

## 6.5 schemas

schemas 层定义请求与响应数据结构，用于约束 API 输入输出。

---

# 7 核心基础设施

## 7.1 配置管理

系统通过统一配置模块管理应用配置，包括：

- 应用环境
- JWT 配置
- 数据目录
- 数据库文件路径
- 上传目录路径

配置在进程启动后统一加载，并在运行期复用。

## 7.2 数据库访问

系统通过 SQLAlchemy Async 管理数据库访问。

数据库访问层负责：

- 创建 async engine
- 创建 sessionmaker
- 提供请求级数据库会话
- 管理会话生命周期

## 7.3 安全机制

系统通过 JWT 实现身份认证。

安全层负责：

- 密码哈希与校验
- access token 生成
- refresh token 生成
- token 解析与用户身份识别

## 7.4 异常处理

系统通过统一异常体系处理业务错误与接口错误。

异常处理层负责：

- 定义业务异常类型
- 将异常转换为标准 HTTP 响应
- 统一错误返回格式

---

# 8 HTTP 接口组织

HTTP 接口采用版本化前缀组织：

`/api/v1`

接口按业务模块划分路由。

## 8.1 认证接口

- `/api/v1/auth`

## 8.2 用户接口

- `/api/v1/users`

## 8.3 房间接口

- `/api/v1/rooms`

## 8.4 消息接口

- `/api/v1/messages`
- 或按房间组织为 `/api/v1/rooms/{room_id}/messages`

---

# 9 实时通信设计

系统通过 WebSocket 提供房间内实时通信能力。

WebSocket 主要用于：

- 房间成员实时事件同步
- 聊天消息广播
- 播放状态同步

实时通信层负责维护连接状态，并根据房间范围进行事件分发。

---

# 10 核心数据对象

## 10.1 User

表示系统用户。

主要字段包括：

- id
- email
- username
- hashed_password
- avatar_key
- auto_accept
- created_at

## 10.2 Room

表示观影房间。

主要字段包括：

- id
- name
- description
- owner_id
- created_at

## 10.3 RoomMember

表示用户与房间之间的成员关系。

主要字段包括：

- id
- room_id
- user_id
- role
- joined_at

## 10.4 Message

表示房间内消息。

主要字段包括：

- id
- room_id
- user_id
- content
- created_at

## 10.5 PlaybackState

表示房间当前播放状态。

主要字段包括：

- room_id
- media_url
- position
- state
- updated_at

---

# 11 资源访问设计

后端负责提供资源访问接口。

当前资源类型包括用户头像。

头像在数据库中保存为 `avatar_key`，接口返回 `avatar_url`，资源通过独立路由访问。

资源访问形式：

`GET /avatar/{key}`

---

# 12 认证与权限边界

系统通过 Bearer Token 识别当前用户身份。

权限控制以业务模块为中心进行划分：

- 用户仅能修改自己的资料
- 房间相关操作基于成员关系与房间角色进行校验
- 消息与播放状态操作基于房间上下文进行校验

权限判断由 service 层负责。

---

# 13 请求处理流程

一次典型的后端请求处理流程如下：

1. 请求进入 FastAPI 路由
2. router 解析参数并注入依赖
3. service 执行业务逻辑与权限校验
4. repository 进行数据库读写
5. service 组织结果
6. router 返回响应 schema

对于实时通信请求，处理流程为：

1. 客户端建立 WebSocket 连接
2. 服务端识别用户身份与连接上下文
3. 客户端发送房间事件或播放事件
4. realtime 模块处理事件并广播给目标连接

---

# 14 系统设计原则

后端系统设计遵循以下原则：

1. 模块按业务领域划分
2. router 保持轻量
3. service 承载业务逻辑
4. repository 负责数据访问
5. HTTP 与 WebSocket 职责分离
6. 数据模型与接口模型分离
7. 资源访问路径与数据库存储解耦