# 拾谷 · ShiGu

<div align="center">

> 一套面向「吃谷人」的个人谷子资产管理与检索系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0+-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.14+-red.svg)](https://www.django-rest-framework.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[功能特性](#-核心特性) • [项目架构](#-项目架构) • [快速开始](#-快速开始) • [API 文档](#-api-说明) • [代码结构](#-代码结构)

</div>

---

## 🏗️ 项目架构

```text
┌────────────────┐      REST API      ┌──────────────────────────────┐
│  前端 / 移动端  │ <────────────────> │    ShiGu 后端 (Django/DRF)    │
└────────────────┘   (JWT Auth)       └──────────────┬───────────────┘
                                                     │
                                      ┌──────────────┴───────────────┐
                                      │  核心业务模块 (Apps)           │
                                      ├──────────────────────────────┤
                                      │ 🔐 Users (认证/数据隔离)      │
                                      │ 📦 Goods (资产管理)           │
                                      │ 📍 Location (物理收纳)        │
                                      │ 🤖 BGM (第三方集成)           │
                                      └──────────────┬───────────────┘
                                                     │
               ┌─────────────────────────────────────┴────────────────┐
               ▼                                                      ▼
    ┌────────────────────┐                                 ┌────────────────────┐
    │   数据存储 (DB)     │                                 │   媒体文件 (Media)  │
    ├────────────────────┤                                 ├────────────────────┤
    │ SQLite/PostgreSQL  │                                 │  图片自动压缩存储   │
    └────────────────────┘                                 └────────────────────┘
```

### 数据流说明
1. **身份认证**：用户通过 `/api/users/login/` 获取 JWT，后续所有受限请求需携带 `Authorization: Bearer <token>`。
2. **多用户隔离**：所有业务模型（Goods, StorageNode, etc.）均关联 `user` 字段，后端通过 `IsOwnerOnly` 权限类和 QuerySet 过滤实现物理层隔离。
3. **第三方集成**：BGM 集成采用两步搜索流程，先搜索作品（Subject），再根据作品 ID 拉取角色（Character），最后选择性同步至本地。

---

## 📖 项目简介

**拾谷（ShiGu）** 是一套基于 **Django 6 + Django REST Framework** 构建的谷子（动漫/游戏周边商品）资产管理系统。专为「吃谷人」打造，帮助用户高效管理、检索和定位个人收藏。

### 核心价值

系统聚焦两个核心问题：

- **我有什么谷子？** —— 按 IP / 角色 / 品类等多维度快速检索、统一管理资产。
- **它们都放哪儿了？** —— 用树状的「物理收纳空间」模型精确标记每一件谷子的存放位置。

### 适用场景

- 🎯 **个人收藏管理**：记录和追踪自己的谷子收藏
- 🔍 **快速检索**：通过多维筛选快速找到想要的谷子
- 📍 **位置定位**：精确标记每件谷子的物理存放位置
- 📊 **资产管理**：统计资产价值、购入时间等
- 🔗 **BGM 集成**：从 Bangumi 快速导入 IP 和角色数据

---

## ✨ 核心特性

### 🔐 完善的用户与认证系统
- **JWT 认证**：基于 JWT (JSON Web Token) 的无状态认证机制，支持 Token 颁发与自动校验
- **多用户隔离**：严格的数据所有权校验，确保用户只能访问和操作自己的谷子资产及收纳空间
- **角色权限控制**：内置角色与权限模型，支持精细化的功能访问控制
- **安全防护**：密码哈希存储、敏感接口限流（Throttle）及跨域安全配置

### 🎯 多维检索系统
- **多维度过滤**：支持按 IP、角色（支持多选）、品类、状态、物理位置等维度组合筛选
- **智能搜索**：支持对谷子名称、IP 名称及 IP 关键词进行全文搜索
- **高性能查询**：使用 `select_related` / `prefetch_related` 优化，彻底解决 N+1 查询问题

### 📦 完整的资产管理
- **多角色支持**：单个谷子可关联多个角色（如双人立牌），使用 M2M 关系实现
- **图片管理**：主图 + 补充图片（支持标签），自动压缩至 300KB 以下
- **状态跟踪**：在馆 / 出街中 / 已售出三种状态，清晰追踪资产流转
- **幂等性保护**：基于「IP+角色集合+名称+入手日期+单价」的智能去重，防止重复录入

### 🗂️ 树状收纳空间
- **无限层级**：房间 → 柜子 → 层 → 抽屉/格子，支持任意深度的树状结构
- **路径冗余**：自动维护完整路径字符串（如「书房/书架A/第3层」），便于快速检索和展示
- **级联管理**：删除节点时自动处理子节点和关联商品，确保数据一致性

### 📂 品类树状结构
- **层级分类**：品类支持树状结构（如「周边/吧唧/圆形吧唧」），便于精细化管理
- **路径维护**：自动维护完整路径字符串，支持按路径搜索和展示
- **颜色标签**：支持为品类配置颜色标识（`color_tag`），便于 UI 展示
- **排序控制**：支持自定义排序值（`order`），灵活控制展示顺序

### 🎨 自定义排序系统
- **谷子排序**：支持自定义排序值（`order`），实现拖拽排序功能
- **稀疏排序**：采用稀疏序列设计（步长 1000），避免频繁重排
- **智能重排**：提供管理命令 `rebalance_goods_order`，批量重排排序值
- **品类排序**：品类支持批量更新排序，便于拖拽排序场景

### 🔍 IP 关键词系统
- **多别名支持**：为每个 IP 配置多个搜索关键词（如「星铁」「崩铁」「HSR」）
- **智能匹配**：搜索时自动匹配 IP 名称和所有关键词，提升检索体验

### 🤖 BGM API 集成
- **角色数据导入**：集成 Bangumi (BGM) API，支持搜索 IP 作品并获取角色列表
- **批量创建**：支持从 BGM 搜索结果中批量创建 IP 和角色到本地数据库
- **智能排序**：角色按关系优先级排序（主角 > 配角 > 客串），提升用户体验
- **数据去重**：自动检测已存在的 IP 和角色，避免重复创建

### 🚀 性能优化
- **查询优化**：列表接口使用瘦身序列化器，详情接口提供完整数据
- **分页支持**：谷子列表接口支持分页（默认每页 18 条，可自定义）
- **限流保护**：检索接口限流 60 次/分钟，防止恶意请求
- **CORS 支持**：完善的跨域配置，支持前后端分离部署

### 🎯 IP 作品类型
- **类型分类**：支持作品类型字段（`subject_type`），包括书籍、动画、音乐、游戏、三次元/特摄
- **类型过滤**：支持按作品类型进行筛选和统计

---

## 📑 目录

- [项目简介](#-项目简介)
- [核心特性](#-核心特性)
- [项目架构](#-项目架构)
- [功能概览](#-功能概览)
- [技术栈](#️-技术栈)
- [代码结构](#-代码结构)
- [快速开始](#-快速开始)
- [API 说明](#-api-说明)
- [实现细节](#-实现细节与使用注意)
- [项目亮点](#-项目亮点)
- [部署指南](#-部署指南)
- [未来规划](#-todo--未来规划)
- [贡献指南](#-贡献指南)

---

## 📋 功能概览

### 用户与权限管理（`apps.users`）

#### 数据模型
- **`User`**：自定义用户模型，支持邮箱/用户名登录，关联角色
- **`Role`**：角色模型，定义用户等级和基础权限
- **`Permission`**：权限模型，支持对特定功能模块的精细化控制

#### API 接口
- **认证中心**
  - `POST /api/auth/register/`：用户注册
  - `POST /api/auth/login/`：用户登录，获取 JWT Token
  - `GET /api/auth/me/`：获取当前登录用户信息
  - `POST /api/auth/logout/`：退出登录（客户端清除 Token）

### 谷子资产管理（`apps.goods`）

#### 数据模型
- **`IP`**：作品来源（如「崩坏：星穹铁道」），支持唯一性约束和索引
  - 新增 `subject_type` 字段：作品类型（书籍、动画、音乐、游戏、三次元/特摄）
- **`IPKeyword`**：IP 多关键词表，支持为同一 IP 配置多个别名/搜索关键字
- **`Character`**：角色信息（如「流萤」），关联所属 IP，支持性别字段
  - `avatar` 字段：支持 URL 或相对路径（CharField），便于使用外部图片资源
- **`Category`**：品类维度（吧唧、色纸、立牌、挂件等）
  - 支持树状结构：`parent` 字段实现层级关系
  - `path_name`：冗余的完整路径（如「周边/吧唧/圆形吧唧」），带索引
  - `color_tag`：颜色标签，用于 UI 展示（如 `#FF5733`）
  - `order`：排序值，控制同级节点的展示顺序
- **`Goods`**：核心谷子资产表，支持：
  - 多维关联：IP / 角色（M2M）/ 品类 / 物理位置（`StorageNode`）
  - 基础资产字段：名称、数量、购入单价、入手时间、是否官谷、状态、备注
  - 图片：主图 + 补充图片（`GuziImage`，如背板细节、瑕疵点等）
  - UUID 主键：适合前后端解耦和离线草稿合并场景
  - `order`：自定义排序值（BigInteger），支持拖拽排序功能
- **`GuziImage`**：谷子补充图片表，支持标签分类
- **`Theme`**：主题表，用于对谷子进行「主题维度」的聚合（例如角色生日、活动主题等）
- **`Showcase` / `ShowcaseGoods`**：展柜与展柜-谷子关联表，用于定义「一组要一起展示的谷子」

#### API 接口
- **基础数据 CRUD**
  - `IPViewSet`：IP 作品的完整 CRUD，支持关键词管理和作品类型过滤
  - `CharacterViewSet`：角色的完整 CRUD，支持按 IP 过滤和搜索
  - `CategoryViewSet`：品类的完整 CRUD，支持树状结构、搜索和过滤
    - `GET /api/categories/tree/`：获取品类树（扁平列表，前端组装为树）
    - `POST /api/categories/batch-update-order/`：批量更新品类排序（用于拖拽排序）
- **谷子检索（`GoodsViewSet`）**
  - 列表接口：瘦身序列化器，满足检索页展示需求，支持分页（默认每页 18 条）
  - 详情接口：完整字段 + 补充图片
  - 多维过滤：`ip` / `character` / `category`（支持树形筛选，自动包含子品类）/ `status` / `status__in` / `location` / `is_official`
  - 全文搜索：支持对 `name`、`ip__name`、`ip__keywords__value` 的搜索
  - 幂等创建：防止重复录入相同资产
  - 排序功能：`POST /api/goods/{id}/move/` 调整谷子排序（支持 before/after 位置）
  - 图片上传：
    - `POST /api/goods/{id}/upload-main-photo/`：上传/更新主图
    - `POST /api/goods/{id}/upload-additional-photos/`：上传/更新补充图片（支持批量）
- **主题与展柜**
  - `ThemeViewSet`：主题 CRUD，支持按主题聚合查看相关谷子
  - `ShowcaseViewSet`：展柜 CRUD，支持为展柜关联多件谷子以及排序
- **BGM API 集成**
  - `POST /api/bgm/search-subjects/`：搜索 IP 作品列表（第一步：确定作品）
  - `POST /api/bgm/get-characters-by-subject-id/`：获取指定作品下的角色列表（第二步：选择角色）
  - `POST /api/bgm/create-characters/`：将选择的角色及关联 IP 批量同步到本地数据库

### 物理收纳空间管理（`apps.location`）

#### 数据模型
- **`StorageNode`**：自关联的收纳节点模型，支持无限级层级
  - `path_name`：冗余的完整路径（如「书房/书架A/第3层」），带索引，方便前端直接展示和检索
  - 可配置位置照片、备注、排序值（控制同级显示顺序）

#### API 接口
- **列表 / 创建接口**：用于后台维护收纳结构
- **详情 / 更新 / 删除接口**：
  - 删除节点时自动级联删除子节点
  - 自动取消关联商品的 `location` 字段（设置为 `null`）
- **位置树一次性下发**：`GET /api/location/tree/`，返回扁平列表，由前端在内存组装为树
- **节点商品查询**：`GET /api/location/nodes/{id}/goods/`，支持 `include_children` 参数查询子节点商品

---

## 🛠️ 技术栈

- **后端框架**：Django 6.0+
- **API 框架**：Django REST Framework 3.14+
- **数据库**：SQLite（开发环境，生产环境可切换 PostgreSQL/MySQL）
- **API 文档**：drf-spectacular（提供 OpenAPI Schema / Swagger UI / Redoc）
- **图片处理**：Pillow 10.0+
- **HTTP 客户端**：requests（用于 BGM API 集成）
- **其他依赖**：
  - `django-filter`：高级过滤支持
  - `django-cors-headers`：跨域资源共享
  - `django-extensions`：Django 扩展工具集
  - `drf-spectacular`：自动生成 API 文档与调试页面
  - `gunicorn`：生产环境 WSGI HTTP 服务器

---

## 📁 代码结构

```
ShiGu/
├── ShiGu/                    # Django 项目配置
│   ├── settings.py          # 项目配置（数据库、DRF、CORS、限流等）
│   ├── urls.py              # 路由配置，集成 DRF DefaultRouter
│   └── wsgi.py / asgi.py    # WSGI/ASGI 入口
│
├── apps/
│   ├── users/               # 用户、角色与认证模块
│   │   ├── models.py        # User / Role / Permission
│   │   ├── serializers.py   # 注册、登录、个人信息序列化
│   │   └── views.py         # 认证相关视图函数
│   │
│   ├── goods/               # 谷子核心域模型及 API
│   │   ├── models.py        # IP / IPKeyword / Character / Category / Theme / Goods / GuziImage / Showcase / ShowcaseGoods
│   │   ├── serializers/     # 序列化器模块（按功能拆分）
│   │   │   ├── __init__.py  # 统一导出
│   │   │   ├── ip.py        # IP 相关序列化器
│   │   │   ├── character.py # 角色相关序列化器
│   │   │   ├── category.py  # 品类相关序列化器
│   │   │   ├── goods.py     # 谷子相关序列化器
│   │   │   ├── theme.py     # 主题相关序列化器
│   │   │   ├── showcase.py  # 展柜相关序列化器
│   │   │   ├── bgm.py       # BGM API 相关序列化器
│   │   │   └── fields.py    # 自定义字段（KeywordsField, AvatarField）
│   │   ├── views/           # 视图模块（按功能拆分）
│   │   │   ├── __init__.py  # 统一导出
│   │   │   ├── ip.py        # IP ViewSet
│   │   │   ├── character.py # Character ViewSet
│   │   │   ├── category.py  # Category ViewSet
│   │   │   ├── goods.py     # Goods ViewSet
│   │   │   ├── theme.py     # Theme ViewSet
│   │   │   ├── showcase.py  # Showcase ViewSet
│   │   │   └── bgm.py       # BGM API 视图函数
│   │   ├── management/      # Django 管理命令
│   │   │   └── commands/
│   │   │       └── rebalance_goods_order.py  # 重排谷子排序值命令
│   │   ├── utils.py         # 图片压缩工具函数
│   │   ├── bgm_service.py   # BGM API 服务封装（搜索 IP、获取角色列表）
│   │   ├── admin.py         # Django Admin 后台管理配置
│   │   └── signals.py       # 信号处理（如需要）
│   │
│   └── location/            # 物理收纳节点模型及 API
│       ├── models.py        # 自关联 StorageNode
│       ├── serializers.py   # 基础与树结构序列化器
│       └── views.py         # 列表/创建/详情/更新/删除/树结构/商品查询视图
│
├── gunicorn_config.py       # Gunicorn 生产环境配置文件
├── manage.sh                # 生产环境服务管理脚本（启动/停止/重启等）
│
├── media/                   # 媒体文件目录（图片上传）
│   ├── characters/          # 角色头像
│   └── goods/               # 谷子图片
│       ├── main/           # 主图
│       └── extra/           # 补充图片
│
├── templates/               # 模板目录（可扩展为后台管理/文档展示）
├── db.sqlite3              # SQLite 数据库（开发环境）
├── requirements.txt        # Python 依赖列表
├── api.md                  # 完整 API 文档
└── README.md               # 项目说明文档
```

---

## 🚀 快速开始

### 环境要求

- **Python**: 3.11+（推荐与 Django 6.0 匹配的版本）
- **数据库**: SQLite（开发环境，生产环境支持 PostgreSQL/MySQL）
- **包管理**: pip / venv / poetry 等虚拟环境管理工具

### 安装步骤

#### 1. 克隆项目

```bash
git clone <your-repo-url> ShiGu_backend
cd ShiGu_backend
```

#### 2. 创建虚拟环境

**使用 venv（推荐）**：
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

**使用 poetry（可选）**：
```bash
poetry install
poetry shell
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 配置环境变量（可选）

创建 `.env` 文件（生产环境必需）：
```env
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com
DATABASE_URL=postgresql://user:password@localhost:5432/shiGu_db

# JWT 配置
JWT_SECRET=your-jwt-secret-key
JWT_ACCESS_TTL_SECONDS=604800
```

#### 5. 数据库迁移

```bash
# 创建迁移文件（如需要）
python manage.py makemigrations

# 执行迁移
python manage.py migrate
```

#### 6. 创建超级管理员（可选）

用于访问 Django Admin 后台：
```bash
python manage.py createsuperuser
```

#### 7. 配置 BGM API（可选）

如需使用 BGM API 导入角色数据功能：

1. 在 `apps/goods/bgm_service.py` 中修改 `ACCESS_TOKEN` 变量
2. 获取 Token：访问 [Bangumi API 文档](https://bangumi.github.io/api/) 申请个人访问令牌
3. 如不配置 Token，BGM API 功能仍可使用，但可能受到请求频率限制

#### 8. 启动开发服务器

```bash
python manage.py runserver
```

**默认访问地址**：`http://127.0.0.1:8000/`

- **Django Admin**：`http://127.0.0.1:8000/admin/`
- **API 根路径**：`http://127.0.0.1:8000/api/`
- **BGM API**：
  - `POST /api/bgm/search-characters/`
  - `POST /api/bgm/create-characters/`
- **完整 API 文档**：参考 [`api.md`](api.md)

#### 9. 验证安装

访问 `http://127.0.0.1:8000/api/` 应能看到 DRF 的 API 根视图。

#### 10. 管理命令（可选）

项目提供了管理命令用于维护数据：

```bash
# 重排谷子排序值（消除相同 order 值的堆积）
python manage.py rebalance_goods_order

# 自定义步长和批量大小
python manage.py rebalance_goods_order --step 2000 --batch-size 1000
```

---

## 📖 API 说明

> 📚 **完整 API 文档**请参考 [`api.md`](api.md)，包含详细的请求/响应示例和字段说明。
>
> 📘 **在线接口文档**（drf-spectacular 自动生成）：
> - Swagger UI：`/api/schema/swagger-ui/`
> - Redoc：`/api/schema/redoc/`
> - OpenAPI Schema：`/api/schema/`

### API 基础信息

- **Base URL**: `http://your-domain.com/api/`
- **Content-Type**: `application/json`
- **认证方式**: JWT 认证
  - 需在 Header 中携带: `Authorization: Bearer <your_token>`
  - 获取 Token: `POST /api/auth/login/`

### 接口概览

| 模块 | 端点 | 说明 |
|------|------|------|
| **认证中心** | `/api/auth/` | 注册、登录、个人信息、退出 |
| **基础数据** | `/api/ips/` | IP 作品 CRUD |
| | `/api/characters/` | 角色 CRUD |
| | `/api/categories/` | 品类 CRUD |
| | `/api/categories/tree/` | 品类树结构 |
| | `/api/categories/batch-update-order/` | 批量更新品类排序 |
| **谷子管理** | `/api/goods/` | 谷子检索与 CRUD（支持分页） |
| | `/api/goods/{id}/move/` | 调整谷子排序 |
| | `/api/goods/{id}/upload-main-photo/` | 上传主图 |
| | `/api/goods/{id}/upload-additional-photos/` | 上传补充图片（支持批量） |
| **主题管理** | `/api/themes/` | 主题 CRUD，按主题聚合谷子 |
| **展柜管理** | `/api/showcases/` | 展柜 CRUD |
| | `/api/showcases/{id}/goods/` | 管理展柜下关联的谷子（增删 / 排序） |
| **位置管理** | `/api/location/nodes/` | 收纳节点 CRUD |
| | `/api/location/tree/` | 位置树结构 |
| | `/api/location/nodes/{id}/goods/` | 节点下商品查询 |
| **BGM 集成** | `/api/bgm/search-subjects/` | 搜索作品列表 |
| | `/api/bgm/get-characters-by-subject-id/` | 获取作品角色 |
| | `/api/bgm/create-characters/` | 批量同步到本地 |

### 认证中心
- `POST /api/auth/register/`：用户注册（请求体：`{"username": "xxx", "password": "xxx"}`）
- `POST /api/auth/login/`：用户登录（请求体：`{"username": "xxx", "password": "xxx"}`，返回 `access_token`）
- `GET /api/auth/me/`：获取当前登录用户信息
- `POST /api/auth/logout/`：退出登录

### 基础数据 CRUD

#### IP 作品管理
- `GET /api/ips/`：获取 IP 作品列表（支持 `?search=关键词`、`?name=作品名`、`?subject_type=4` 过滤）
- `GET /api/ips/{id}/`：获取 IP 作品详情
- `POST /api/ips/`：创建 IP 作品（请求体：`{"name": "崩坏：星穹铁道", "keywords": ["星铁", "崩铁", "HSR"], "subject_type": 4}`）
- `PUT/PATCH /api/ips/{id}/`：更新 IP 作品
- `DELETE /api/ips/{id}/`：删除 IP 作品
- `GET /api/ips/{id}/characters/`：获取指定 IP 下的所有角色列表

#### 角色管理
- `GET /api/characters/`：获取角色列表（支持 `?ip=1` 按 IP 过滤，`?search=角色名` 搜索）
- `GET /api/characters/{id}/`：获取角色详情
- `POST /api/characters/`：创建角色（请求体：`{"name": "流萤", "ip_id": 1, "avatar": null, "gender": "female"}`）
- `PUT/PATCH /api/characters/{id}/`：更新角色
- `DELETE /api/characters/{id}/`：删除角色

#### 品类管理
- `GET /api/categories/`：获取品类列表（支持 `?search=品类名` 搜索，`?parent=1` 按父节点过滤）
- `GET /api/categories/{id}/`：获取品类详情
- `POST /api/categories/`：创建品类（支持树状结构，请求体：`{"name": "吧唧", "parent": 1, "color_tag": "#FF5733"}`）
- `PUT/PATCH /api/categories/{id}/`：更新品类
- `DELETE /api/categories/{id}/`：删除品类（级联删除所有子节点）
- `GET /api/categories/tree/`：获取品类树（扁平列表，前端组装为树）
- `POST /api/categories/batch-update-order/`：批量更新品类排序（用于拖拽排序）

### 谷子检索

#### 谷子列表
- `GET /api/goods/`（支持分页，默认每页 18 条，可通过 `?page_size=20` 自定义）
- 查询参数示例：
  - `?ip=1`：按 IP 过滤
  - `?character=5`：按单个角色过滤（包含该角色的谷子）
  - `?category=2`：按品类过滤（自动包含该品类下的所有子品类）
  - `?status=in_cabinet`：按单个状态过滤
  - `?status__in=in_cabinet,sold`：按多个状态过滤
  - `?location=3`：按收纳位置过滤
  - `?is_official=true`：按是否官谷过滤
  - `?search=流萤`：对名称、IP 名称及 IP 关键词进行搜索
  - `?page=1&page_size=20`：分页参数

#### 谷子详情
- `GET /api/goods/{id}/`
- 返回谷子的完整信息（基础信息、价格、时间、位置、备注、补充图片等）

#### 创建/更新谷子
- `POST /api/goods/`：创建谷子（JSON，主图单独上传）
- `PUT/PATCH /api/goods/{id}/`：更新谷子
- `POST /api/goods/{id}/move/`：调整谷子排序（请求体：`{"anchor_id": "uuid", "position": "before|after"}`）
- `POST /api/goods/{id}/upload-main-photo/`：上传/更新主图（multipart/form-data）
- `POST /api/goods/{id}/upload-additional-photos/`：上传/更新补充图片（multipart/form-data，支持批量）
- `DELETE /api/goods/{id}/`：删除谷子

### 收纳位置

#### 收纳节点管理
- `GET /api/location/nodes/`：收纳节点列表
- `POST /api/location/nodes/`：创建收纳节点
- `GET /api/location/nodes/{id}/`：获取节点详情
- `PUT/PATCH /api/location/nodes/{id}/`：更新节点
- `DELETE /api/location/nodes/{id}/`：删除节点（级联删除子节点，取消关联商品）

#### 位置树与商品查询
- `GET /api/location/tree/`：收纳位置树数据一次性下发
- `GET /api/location/nodes/{id}/goods/`：查看指定节点下的谷子
  - `?include_children=true`：包含所有子节点谷子

### BGM 集成
- `POST /api/bgm/search-subjects/`：搜索 IP 作品列表
  - 请求体：`{"keyword": "星穹铁道", "subject_type": 4}`
- `POST /api/bgm/get-characters-by-id/`：获取作品下的角色
  - 请求体：`{"subject_id": 12345}`
- `POST /api/bgm/create-characters/`：批量同步角色到本地
  - 请求体：`{"ip_name": "xxx", "characters": [{"name": "xxx", "avatar": "xxx", "gender": "xxx"}, ...]}`

## 🚢 部署指南

### 生产环境配置

#### 1. 环境变量配置

创建 `.env` 文件或设置系统环境变量：

```env
# 安全配置
SECRET_KEY=your-very-long-random-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# 数据库配置（PostgreSQL 示例）
DATABASE_URL=postgresql://user:password@localhost:5432/shiGu_db

# CORS 配置
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
```

#### 2. 数据库迁移

```bash
python manage.py migrate
python manage.py collectstatic
```

#### 3. 使用 Gunicorn（推荐）

**方式一：使用管理脚本（推荐）**

项目提供了 `manage.sh` 脚本，方便管理生产环境服务：

```bash
# 启动服务
./manage.sh start

# 停止服务
./manage.sh stop

# 重启服务
./manage.sh restart

# 重新加载配置（优雅重启，不中断连接）
./manage.sh reload

# 查看服务状态
./manage.sh status

# 查看日志
./manage.sh logs          # 错误日志
./manage.sh logs access   # 访问日志
```

**方式二：直接使用 Gunicorn**

```bash
# 安装 Gunicorn
pip install gunicorn

# 使用配置文件启动
gunicorn ShiGu.wsgi:application --config gunicorn_config.py

# 或直接指定参数启动
gunicorn ShiGu.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

#### 4. Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 静态文件
    location /static/ {
        alias /path/to/ShiGu_backend/staticfiles/;
    }

    # 媒体文件
    location /media/ {
        alias /path/to/ShiGu_backend/media/;
    }

    # API 代理
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 5. Systemd 服务配置（可选）

创建 `/etc/systemd/system/shigu.service`：

```ini
[Unit]
Description=ShiGu Gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/ShiGu_backend
ExecStart=/path/to/venv/bin/gunicorn ShiGu.wsgi:application --bind 127.0.0.1:8000 --workers 4

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl start shigu
sudo systemctl enable shigu
```

### Docker 部署（可选）

项目可扩展为 Docker 部署，示例 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "ShiGu.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### 性能优化建议

- **数据库**：生产环境使用 PostgreSQL 或 MySQL，配置连接池
- **缓存**：集成 Redis 进行查询缓存和会话存储
- **CDN**：媒体文件使用 CDN 加速
- **静态文件**：使用 Nginx 直接提供静态文件服务
- **监控**：集成 Sentry 等错误监控工具

---

## 💡 实现细节与使用注意

### 数据设计
- **ID 设计**：`Goods` 使用 UUID 主键，适合前后端解耦和离线草稿合并场景
- **多角色关联**：`Goods` 与 `Character` 使用 M2M 关系，支持单个谷子关联多个角色
- **IP 关键词**：通过独立的 `IPKeyword` 表管理，支持搜索时自动匹配

### 图片处理
- **自动压缩**：上传主图或补充图时自动压缩到约 300KB（`apps/goods/utils.compress_image`）
- **格式转换**：自动将 RGBA/LA/P 模式转换为 RGB（JPEG 不支持透明度）
- **独立上传**：主图通过 `POST /api/goods/{id}/upload-main-photo/` 接口单独上传
- **应用范围**：主图、角色头像、补充图片均支持自动压缩

### 幂等性保护
- **去重规则**：`GoodsViewSet.perform_create` 基于「IP+角色集合（顺序无关）+名称+入手日期+单价」做幂等写入
- **智能匹配**：角色集合通过排序后比较，确保顺序无关的去重判断

### 多用户隔离与权限
- **数据所有权**：所有核心模型（`Goods`、`Theme`、`Showcase`、`StorageNode`）均通过 `user` 字段与用户关联。
- **物理隔离**：系统通过 `IsOwnerOnly` 权限类拦截未授权访问，并在 `get_queryset` 中自动应用 `filter(user=request.user)`，确保用户数据的物理隔离。
- **公共元数据**：`IP`、`Character`、`Category` 属于公共元数据，默认所有人可查，但只有管理员（`role="admin"`）可进行增删改操作。

### 搜索体验
- **多字段搜索**：`Goods` 支持对名称、IP 名称及 IP 关键词（`IPKeyword`）的轻量搜索
- **关键词管理**：IP 关键词在序列化器中支持字符串数组读写，创建/更新时自动同步

### 品类树状结构
- **层级设计**：`Category` 采用自关联设计，支持无限级层级（类似 `StorageNode`）
- **路径维护**：`path_name` 字段自动维护完整路径（如「周边/吧唧/圆形吧唧」），带索引便于搜索
- **颜色标签**：`color_tag` 字段支持配置颜色标识（如 `#FF5733`），便于 UI 展示
- **排序控制**：`order` 字段控制同级节点的展示顺序，支持批量更新排序
- **级联删除**：删除品类节点时自动级联删除所有子节点

### 自定义排序系统
- **谷子排序**：`Goods.order` 字段（BigInteger）支持自定义排序，默认排序规则为 `order, -created_at`
- **稀疏排序**：采用稀疏序列设计（步长 1000），避免频繁重排导致的性能问题
- **拖拽排序**：`POST /api/goods/{id}/move/` 接口支持调整谷子排序（before/after 位置）
- **智能重排**：当排序值冲突时，自动在锚点附近重排局部窗口，避免大范围更新
- **管理命令**：`python manage.py rebalance_goods_order` 可批量重排所有谷子的排序值

### 分页功能
- **默认分页**：谷子列表接口默认每页 18 条记录
- **自定义分页**：支持通过 `?page_size=20` 自定义每页数量（最大 100 条）
- **分页响应**：返回格式包含 `count`、`page`、`page_size`、`next`、`previous`、`results`

### 角色头像字段
- **字段类型**：`Character.avatar` 从 `ImageField` 改为 `CharField`，支持 URL 或相对路径
- **应用场景**：便于使用外部图片资源（如 BGM API 返回的头像 URL），无需本地存储

### IP 作品类型
- **字段类型**：`IP.subject_type` 字段支持作品类型分类（1=书籍, 2=动画, 3=音乐, 4=游戏, 6=三次元/特摄）
- **过滤支持**：支持按作品类型进行筛选（`?subject_type=4` 或 `?subject_type__in=2,4`）

### 角色性别字段
- **字段类型**：`Character` 支持 `gender` 字段，取值为 `male` / `female` / `other`，默认 `other`
- **应用场景**：便于后续做统计或展示优化（如按性别筛选、统计等）

### 收纳节点维护
- **路径自动生成**：`StorageNodeSerializer` 若未提供 `path_name`，会基于父节点自动生成
- **路径同步更新**：更新父子关系或名称时会同步刷新路径
- **级联删除**：删除节点会递归删除子节点，并将关联谷子的 `location` 置空，避免悬挂引用
- **级联查询**：`StorageNodeGoodsView` 支持 `include_children` 参数做级联查询

### 品类树形筛选
- **自动包含子品类**：`GoodsFilter.filter_category_tree` 方法实现树形筛选，当按品类过滤时自动包含该品类下的所有子品类
- **递归查询**：使用递归算法获取指定品类的所有后代品类 ID，确保筛选结果完整
- **性能优化**：使用 `prefetch_related` 预加载子节点，避免递归过程中的 N+1 查询问题

### 性能优化
- **查询优化**：列表接口使用 `select_related` / `prefetch_related` 规避 N+1 查询
- **序列化优化**：列表接口使用瘦身序列化器，详情接口提供完整数据
- **分页优化**：谷子列表接口支持分页，减少单次响应数据量
- **限流保护**：检索接口限流 60 次/分钟，防止恶意请求
- **代码结构**：序列化器和视图按功能模块拆分，提高代码可维护性和可读性

### 跨域与安全
- **CORS 配置**：开发环境默认开放本地常见端口的 CORS
- **生产环境**：建议使用 `CORS_ALLOWED_ORIGINS` 明确指定允许的域名

### 媒体与静态文件
- **开发环境**：媒体目录为 `media/`，由 Django 开发服务器提供
- **生产环境**：静态文件收集至 `staticfiles/`，媒体文件需用 Nginx 等 Web 服务器托管

### 数据库与环境
- **开发环境**：默认使用 SQLite
- **生产环境**：`SECRET_KEY`、`DEBUG`、数据库等生产参数需通过环境变量或独立配置文件覆盖
- **时区配置**：默认使用 UTC 时区，生产环境建议根据实际需求调整 `TIME_ZONE` 设置
- **语言配置**：默认使用英文（`en-us`），可根据需要修改 `LANGUAGE_CODE`

### 管理命令
- **重排排序值**：`python manage.py rebalance_goods_order` 用于重排谷子的 `order` 字段
  - 消除历史上相同 `order` 值的堆积
  - 重新赋值为稀疏等差序列（默认步长 1000）
  - 支持自定义步长（`--step`）和批量大小（`--batch-size`）参数


---

## 🎯 项目亮点

1. **完整的 CRUD 接口**：所有基础数据（IP、角色、品类）和核心数据（谷子）都提供完整的增删改查接口
2. **高性能检索**：通过查询优化和瘦身序列化器，确保列表检索的响应速度
3. **智能去重**：基于业务逻辑的幂等性保护，防止重复录入
4. **灵活的收纳管理**：树状结构 + 路径冗余，既支持复杂层级又便于快速检索
5. **品类树状结构**：品类支持树状层级分类，便于精细化管理，支持颜色标签和自定义排序
6. **自定义排序系统**：谷子和品类都支持自定义排序，实现拖拽排序功能，采用稀疏序列设计避免频繁重排
7. **多角色支持**：M2M 关系设计，完美支持双人/多人谷子场景
8. **关键词搜索**：IP 关键词系统，提升搜索体验
9. **图片自动压缩**：智能压缩算法，上传时自动压缩，节省存储空间
10. **BGM API 集成**：无缝对接 Bangumi API，快速导入 IP 和角色数据，提升数据录入效率
11. **生产环境工具**：提供 `manage.sh` 脚本和 `gunicorn_config.py` 配置，便于生产环境部署和管理
12. **代码结构优化**：序列化器和视图按功能模块拆分，提高代码可维护性

---

## 📝 TODO / 未来规划

- [ ] **统计与可视化**
  - 资产价值统计、购入时间分布
  - IP / 角色 / 品类占比等统计图表
  - 数据导出（Excel/CSV）
- [ ] **多端与备份**
  - 数据加密备份、多设备同步
  - 支持导出 / 导入功能
- [ ] **AI 识别谷子**
  - 支持 AI 识别谷子的角色、IP 和谷子类型
  - 自动标签生成
- [ ] **高级搜索**
  - 全文搜索引擎集成（Elasticsearch/Meilisearch）
  - 价格区间、日期范围等高级筛选
- [ ] **批量操作**
  - 批量导入谷子数据
  - 批量更新状态、位置等

---

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 贡献方式

1. **报告问题**：发现 Bug 或有功能建议？请提交 [Issue](../../issues)
2. **提交代码**：Fork 项目 → 创建功能分支 → 提交更改 → 发起 Pull Request
3. **改进文档**：完善文档、添加示例、修正错别字都欢迎

### 开发规范

- 遵循 PEP 8 Python 代码规范
- 提交前运行测试：`python manage.py test`
- 保持代码注释清晰，特别是复杂逻辑
- 提交信息使用清晰的中文或英文描述

### Pull Request 流程

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

---

## 🙏 致谢

- [Django](https://www.djangoproject.com/) - Web 框架
- [Django REST Framework](https://www.django-rest-framework.org/) - RESTful API 框架
- [Bangumi API](https://bangumi.github.io/api/) - 动漫数据来源

---

## 🌍 English Overview

**ShiGu** is a focused inventory and location management system for anime / game merch collectors. It provides:

- A rich **goods model** linking IP, character (M2M), category and physical storage location
- High‑performance **search & filter APIs** with index‑friendly fields and basic idempotent create logic
- A tree‑like **storage node model** to describe real‑world spaces (room → cabinet → shelf → drawer)
- **IP keyword system** for enhanced search experience
- **Automatic image compression** to optimize storage usage
- **BGM API integration** for quick IP and character data import

The name **ShiGu** plays on the Chinese words for "eating merch" (吃谷) and "picking up / collecting" (拾谷), emphasizing both the emotional side of collecting and the structured act of organizing your collection.

---

<div align="center">

**拾谷 · ShiGu** - 让每一件谷子都有归属 ✨

Made with ❤️ for 吃谷人

[⬆ 返回顶部](#拾谷--shigu)

</div>
