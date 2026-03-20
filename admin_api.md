# 后台管理 API 说明（Admin）

面向：后台管理前端（Vue / React 等）

本文档描述**仅管理员**可调用的专用接口，以及管理员使用既有业务 API 时的权限差异。字段级细节仍以根目录 [`api.md`](api.md) 为准。

---

## 一、认证与准入

### 1.1 认证方式

与主站一致：

- 请求头：`Authorization: Bearer <access_token>`
- Token 通过 `POST /api/auth/login/` 或 `POST /api/auth/register/` 获取（见 `api.md`）。

### 1.2 谁算「管理员」

后端根据当前登录用户在数据库中的 **`users.Role.name`** 判断（不区分大小写）：名称为 `Admin` 时视为管理员（与 `python manage.py seed_users` 创建的角色一致）。

### 1.3 前端如何控制「仅管理员进后台」

1. 用户登录后调用 `GET /api/auth/me/`。
2. 若响应中 `role` 为 **`Admin`**，允许进入后台路由；否则不展示后台入口，并拦截前端路由。

> 说明：`/api/admin/*` 在服务端也会校验管理员身份；非管理员调用将返回 **403 Forbidden**（已登录）或 **401**（未带 Token / Token 无效）。

---

## 二、专用接口：`/api/admin/`

以下路径**全部**要求：已登录 + 管理员。

### 2.1 用户列表（分页）

| 项目 | 说明 |
|------|------|
| **URL** | `GET /api/admin/users/` |
| **查询参数** | `page`（默认 1）、`page_size`（默认 20，最大 100） |

**响应体**（与 DRF 分页一致）：

```json
{
  "count": 100,
  "next": "http://host/api/admin/users/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "username": "admin",
      "role": { "id": 1, "name": "Admin", "created_at": "..." },
      "is_active": true,
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

### 2.2 用户详情

| 项目 | 说明 |
|------|------|
| **URL** | `GET /api/admin/users/{id}/` |

响应为单条用户对象（结构同 `results[]` 元素）。**不返回密码或密码哈希。**

### 2.3 新建用户

| 项目 | 说明 |
|------|------|
| **URL** | `POST /api/admin/users/` |
| **Content-Type** | `application/json` |

**请求体示例**：

```json
{
  "username": "newuser",
  "password": "至少6位",
  "role_id": 2
}
```

- `role_id`：对应 `GET /api/admin/roles/` 返回的 `id`（如普通用户 `User`、管理员 `Admin`）。

**响应**：201，body 为创建后的用户对象（含嵌套 `role`，无密码）。

### 2.4 更新用户（含部分更新）

| 项目 | 说明 |
|------|------|
| **URL** | `PUT /api/admin/users/{id}/` 或 `PATCH /api/admin/users/{id}/` |

**请求体字段（均可按需组合）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `role_id` | 整数 | 角色主键 |
| `is_active` | 布尔 | 是否启用；停用后台账号可置 `false` |
| `password` | 字符串 | 新密码（可选，长度 6～128） |

**响应**：200，body 为更新后的用户对象。

> **不建议**通过 API 物理删除用户：`User` 与谷子、主题等为级联关系，误删会造成大量业务数据丢失。请优先使用 `is_active: false` 停用账号。

### 2.5 角色枚举（下拉框）

| 项目 | 说明 |
|------|------|
| **URL** | `GET /api/admin/roles/` |

返回 `users.Role` 全表列表，用于分配用户时的角色选择（如 `Admin`、`User`）。

**响应示例**：

```json
[
  { "id": 1, "name": "Admin", "created_at": "..." },
  { "id": 2, "name": "User", "created_at": "..." }
]
```

> 注意：此处「角色」指**账号角色**（`users.Role`）。作品下的**登场角色**（`goods.Character`）仍使用业务接口 `GET /api/characters/` 等，勿混淆。

---

## 三、复用业务 API：管理员与普通用户差异

管理员使用同一批 `/api/*` 接口时，行为差异如下表。详细 URL、请求体与 `api.md` 一致。

| 资源 | Base URL | 管理员相对普通用户的差异 |
|------|----------|-------------------------|
| 谷子 | `/api/goods/` | 列表/详情/统计等 **可见全站用户**的谷子；列表支持按归属用户筛选：`GET /api/goods/?user={user_id}`（普通用户传他人 `user` 只会得到空结果，无越权）。**新建谷子**时，管理员可在请求体中增加 **`user_id`**（用户主键），将谷子归属到指定用户；不传则归属当前登录管理员。 |
| 主题 | `/api/themes/` | 列表/详情等为全站主题；列表支持 `GET /api/themes/?user={user_id}`。**新建主题**时，管理员可传 **`user_id`** 指定归属用户；不传则归属当前登录用户。 |
| IP 作品 | `/api/ips/` | 任意已登录用户可读列表/详情；**创建/修改/删除**仅管理员。 |
| 品类 | `/api/categories/` | 同上。 |
| 作品角色 | `/api/characters/` | 同上（对应模型 `Character`，非 `users.Role`）。 |

谷子、主题请求中的 **`user_id`** 仅管理员可用；普通用户传入会校验失败。

---

## 四、与 OpenAPI / Swagger 的关系

项目已配置 `drf-spectacular`，可在 `GET /api/schema/` 或 Swagger UI 中查看；后台相关接口标签为 **`Admin`**。

---

## 五、常见错误码

| HTTP 状态 | 含义 |
|-----------|------|
| 401 | 未携带 Token、Token 无效或用户已停用 |
| 403 | 已登录但非管理员（访问 `/api/admin/*` 时） |
| 400 | 参数校验失败（如用户名已存在、非法 `role_id`） |

---

## 六、与 Django 自带后台的关系

- Django Admin 站点仍为：`/admin/`（基于 session，与 JWT 后台独立）。
- 本文档描述的是 **REST `api/admin/`**，供独立后台前端使用，两者可同时存在。
