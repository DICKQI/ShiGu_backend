## 拾谷 · ShiGu

拾谷（英文暂定 **ShiGu**）是一套面向「吃谷人」的个人谷子资产管理与检索系统，基于 **Django 6 + Django REST Framework** 构建。  
它聚焦两个核心问题：

- **我有什么谷子？** —— 按 IP / 角色 / 品类等多维度快速检索、统一管理资产。
- **它们都放哪儿了？** —— 用树状的「物理收纳空间」模型精确标记每一件谷子的存放位置。


## 功能概览

- **谷子资产管理（apps.goods）**
  - `IP`：作品来源（如「崩坏：星穹铁道」），支持简称 / 搜索关键字（如「星铁」「HSR」）。
  - `Character`：角色信息（如「流萤」），关联所属 IP，可配置头像与性别（`male` / `female` / `other`）。
  - `Category`：品类维度（吧唧、色纸、立牌、挂件等）。
  - `Goods`：核心谷子资产表，支持：
    - 多维关联：IP / 角色 / 品类 / 物理位置（`StorageNode`）
    - 基础资产字段：名称、数量、购入单价、入手时间、是否官谷、状态（在馆 / 出街中 / 已售出）、备注
    - 图片：主图 + 补充图片（`GuziImage`，如背板细节、瑕疵点等）
  - **基础数据 CRUD 接口**
    - `IPViewSet`：IP作品的完整 CRUD（列表、详情、创建、更新、删除），支持搜索和过滤。
    - `CharacterViewSet`：角色的完整 CRUD，支持按 IP 过滤和搜索，创建/更新时使用 `ip_id` 字段。
    - `CategoryViewSet`：品类的完整 CRUD，支持搜索和过滤。
  - **检索接口（`GoodsViewSet`）**
    - 列表接口使用「瘦身」序列化器：满足检索页展示，减少无用字段。
    - 详情接口提供完整字段 + 补充图。
    - 支持多维过滤：`ip` / `character` / `category` / `status` / `location`。
    - 支持对 `name` 走索引的轻量全文搜索。
    - 使用 `select_related` / `prefetch_related` 规避 N+1 查询，提高检索性能。
    - 简单幂等写入逻辑：同一 IP + 角色 + 名称 + 入手日期 + 单价 视为同一资产，避免重复录入。

- **物理收纳空间管理（apps.location）**
  - `StorageNode`：自关联的收纳节点模型（房间 → 柜子 → 层 → 抽屉 / 格子 ……），支持无限级层级。
  - `path_name`：冗余的完整路径（如「书房/书架A/第3层」），方便前端直接展示和检索。
  - 可配置位置照片、备注、排序值（控制同级显示顺序）。
  - 接口设计：
    - 列表 / 创建接口：用于后台维护收纳结构。
    - 「位置树一次性下发」接口：返回扁平列表，由前端（如 Pinia）在内存组装为树，后续可在外层加缓存。

- **API 路由与限流**
  - 所有核心接口均在 `/api/` 前缀下提供：
    - **基础数据 CRUD**：
      - `GET /api/ips/`：IP作品列表（支持搜索和过滤）
      - `GET /api/ips/{id}/`：IP作品详情
      - `POST /api/ips/`：创建IP作品
      - `PUT/PATCH /api/ips/{id}/`：更新IP作品
      - `DELETE /api/ips/{id}/`：删除IP作品
      - `GET /api/characters/`：角色列表（支持按IP过滤和搜索）
      - `GET /api/characters/{id}/`：角色详情
      - `POST /api/characters/`：创建角色（需提供 `ip_id`）
      - `PUT/PATCH /api/characters/{id}/`：更新角色
      - `DELETE /api/characters/{id}/`：删除角色
      - `GET /api/categories/`：品类列表（支持搜索和过滤）
      - `GET /api/categories/{id}/`：品类详情
      - `POST /api/categories/`：创建品类
      - `PUT/PATCH /api/categories/{id}/`：更新品类
      - `DELETE /api/categories/{id}/`：删除品类
    - **谷子检索**：
      - `GET /api/goods/`：谷子列表检索。
      - `GET /api/goods/{id}/`：谷子详情。
      - `POST /api/goods/` 等：资产的 CRUD（视具体权限控制而定）。
    - **收纳位置**：
      - `GET /api/location/nodes/`：收纳节点列表。
      - `GET /api/location/nodes/{id}/goods/`：查看指定节点下的谷子，`?include_children=true` 时包含所有子节点谷子。
      - `GET /api/location/tree/`：收纳位置树数据下发。
  - 统一 DRF 配置中启用了：
    - `django_filters` 和 `SearchFilter` 作为默认过滤后端。
    - 针对谷子检索接口的 `ScopedRateThrottle`（默认 `goods_search: 60/minute`），以适配前端高频搜索。

---

## 代码结构

- **核心 Django 项目**
  - `ShiGu/settings.py`：基础配置（SQLite、DRF、节流、过滤等）。
  - `ShiGu/urls.py`：项目路由，集成 DRF `DefaultRouter`。
- **应用层**
  - `apps/goods/`：谷子核心域模型及 API：
    - `models.py`：`IP` / `IPKeyword` / `Character` / `Category` / `Goods` / `GuziImage`。
    - `serializers.py`：列表 / 详情用序列化器及关联对象简化视图，支持基础数据的 CRUD 操作。
    - `views.py`：
      - `IPViewSet` / `CharacterViewSet` / `CategoryViewSet`：基础数据的完整 CRUD 接口。
      - `GoodsViewSet`：包含高性能查询、过滤、搜索、限流与简单幂等写入逻辑。
  - `apps/location/`：物理收纳节点模型及 API：
    - `models.py`：自关联 `StorageNode`。
    - `serializers.py`：基础与树结构下发序列化器。
    - `views.py`：列表 / 创建与位置树下发视图。
- **其他**
  - `templates/`：后续可扩展为后台管理 / 文档展示等模板目录。
  - `db.sqlite3`：默认开发数据库。

---

## 快速开始

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

   （示例命令，具体依赖可按实际 `requirements.txt` / `pyproject.toml` 为准）

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate

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

5. **启动开发服务器**

   ```bash
   python manage.py runserver
   ```

   默认访问地址为 `http://127.0.0.1:8000/`：
   - Django Admin：`/admin/`
   - API：`/api/` 及相关子路径。

---

## 简要 API 说明

以下为部分核心接口示例，实际字段以序列化器为准：

### 基础数据 CRUD

- **IP作品管理**
  - **GET** `/api/ips/`：获取IP作品列表（支持 `?search=关键词` 和 `?name=作品名` 过滤）
  - **GET** `/api/ips/{id}/`：获取IP作品详情
  - **POST** `/api/ips/`：创建IP作品（请求体：`{"name": "崩坏：星穹铁道"}`）
  - **PUT/PATCH** `/api/ips/{id}/`：更新IP作品
  - **DELETE** `/api/ips/{id}/`：删除IP作品

- **角色管理**
  - **GET** `/api/characters/`：获取角色列表（支持 `?ip=1` 按IP过滤，`?search=角色名` 搜索）
  - **GET** `/api/characters/{id}/`：获取角色详情
  - **POST** `/api/characters/`：创建角色（请求体：`{"name": "流萤", "ip_id": 1, "avatar": null}`）
  - **PUT/PATCH** `/api/characters/{id}/`：更新角色
  - **DELETE** `/api/characters/{id}/`：删除角色

- **品类管理**
  - **GET** `/api/categories/`：获取品类列表（支持 `?search=品类名` 搜索）
  - **GET** `/api/categories/{id}/`：获取品类详情
  - **POST** `/api/categories/`：创建品类（请求体：`{"name": "吧唧"}`）
  - **PUT/PATCH** `/api/categories/{id}/`：更新品类
  - **DELETE** `/api/categories/{id}/`：删除品类

### 谷子检索

- **谷子列表**

  - **GET** `/api/goods/`
  - 查询参数示例：
    - `?ip=1`：按 IP 过滤
    - `?character=5`：按角色过滤
    - `?category=2`：按品类过滤
    - `?status=in_cabinet`：按状态过滤
    - `?location=3`：按收纳位置过滤
    - `?search=流萤`：对名称进行轻量搜索

- **谷子详情**

  - **GET** `/api/goods/{id}/`
  - 返回谷子的完整信息（基础信息、价格、时间、位置、备注、补充图片等）。

### 收纳位置

- **收纳节点列表 / 创建**

  - **GET / POST** `/api/location/nodes/`
  - 用于在后台维护收纳空间的层级结构。

- **收纳节点下的谷子**

  - **GET** `/api/location/nodes/{id}/goods/?include_children=false|true`
  - 列出当前节点或当前 + 子节点下的所有谷子，返回“瘦身”列表序列化字段。

- **收纳位置树一次性下发**

  - **GET** `/api/location/tree/`
  - 返回带 `parent` 与 `path_name` 的扁平节点列表，前端可在内存中构建树。

> 📖 **完整 API 文档**：请参考 `api.md` 文件，包含详细的请求/响应示例和字段说明。

---

## 实现细节与使用注意

- **ID 设计**：`Goods` 使用 UUID 主键，适合前后端解耦和离线草稿合并场景。
- **图片与压缩**：上传主图或补充图时自动压缩到约 300KB (`apps/goods/utils.compress_image`)，`POST /api/goods/{id}/upload-main-photo/` 支持独立更新主图。
- **幂等创建**：`GoodsViewSet.perform_create` 基于「IP+角色+名称+入手日期+单价」做幂等写入，防止重复录入。
- **搜索体验**：`Goods` 支持对名称、IP 名称及 IP 关键词(`IPKeyword`)的轻量搜索；`IP` 关键词在序列化器中支持字符串数组读写。
- **角色性别字段**：`Character` 支持 `gender` 字段，取值为 `male` / `female` / `other`，默认 `female`，便于后续做统计或展示优化。
- **收纳节点维护**：
  - `StorageNodeSerializer` 若未提供 `path_name`，会基于父节点自动生成；更新父子关系或名称时会同步刷新路径。
  - 删除节点会递归删除子节点，并将关联谷子的 `location` 置空，避免悬挂引用。
  - `StorageNodeGoodsView` 支持 `include_children` 参数做级联查询。
- **跨域与限流**：开发环境默认开放本地常见端口的 CORS；检索接口限流范围在 `settings.REST_FRAMEWORK.DEFAULT_THROTTLE_RATES` 中统一配置。
- **媒体与静态文件**：媒体目录为 `media/`（开发环境由 Django 提供），静态文件收集至 `staticfiles/`，生产需用 Nginx 等托管。
- **数据库与环境**：默认 SQLite；`SECRET_KEY`、`DEBUG`、数据库等生产参数需通过环境变量或独立配置文件覆盖。
- **后台管理**：通过 `python manage.py createsuperuser` 创建账户后，可在 `/admin/` 维护基础数据（IP/角色/品类/收纳节点等）。

---

## TODO / 未来规划与扩展方向

- [ ] **用户与权限体系**
  - 支持多用户、多角色、多设备登录与访问控制。
- [ ] **统计与可视化**
  - 资产价值、购入时间分布、IP / 角色 / 品类占比等统计图表。
- [ ] **多端与备份**
  - 数据加密备份、多设备同步，支持导出 / 导入。
- [ ] **AI识别谷子**
  - 支持AI识别谷子的角色、IP、和谷子类型（吧唧、立牌、色纸、小卡等）

---

## English Overview

**ShiGu** is a small but focused inventory and location management system for anime / game merch collectors.  
It provides:

- A rich **goods model** linking IP, character, category and physical storage location.
- High‑performance **search & filter APIs** with index‑friendly fields and basic idempotent create logic.
- A tree‑like **storage node model** to describe real‑world spaces (room → cabinet → shelf → drawer), exposed through simple, cache‑friendly APIs.

The name **ShiGu** plays on the Chinese words for "eating merch" and "picking up / collecting", emphasizing both the emotional side of collecting and the structured act of organizing your collection.


