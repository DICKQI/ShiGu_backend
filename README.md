# 拾谷 · ShiGu

> 一套面向「吃谷人」的个人谷子资产管理与检索系统

**拾谷（ShiGu）** 是一套基于 **Django 6 + Django REST Framework** 构建的谷子（动漫/游戏周边商品）资产管理系统。它聚焦两个核心问题：

- **我有什么谷子？** —— 按 IP / 角色 / 品类等多维度快速检索、统一管理资产。
- **它们都放哪儿了？** —— 用树状的「物理收纳空间」模型精确标记每一件谷子的存放位置。

---

## ✨ 核心特性

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
- **限流保护**：检索接口限流 60 次/分钟，防止恶意请求
- **CORS 支持**：完善的跨域配置，支持前后端分离部署

---

## 📋 功能概览

### 谷子资产管理（`apps.goods`）

#### 数据模型
- **`IP`**：作品来源（如「崩坏：星穹铁道」），支持唯一性约束和索引
- **`IPKeyword`**：IP 多关键词表，支持为同一 IP 配置多个别名/搜索关键字
- **`Character`**：角色信息（如「流萤」），关联所属 IP，支持头像和性别字段
- **`Category`**：品类维度（吧唧、色纸、立牌、挂件等）
- **`Goods`**：核心谷子资产表，支持：
  - 多维关联：IP / 角色（M2M）/ 品类 / 物理位置（`StorageNode`）
  - 基础资产字段：名称、数量、购入单价、入手时间、是否官谷、状态、备注
  - 图片：主图 + 补充图片（`GuziImage`，如背板细节、瑕疵点等）
  - UUID 主键：适合前后端解耦和离线草稿合并场景
- **`GuziImage`**：谷子补充图片表，支持标签分类

#### API 接口
- **基础数据 CRUD**
  - `IPViewSet`：IP 作品的完整 CRUD，支持关键词管理
  - `CharacterViewSet`：角色的完整 CRUD，支持按 IP 过滤和搜索
  - `CategoryViewSet`：品类的完整 CRUD，支持搜索和过滤
- **谷子检索（`GoodsViewSet`）**
  - 列表接口：瘦身序列化器，满足检索页展示需求
  - 详情接口：完整字段 + 补充图片
  - 多维过滤：`ip` / `characters` / `characters__in` / `category` / `status` / `status__in` / `location`
  - 全文搜索：支持对 `name`、`ip__name`、`ip__keywords__value` 的搜索
  - 幂等创建：防止重复录入相同资产
  - 主图上传：独立接口 `POST /api/goods/{id}/upload-main-photo/`
- **BGM API 集成**
  - `POST /api/bgm/search-characters/`：搜索 IP 作品并获取角色列表（调用 BGM API）
  - `POST /api/bgm/create-characters/`：批量创建 IP 和角色到本地数据库

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
- **图片处理**：Pillow 10.0+
- **HTTP 客户端**：requests（用于 BGM API 集成）
- **其他依赖**：
  - `django-filter`：高级过滤支持
  - `django-cors-headers`：跨域资源共享

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
│   ├── goods/               # 谷子核心域模型及 API
│   │   ├── models.py        # IP / IPKeyword / Character / Category / Goods / GuziImage
│   │   ├── serializers.py   # 列表/详情序列化器，支持基础数据 CRUD 和 BGM API
│   │   ├── views.py         # ViewSet：IP / Character / Category / Goods / BGM API
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

- Python 3.11+（推荐与 Django 6.0 匹配的版本）
- pip / venv 或其他虚拟环境管理工具

### 本地运行步骤

1. **克隆项目**

   ```bash
   git clone <your-repo-url> ShiGu
   cd ShiGu
   ```

2. **创建虚拟环境并安装依赖**

   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate

   pip install -r requirements.txt
   ```

3. **迁移数据库**

   ```bash
   python manage.py migrate
   ```

4. **创建超级管理员（可选，用于 Django Admin）**

   ```bash
   python manage.py createsuperuser
   ```

5. **配置 BGM API（可选，用于角色数据导入）**

   如需使用 BGM API 导入角色数据功能，需要配置 Access Token：
   - 在 `apps/goods/bgm_service.py` 中修改 `ACCESS_TOKEN` 变量
   - 获取 Token：访问 [Bangumi API 文档](https://bangumi.github.io/api/) 申请个人访问令牌
   - 如不配置 Token，BGM API 功能仍可使用，但可能受到请求频率限制

6. **启动开发服务器**

   ```bash
   python manage.py runserver
   ```

   默认访问地址为 `http://127.0.0.1:8000/`：
   - Django Admin：`/admin/`
   - API 根路径：`/api/`
   - BGM API：`/api/bgm/search-characters/`、`/api/bgm/create-characters/`
   - API 文档：参考 `api.md`

---

## 📖 API 说明

### 基础数据 CRUD

#### IP 作品管理
- `GET /api/ips/`：获取 IP 作品列表（支持 `?search=关键词` 和 `?name=作品名` 过滤）
- `GET /api/ips/{id}/`：获取 IP 作品详情
- `POST /api/ips/`：创建 IP 作品（请求体：`{"name": "崩坏：星穹铁道", "keywords": ["星铁", "崩铁", "HSR"]}`）
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
- `GET /api/categories/`：获取品类列表（支持 `?search=品类名` 搜索）
- `GET /api/categories/{id}/`：获取品类详情
- `POST /api/categories/`：创建品类（请求体：`{"name": "吧唧"}`）
- `PUT/PATCH /api/categories/{id}/`：更新品类
- `DELETE /api/categories/{id}/`：删除品类

### 谷子检索

#### 谷子列表
- `GET /api/goods/`
- 查询参数示例：
  - `?ip=1`：按 IP 过滤
  - `?characters=5`：按单个角色过滤
  - `?characters__in=5,6`：按多个角色过滤（包含任意指定角色）
  - `?category=2`：按品类过滤
  - `?status=in_cabinet`：按单个状态过滤
  - `?status__in=in_cabinet,sold`：按多个状态过滤
  - `?location=3`：按收纳位置过滤
  - `?search=流萤`：对名称、IP 名称及 IP 关键词进行搜索

#### 谷子详情
- `GET /api/goods/{id}/`
- 返回谷子的完整信息（基础信息、价格、时间、位置、备注、补充图片等）

#### 创建/更新谷子
- `POST /api/goods/`：创建谷子（JSON，主图单独上传）
- `PUT/PATCH /api/goods/{id}/`：更新谷子
- `POST /api/goods/{id}/upload-main-photo/`：上传/更新主图（multipart/form-data）
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

### BGM API 集成

#### 搜索 IP 作品并获取角色列表
- `POST /api/bgm/search-characters/`：搜索 IP 作品并获取角色列表（调用 BGM API，不写入数据库）
  - 请求体：`{"ip_name": "崩坏：星穹铁道"}`
  - 返回：IP 显示名称和角色列表（包含角色名、关系、头像 URL）

#### 批量创建 IP 和角色
- `POST /api/bgm/create-characters/`：根据角色列表批量创建 IP 和角色到本地数据库
  - 请求体：`{"characters": [{"ip_name": "崩坏：星穹铁道", "character_name": "流萤"}, ...]}`
  - 返回：创建统计和每个角色的处理结果（created / already_exists / error）

> 📖 **完整 API 文档**：请参考 `api.md` 文件，包含详细的请求/响应示例和字段说明。

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

### 搜索体验
- **多字段搜索**：`Goods` 支持对名称、IP 名称及 IP 关键词（`IPKeyword`）的轻量搜索
- **关键词管理**：IP 关键词在序列化器中支持字符串数组读写，创建/更新时自动同步

### 角色性别字段
- **字段类型**：`Character` 支持 `gender` 字段，取值为 `male` / `female` / `other`，默认 `female`
- **应用场景**：便于后续做统计或展示优化（如按性别筛选、统计等）

### 收纳节点维护
- **路径自动生成**：`StorageNodeSerializer` 若未提供 `path_name`，会基于父节点自动生成
- **路径同步更新**：更新父子关系或名称时会同步刷新路径
- **级联删除**：删除节点会递归删除子节点，并将关联谷子的 `location` 置空，避免悬挂引用
- **级联查询**：`StorageNodeGoodsView` 支持 `include_children` 参数做级联查询

### 性能优化
- **查询优化**：列表接口使用 `select_related` / `prefetch_related` 规避 N+1 查询
- **序列化优化**：列表接口使用瘦身序列化器，详情接口提供完整数据
- **限流保护**：检索接口限流 60 次/分钟，防止恶意请求

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


---

## 🎯 项目亮点

1. **完整的 CRUD 接口**：所有基础数据（IP、角色、品类）和核心数据（谷子）都提供完整的增删改查接口
2. **高性能检索**：通过查询优化和瘦身序列化器，确保列表检索的响应速度
3. **智能去重**：基于业务逻辑的幂等性保护，防止重复录入
4. **灵活的收纳管理**：树状结构 + 路径冗余，既支持复杂层级又便于快速检索
5. **多角色支持**：M2M 关系设计，完美支持双人/多人谷子场景
6. **关键词搜索**：IP 关键词系统，提升搜索体验
7. **图片自动压缩**：智能压缩算法，上传时自动压缩，节省存储空间
8. **BGM API 集成**：无缝对接 Bangumi API，快速导入 IP 和角色数据，提升数据录入效率

---

## 📝 TODO / 未来规划

- [ ] **用户与权限体系**
  - 支持多用户、多角色、多设备登录与访问控制
  - JWT Token 认证
- [ ] **统计与可视化**
  - 资产价值统计、购入时间分布
  - IP / 角色 / 品类占比等统计图表
  - 数据导出（Excel/CSV）
- [ ] **多端与备份**
  - 数据加密备份、多设备同步
  - 支持导出 / 导入功能
- [ ] **AI 识别谷子**
  - 支持 AI 识别谷子的角色、IP 和谷子类型（吧唧、立牌、色纸、小卡等）
  - 自动标签生成
- [ ] **高级搜索**
  - 全文搜索引擎集成（Elasticsearch/Meilisearch）
  - 价格区间、日期范围等高级筛选
- [ ] **批量操作**
  - 批量导入谷子数据
  - 批量更新状态、位置等

---

## 🌍 English Overview

**ShiGu** is a small but focused inventory and location management system for anime / game merch collectors. It provides:

- A rich **goods model** linking IP, character (M2M), category and physical storage location
- High‑performance **search & filter APIs** with index‑friendly fields and basic idempotent create logic
- A tree‑like **storage node model** to describe real‑world spaces (room → cabinet → shelf → drawer), exposed through simple, cache‑friendly APIs
- **IP keyword system** for enhanced search experience
- **Automatic image compression** to optimize storage usage

The name **ShiGu** plays on the Chinese words for "eating merch" (吃谷) and "picking up / collecting" (拾谷), emphasizing both the emotional side of collecting and the structured act of organizing your collection.

---

## 📄 许可证

本项目采用 MIT 许可证。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**拾谷 · ShiGu** - 让每一件谷子都有归属 ✨
