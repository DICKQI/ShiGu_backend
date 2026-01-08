## 谷子检索系统 API 文档（后端：Django + DRF）

面向：前端工程师（Vue / React 等）

说明：
- 所有接口默认返回 `application/json`。
- 未特殊说明的分页接口均使用 DRF 默认分页（后续可按需改为 cursor 分页）。
- 图片字段为 URL 字符串，真实存储可对接本地或云存储（OSS/COS）。

---

## 一、数据库模型与字段说明

### 1.1 位置模块（`apps.location`）

#### `StorageNode` 收纳节点表

用于表示房间 / 柜子 / 层 / 抽屉等树状结构。

| 字段名       | 类型              | 说明                                                                 |
| ------------ | ----------------- | -------------------------------------------------------------------- |
| `id`         | Integer (PK)      | 自增主键                                                             |
| `name`       | Char(50)          | 节点名称，如：`卧室`、`A1柜`、`第三层`                               |
| `parent`     | FK -> `StorageNode` | 父节点 ID，顶层节点为 `null`                                         |
| `path_name`  | Char(200), 索引   | 冗余完整路径，如：`书房/书架A/第3层`                                |
| `image`      | Image(URL)        | 位置照片 URL，可用于显示柜子 / 抽屉的实景图                         |
| `description`| Text              | 备注，如：`靠窗的那一侧`                                             |
| `order`      | Integer           | 同级展示顺序，越小越靠前                                             |

---

### 1.2 谷子模块（`apps.goods`）

#### `IP` 作品来源表

| 字段名      | 类型                  | 说明                                                  |
| ----------- | --------------------- | ----------------------------------------------------- |
| `id`        | Integer (PK)          | 自增主键                                              |
| `name`      | Char(100), 唯一, 索引 | 作品名，如：`崩坏：星穹铁道`                          |

#### `IPKeyword` IP 多关键词表

用于为同一个 IP 维护**多个别名 / 关键词**，例如：`星铁`、`崩铁`、`HSR`、`星穹铁道` 等，便于搜索。

| 字段名  | 类型              | 说明                                                         |
| ------- | ----------------- | ------------------------------------------------------------ |
| `id`    | Integer (PK)      | 自增主键                                                     |
| `ip`    | FK -> `IP`        | 所属 IP 作品                                                 |
| `value` | Char(50), 索引    | 关键词 / 别名，例如：`星铁`、`崩铁`、`HSR` 等                |

> 约束：同一 `ip` 下 `value` 唯一（防止重复录入相同别名）。

#### `Character` 角色表

| 字段名   | 类型                | 说明                                      |
| -------- | ------------------- | ----------------------------------------- |
| `id`     | Integer (PK)        | 自增主键                                  |
| `ip`     | FK -> `IP`          | 所属作品                                  |
| `name`   | Char(100), 索引     | 角色名，如：`流萤`                        |
| `avatar` | Image(URL，可空)    | 角色头像 URL，用于前端列表/角色选择展示  |
| `gender` | Char(10)            | 角色性别：`male`(男) / `female`(女) / `other`(其他)，默认 `female` |

> 约束：同一 `ip` 下 `name` 唯一。

#### `Category` 品类表

| 字段名 | 类型              | 说明                           |
| ------ | ----------------- | ------------------------------ |
| `id`   | Integer (PK)      | 自增主键                       |
| `name` | Char(50), 唯一    | 品类名，如：`吧唧`、`立牌`    |

#### `Goods` 谷子核心表

| 字段名         | 类型                         | 说明                                                                 |
| -------------- | ---------------------------- | -------------------------------------------------------------------- |
| `id`           | UUID (PK)                    | 谷子唯一资产编号（字符串 UUID）                                     |
| `name`         | Char(200), 索引              | 谷子名称，如：`流萤花火双人立牌`                                   |
| `ip`           | FK -> `IP`                   | 所属作品                                                             |
| `characters`   | M2M -> `Character[]`         | 关联角色列表（多对多关系），例如双人立牌可同时关联流萤和花火       |
| `category`     | FK -> `Category`             | 品类                                                                 |
| `location`     | FK -> `StorageNode` (可空)   | 物理存放位置，允许为空（尚未收纳 / 在路上等）                       |
| `main_photo`   | Image(URL，可空)             | 主展示图（列表页和详情主图）                                        |
| `quantity`     | PositiveInteger              | 数量，默认为 1                                                       |
| `price`        | Decimal(10,2，可空)          | 购入单价                                                             |
| `purchase_date`| Date，可空                   | 入手日期                                                             |
| `is_official`  | Boolean                      | 是否官谷，默认 `true`                                               |
| `status`       | Char(20)                     | 状态：`in_cabinet`(在馆)、`outdoor`(出街中)、`sold`(已售出)        |
| `notes`        | Text，可空                   | 备注，如：瑕疵说明、购入渠道等                                      |
| `created_at`   | DateTime                     | 创建时间                                                             |
| `updated_at`   | DateTime                     | 更新时间                                                             |

#### `GuziImage` 谷子补充图片表

| 字段名  | 类型                     | 说明                                          |
| ------- | ------------------------ | --------------------------------------------- |
| `id`    | Integer (PK)             | 自增主键                                      |
| `guzi`  | FK -> `Goods`            | 所属谷子                                      |
| `image` | Image(URL)               | 补充图片 URL                                  |
| `label` | Char(100，可空)         | 图片标签，如：`背板细节`、`瑕疵点` 等         |

---

## 二、鉴权与通用说明

当前项目为内网 / 个人系统示例，API 暂不强制鉴权。
若后期需要接入登录态，可在 DRF 中配置 `DEFAULT_AUTHENTICATION_CLASSES` 并统一在 Header 携带 Token。

错误响应统一使用 DRF 默认格式，例如：

```json
{
  "detail": "Not found."
}
```

---

## 三、位置相关 API

### 3.1 获取位置树（一次性下发）

- **URL**：`GET /api/location/tree/`
- **说明**：
  - 返回所有 `StorageNode` 的扁平列表（含父子关系）。
  - 前端在内存中使用 `id`/`parent` 组装树结构（建议存入 Pinia/Vuex）。

#### 请求参数

无（后续如需分页/筛选再扩展）。

#### 响应示例

```json
[
  {
    "id": 1,
    "name": "卧室",
    "parent": null,
    "path_name": "卧室",
    "order": 0
  },
  {
    "id": 2,
    "name": "书桌左侧柜子",
    "parent": 1,
    "path_name": "卧室/书桌左侧柜子",
    "order": 10
  },
  {
    "id": 3,
    "name": "第一层",
    "parent": 2,
    "path_name": "卧室/书桌左侧柜子/第一层",
    "order": 0
  }
]
```

字段说明同上文 `StorageNode` 表。

---

### 3.2 列表 / 新建收纳节点（后台使用）

- **URL**：`GET /api/location/nodes/`
- **URL**：`POST /api/location/nodes/`

#### GET 请求

用于后台管理页面展示所有节点（可配合前端表格）。

**请求参数**：暂不支持筛选/分页，后续如需要可以扩展。

**响应示例**：

```json
[
  {
    "id": 1,
    "name": "卧室",
    "parent": null,
    "path_name": "卧室",
    "order": 0,
    "image": null,
    "description": "主卧房间"
  }
]
```

#### POST 请求

**请求体（JSON）**：

```json
{
  "name": "第一层",
  "parent": 2,
  "path_name": "卧室/书桌左侧柜子/第一层",
  "order": 0,
  "description": "常用立牌"
}
```

说明：
- `parent`：上级节点 ID，顶层节点可为 `null`。
- `path_name`：完整路径，**可选字段**。如果不提供，系统会根据父节点自动生成：
  - 有父节点：`父节点路径 + "/" + 当前节点名称`
  - 无父节点（根节点）：直接使用节点名称
- `image`：如走表单上传，可使用 `multipart/form-data`；本项目示例以 URL 存储为主。

**响应**：返回创建后的节点详情（同 3.3.1）。

---

### 3.3 收纳节点详情 / 更新 / 删除接口

#### 3.3.1 获取收纳节点详情

- **URL**：`GET /api/location/nodes/{id}/`
- **说明**：获取单个收纳节点的详细信息。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | 收纳节点主键 `id` |

##### 响应示例

```json
{
  "id": 3,
  "name": "第一层",
  "parent": 2,
  "path_name": "卧室/书桌左侧柜子/第一层",
  "order": 0,
  "image": null,
  "description": "常用立牌"
}
```

**字段说明**：同 `StorageNode` 表字段说明。

---

#### 3.3.2 更新收纳节点

- **URL**：`PUT /api/location/nodes/{id}/`（完整更新）
- **URL**：`PATCH /api/location/nodes/{id}/`（部分更新）
- **说明**：更新收纳节点信息。当父节点或名称改变时，系统会自动更新 `path_name`。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | 收纳节点主键 `id` |

##### 请求体（JSON）

**完整更新（PUT）**：

```json
{
  "name": "第一层（更新）",
  "parent": 2,
  "path_name": "卧室/书桌左侧柜子/第一层（更新）",
  "order": 10,
  "description": "更新后的备注"
}
```

**部分更新（PATCH）**：

```json
{
  "name": "第一层（更新）",
  "order": 10
}
```

##### 字段说明

| 字段名       | 类型   | 必填 | 说明                                                                 |
| ------------ | ------ | ---- | -------------------------------------------------------------------- |
| `name`       | string | 否   | 节点名称，最大长度50字符（PUT 必填，PATCH 可选）                    |
| `parent`     | int    | 否   | 父节点 ID，顶层节点可为 `null`（PUT 必填，PATCH 可选）              |
| `path_name`  | string | 否   | 完整路径，**可选字段**。如果不提供且父节点或名称改变，系统会自动重新生成 |
| `order`      | int    | 否   | 排序值，默认 0                                                       |
| `image`      | string | 否   | 位置照片 URL，如通过表单上传可使用 `multipart/form-data`            |
| `description`| string | 否   | 备注信息                                                             |

##### 响应

返回更新后的节点详情（同 3.3.1）。

> **注意**：
> - 如果更新了 `parent` 或 `name`，且未提供 `path_name`，系统会自动根据新的父节点和名称重新生成 `path_name`。
> - 如果明确提供了 `path_name`，则使用提供的值。

---

#### 3.3.3 删除收纳节点

- **URL**：`DELETE /api/location/nodes/{id}/`
- **说明**：删除指定的收纳节点。删除父节点时，会**级联删除所有子节点**，并**自动取消所有关联商品的 location 关联**（将商品的 `location` 字段设置为 `null`）。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | 收纳节点主键 `id` |

##### 删除行为说明

1. **级联删除**：删除父节点时，会递归删除所有子节点（包括子节点的子节点等）。
2. **商品关联处理**：删除节点前，系统会自动将所有关联到该节点及其子节点的商品的 `location` 字段设置为 `null`，确保数据一致性。
3. **事务保护**：删除操作在数据库事务中执行，确保原子性。

##### 响应

- 成功：返回 `204 No Content`
- 失败：如果节点不存在，返回 `404 Not Found`

##### 示例

假设有以下节点结构：
```
卧室 (id: 1)
  └── 书桌左侧柜子 (id: 2)
      └── 第一层 (id: 3)
```

删除 `书桌左侧柜子`（id: 2）时：
- 会同时删除 `第一层`（id: 3）
- 所有关联到节点 2 和节点 3 的商品的 `location` 字段会被设置为 `null`

---

#### 3.3.4 获取收纳节点下的所有商品

- **URL**：`GET /api/location/nodes/{id}/goods/`
- **说明**：获取指定收纳节点下的所有商品列表。支持查询参数控制是否包含子节点下的商品。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | 收纳节点主键 `id` |

##### 查询参数（全部可选）

| 参数名            | 类型    | 说明                                                                 |
| ----------------- | ------- | -------------------------------------------------------------------- |
| `include_children`| boolean | 是否包含子节点下的商品，默认 `false`（只查询当前节点）。设置为 `true` 时，会递归查询所有子节点（包括子节点的子节点）下的商品 |
| `page`            | int     | 分页页码（DRF 默认分页）                                             |

##### 响应示例

**只查询当前节点（默认）**：

```http
GET /api/location/nodes/3/goods/
```

**包含所有子节点**：

```http
GET /api/location/nodes/2/goods/?include_children=true
```

**响应（分页）**：

```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "e4c1cb33-5cd3-4f94-bfc7-9de0b99f5a10",
      "name": "流萤花火双人立牌",
      "ip": {
        "id": 1,
        "name": "崩坏：星穹铁道"
      },
      "character": {
        "id": 5,
        "name": "流萤",
        "ip": {
          "id": 1,
          "name": "崩坏：星穹铁道"
        }
      },
      "category": {
        "id": 2,
        "name": "立牌"
      },
      "location_path": "卧室/书桌左侧柜子/第一层",
      "main_photo": "https://cdn.example.com/goods/main/xxx.jpg",
      "status": "in_cabinet",
      "quantity": 1
    }
  ]
}
```

**字段说明**：
- 返回格式与 `GET /api/goods/` 列表接口相同，使用 `GoodsListSerializer`（瘦身字段）。
- 商品按创建时间倒序排列（最新的在前）。

##### 使用场景

- **查看单个节点下的商品**：`GET /api/location/nodes/3/goods/`
- **查看节点及其所有子节点下的商品**：`GET /api/location/nodes/2/goods/?include_children=true`
  - 例如：查询"书桌左侧柜子"（id: 2）及其下所有层级（如"第一层"、"第二层"等）的商品

---

## 四、谷子检索与详情 API

### 4.1 谷子列表检索（高性能列表）

- **URL**：`GET /api/goods/`
- **说明**：
  - 用于“快速检索页 / 云展柜列表页”。
  - 返回瘦身字段：**不包含备注、补充图等大字段**。
  - 支持多维过滤（IP/角色/品类/状态/位置）+ 文本搜索。

#### 查询参数（全部可选）

| 参数名        | 类型   | 说明                                                                                          |
| ------------- | ------ | --------------------------------------------------------------------------------------------- |
| `ip`          | int    | IP ID，精确过滤，例如 `/api/goods/?ip=1`                                                     |
| `characters`  | int    | 角色 ID，精确过滤（匹配包含该角色的谷子）                                                   |
| `characters__in` | string | **多角色过滤**：逗号分隔的角色ID列表，如：`5,6`，匹配包含任意指定角色的谷子              |
| `category`    | int    | 品类 ID，精确过滤                                                                            |
| `status`      | string | 单状态过滤：`in_cabinet` / `outdoor` / `sold`                                               |
| `status__in`  | string | **多状态过滤**：逗号分隔的状态列表，如：`in_cabinet,sold`                                   |
| `location`    | int    | 位置节点 ID，过滤收纳在某一具体节点下的谷子                                                 |
| `search`      | string | 轻量模糊搜索：会同时在 `Goods.name`、`IP.name`、`IPKeyword.value` 上匹配    |
| `page`        | int    | 分页页码（DRF 默认）                                                                         |

> 示例 1：检索"星铁 + 流萤 + 吧唧，当前在馆"的所有谷子：
>
> `/api/goods/?ip=1&characters=5&category=2&status=in_cabinet&search=流萤`
>
> 示例 2：检索"星铁 + 流萤或花火 + 吧唧，当前在馆 **或 已售出**"的所有谷子（多角色、多状态）：
>
> `/api/goods/?ip=1&characters__in=5,6&category=2&status__in=in_cabinet,sold&search=流萤`
>
> 示例 3：如果 IP `崩坏：星穹铁道` 额外配置了关键词 `崩铁`、`HSR`，则：
>
> `/api/goods/?search=崩铁` 或 `/api/goods/?search=HSR` 也可以命中该 IP 及其下所有相关谷子。

#### 响应示例（分页）

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "e4c1cb33-5cd3-4f94-bfc7-9de0b99f5a10",
      "name": "流萤花火双人立牌",
      "ip": {
        "id": 1,
        "name": "崩坏：星穹铁道"
      },
      "characters": [
        {
          "id": 5,
          "name": "流萤",
          "ip": {
            "id": 1,
            "name": "崩坏：星穹铁道"
          },
          "avatar": null,
          "gender": "female"
        },
        {
          "id": 6,
          "name": "花火",
          "ip": {
            "id": 1,
            "name": "崩坏：星穹铁道"
          },
          "avatar": "https://cdn.example.com/characters/huohuo.jpg",
          "gender": "female"
        }
      ],
      "category": {
        "id": 2,
        "name": "立牌"
      },
      "location_path": "卧室/书桌左侧柜子/第一层",
      "main_photo": "https://cdn.example.com/goods/main/xxx.jpg",
      "status": "in_cabinet",
      "quantity": 1
    }
  ]
}
```

**字段说明**：
- `id`：谷子 UUID，后续详情/编辑都用此 ID。
- `ip` / `characters` / `category`：已展开为简单对象，避免前端再二次请求。`characters` 为数组，可包含多个角色。
- `location_path`：人类可读的完整路径（前端直接展示即可）。
- `main_photo`：主图 URL，可直接用作列表缩略图（后续可以替换为缩略图 URL）。

---

### 4.2 谷子详情

- **URL**：`GET /api/goods/{id}/`
- **说明**：返回单个谷子的完整信息 + 所有补充图片。

#### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | UUID | 谷子主键 `id`   |

#### 响应示例

```json
{
  "id": "e4c1cb33-5cd3-4f94-bfc7-9de0b99f5a10",
  "name": "流萤花火双人立牌",
  "ip": {
    "id": 1,
    "name": "崩坏：星穹铁道"
  },
  "characters": [
    {
      "id": 5,
      "name": "流萤",
      "ip": {
        "id": 1,
        "name": "崩坏：星穹铁道"
      },
      "avatar": null,
      "gender": "female"
    },
    {
      "id": 6,
      "name": "花火",
      "ip": {
        "id": 1,
        "name": "崩坏：星穹铁道"
      },
      "avatar": "https://cdn.example.com/characters/huohuo.jpg",
      "gender": "female"
    }
  ],
  "category": {
    "id": 2,
    "name": "立牌"
  },
  "location_path": "卧室/书桌左侧柜子/第一层",
  "location": 3,
  "main_photo": "https://cdn.example.com/goods/main/xxx.jpg",
  "quantity": 1,
  "price": "89.00",
  "purchase_date": "2024-09-20",
  "is_official": true,
  "status": "in_cabinet",
  "notes": "B站谷子团，板子有轻微划痕",
  "created_at": "2024-09-21T10:00:00Z",
  "updated_at": "2024-09-21T10:00:00Z",
  "additional_photos": [
    {
      "id": 1,
      "image": "https://cdn.example.com/goods/extra/back_detail.jpg",
      "label": "背板细节"
    },
    {
      "id": 2,
      "image": "https://cdn.example.com/goods/extra/defect.jpg",
      "label": "瑕疵点"
    }
  ]
}
```

**字段说明补充**：
- `characters`：关联角色数组，可包含多个角色，例如双人立牌可同时关联流萤和花火。
- `location`：位置节点 ID，可用于前端联动高亮位置树。
- `additional_photos`：补充图片数组，适合做详情页图片画廊。

---

### 4.3 新建 / 编辑谷子（主数据 JSON，主图单独上传）

> 说明：目前后端对幂等性做了**简易保护**，防止重复录入完全相同的谷子。主数据与主图分开：先提交 JSON 创建谷子，再单独上传主图。

- **URL**：`POST /api/goods/`（仅主数据，JSON）
- **URL**：`PUT /api/goods/{id}/`（主数据更新，JSON）
- **URL**：`PATCH /api/goods/{id}/`（主数据部分更新，JSON）

#### POST 请求体示例（JSON）

```json
{
  "name": "流萤花火双人立牌",
  "ip_id": 1,
  "character_ids": [5, 6],
  "category_id": 1,
  "location": 3,
  "quantity": 1,
  "price": "89.00",
  "purchase_date": "2024-09-20",
  "is_official": true,
  "status": "in_cabinet",
  "notes": "线下展会购入"
}
```

说明：
- `character_ids`：角色ID数组，可包含多个角色，例如 `[5, 6]` 表示同时关联流萤（ID: 5）和花火（ID: 6）。
- 主图 `main_photo` 不在此接口上传；请使用下方 `upload-main-photo`。
- 后端会根据以下组合判断是否重复（幂等）：
  - `ip + 相同角色集合（顺序无关） + name + purchase_date + price`
  - 若已存在同组合的记录，则不会新建，而是返回已有实例。

**响应**：返回创建后的完整详情（同 4.2）。

#### 4.3.1 主图上传 / 更新接口

- **URL**：`POST /api/goods/{id}/upload-main-photo/`
- **请求方式**：`multipart/form-data`
- **字段**：`main_photo`（文件，必填）
- **说明**：独立上传或更新主图，后台会自动压缩到约 300KB 以下（若需要）。

示例（form-data）：

```
main_photo: <file>
```

响应：返回更新后的谷子详情（同 4.2）。

### 4.4 删除谷子

- **URL**：`DELETE /api/goods/{id}/`
- **说明**：删除指定谷子。关联的补充图片 `GuziImage` 会因外键级联一并删除；若需物理删除存储中的图片，请根据存储后端自行处理。
- **响应**：
  - 成功：`204 No Content`
  - 失败：`404 Not Found`（ID 不存在）

---

## 五、基础数据 API（CRUD 完整接口）

用于管理基础数据（IP作品、角色、品类）的完整 CRUD 接口。建议在应用启动时预加载列表数据并缓存到前端状态管理（Pinia/Vuex）。

### 5.1 IP作品 CRUD 接口

#### 5.1.1 获取IP作品列表

- **URL**：`GET /api/ips/`
- **说明**：获取所有IP作品列表，用于筛选器下拉选项。

##### 查询参数（全部可选）

| 参数名 | 类型   | 说明                                    |
| ------ | ------ | --------------------------------------- |
| `name` | string | 按名称精确或模糊匹配（`exact` / `icontains`） |
| `search` | string | 轻量搜索：在 `name`、`keywords__value` 上匹配 |

##### 响应示例

```json
[
  {
    "id": 1,
    "name": "崩坏：星穹铁道",
    "keywords": [
      {
        "id": 1,
        "value": "星铁"
      },
      {
        "id": 2,
        "value": "崩铁"
      },
      {
        "id": 3,
        "value": "HSR"
      }
    ],
    "character_count": 5
  },
  {
    "id": 2,
    "name": "原神",
    "keywords": [],
    "character_count": 3
  }
]
```

**字段说明**：
- `id`：IP作品 ID，用于后续筛选参数。
- `name`：完整作品名。
- `keywords`：IP关键词/别名数组，每个关键词包含 `id` 和 `value` 字段。
- `character_count`：该IP下的角色数量（整数）。

---

#### 5.1.2 获取IP作品详情

- **URL**：`GET /api/ips/{id}/`
- **说明**：获取单个IP作品的详细信息。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | IP作品主键 `id` |

##### 响应示例

```json
{
  "id": 1,
  "name": "崩坏：星穹铁道",
  "keywords": [
    {
      "id": 1,
      "value": "星铁"
    },
    {
      "id": 2,
      "value": "崩铁"
    },
    {
      "id": 3,
      "value": "HSR"
    }
  ],
  "character_count": 5
}
```

**字段说明**：
- `id`：IP作品 ID。
- `name`：完整作品名。
- `keywords`：IP关键词/别名数组，每个关键词包含 `id` 和 `value` 字段。
- `character_count`：该IP下的角色数量（整数）。

---

#### 5.1.3 创建IP作品

- **URL**：`POST /api/ips/`
- **说明**：创建新的IP作品。

##### 请求体（JSON）

```json
{
  "name": "崩坏：星穹铁道",
  "keywords": ["星铁", "崩铁", "HSR"]
}
```

##### 字段说明

| 字段名    | 类型           | 必填 | 说明                                                                 |
| --------- | -------------- | ---- | -------------------------------------------------------------------- |
| `name`    | string         | 是   | 作品名，必须唯一，最大长度100字符                                    |
| `keywords`| array[string]  | 否   | 关键词/别名列表，例如：`["星铁", "崩铁", "HSR"]`。每个关键词最大长度50字符，会自动去重和去空 |

##### 响应

返回创建后的IP作品详情（同 5.1.2），包含 `keywords` 字段显示已创建的关键词。

---

#### 5.1.4 更新IP作品

- **URL**：`PUT /api/ips/{id}/`（完整更新）
- **URL**：`PATCH /api/ips/{id}/`（部分更新）
- **说明**：更新IP作品信息。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | IP作品主键 `id` |

##### 请求体（JSON）

**完整更新（PUT）**：

```json
{
  "name": "崩坏：星穹铁道（更新）",
  "keywords": ["星铁", "崩铁", "HSR", "星穹铁道"]
}
```

**部分更新（PATCH）**：

```json
{
  "keywords": ["星铁", "崩铁"]
}
```

##### 字段说明

| 字段名    | 类型           | 必填 | 说明                                                                 |
| --------- | -------------- | ---- | -------------------------------------------------------------------- |
| `name`    | string         | 否   | 作品名，最大长度100字符（PUT 必填，PATCH 可选）                      |
| `keywords`| array[string]  | 否   | 关键词/别名列表，例如：`["星铁", "崩铁", "HSR"]`。每个关键词最大长度50字符。更新时会**完全替换**现有关键词列表（删除不在列表中的关键词，添加新关键词） |

##### 响应

返回更新后的IP作品详情（同 5.1.2），包含 `keywords` 字段显示更新后的关键词。

> **注意**：如果 `keywords` 字段在请求中未提供，则不会修改现有关键词。如果提供了 `keywords` 字段（即使是空数组 `[]`），则会按照提供的列表完全替换现有关键词。

---

#### 5.1.5 删除IP作品

- **URL**：`DELETE /api/ips/{id}/`
- **说明**：删除指定的IP作品。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | IP作品主键 `id` |

##### 响应

- 成功：返回 `204 No Content`
- 失败：如果该IP作品下有关联的角色或谷子，将返回错误（受外键保护）

---

#### 5.1.6 获取IP作品下的所有角色

- **URL**：`GET /api/ips/{id}/characters/`
- **说明**：获取指定IP作品下的所有角色列表。这是通过IP获取角色的专用接口，语义更清晰。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | IP作品主键 `id` |

##### 响应示例

```json
[
  {
    "id": 5,
    "name": "流萤",
    "ip": {
      "id": 1,
      "name": "崩坏：星穹铁道"
    },
    "avatar": null,
    "gender": "female"
  },
  {
    "id": 6,
    "name": "花火",
    "ip": {
      "id": 1,
      "name": "崩坏：星穹铁道"
    },
    "avatar": "https://cdn.example.com/characters/huohuo.jpg",
    "gender": "female"
  }
]
```

**字段说明**：
- `id`：角色 ID，用于后续筛选参数。
- `name`：角色名。
- `ip`：所属IP作品信息（已展开，避免前端二次请求）。
- `avatar`：角色头像 URL（可选）。
- `gender`：角色性别：`male`(男) / `female`(女) / `other`(其他)。

> **注意**：此接口与 `GET /api/characters/?ip={id}` 功能相同，但提供更直观的 RESTful 语义。可以根据前端使用习惯选择使用哪个接口。

---

### 5.2 角色 CRUD 接口

#### 5.2.1 获取角色列表

- **URL**：`GET /api/characters/`
- **说明**：获取所有角色列表，支持按IP过滤，用于筛选器下拉选项。

##### 查询参数（全部可选）

| 参数名      | 类型   | 说明                                    |
| ----------- | ------ | --------------------------------------- |
| `ip`        | int    | IP ID，精确过滤，例如 `/api/characters/?ip=1` |
| `name`      | string | 按角色名精确或模糊匹配（`exact` / `icontains`） |
| `search`    | string | 轻量搜索：在 `name`、`ip__name`、`ip__keywords__value` 上匹配 |

> 示例：获取"崩坏：星穹铁道"下的所有角色：
>
> `/api/characters/?ip=1`

##### 响应示例

```json
[
  {
    "id": 5,
    "name": "流萤",
    "ip": {
      "id": 1,
      "name": "崩坏：星穹铁道"
    },
    "avatar": null,
    "gender": "female"
  },
  {
    "id": 6,
    "name": "花火",
    "ip": {
      "id": 1,
      "name": "崩坏：星穹铁道"
    },
    "avatar": "https://cdn.example.com/characters/huohuo.jpg",
    "gender": "female"
  }
]
```

**字段说明**：
- `id`：角色 ID，用于后续筛选参数。
- `name`：角色名。
- `ip`：所属IP作品信息（已展开，避免前端二次请求）。
- `avatar`：角色头像 URL（可选）。
 - `gender`：角色性别：`male`(男) / `female`(女) / `other`(其他)，若不传则默认 `female`。

---

#### 5.2.2 获取角色详情

- **URL**：`GET /api/characters/{id}/`
- **说明**：获取单个角色的详细信息。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | 角色主键 `id`   |

##### 响应示例

```json
{
  "id": 5,
  "name": "流萤",
  "ip": {
    "id": 1,
    "name": "崩坏：星穹铁道"
  },
  "avatar": null,
  "gender": "female"
}
```

---

#### 5.2.3 创建角色

- **URL**：`POST /api/characters/`
- **说明**：创建新角色。

##### 请求体（JSON）

```json
{
  "name": "流萤",
  "ip_id": 1,
  "avatar": null,
  "gender": "female"
}
```

##### 字段说明

| 字段名   | 类型   | 必填 | 说明                                                         |
| -------- | ------ | ---- | ------------------------------------------------------------ |
| `name`   | string | 是   | 角色名，最大长度100字符，同一IP下必须唯一                    |
| `ip_id`  | int    | 是   | 所属IP作品ID（使用 `ip_id` 而非 `ip`）                       |
| `avatar` | string | 否   | 角色头像 URL，如通过表单上传可使用 `multipart/form-data` |
| `gender` | string | 否   | 角色性别：`male`(男) / `female`(女) / `other`(其他)，不传时后端默认保存为 `female` |

##### 响应

返回创建后的角色详情（同 5.2.2）。

---

#### 5.2.4 更新角色

- **URL**：`PUT /api/characters/{id}/`（完整更新）
- **URL**：`PATCH /api/characters/{id}/`（部分更新）
- **说明**：更新角色信息。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | 角色主键 `id`   |

##### 请求体（JSON）

```json
{
  "name": "流萤（更新）",
  "ip_id": 1,
  "avatar": "https://cdn.example.com/characters/liuying.jpg",
  "gender": "female"
}
```

##### 响应

返回更新后的角色详情（同 5.2.2）。

---

#### 5.2.5 删除角色

- **URL**：`DELETE /api/characters/{id}/`
- **说明**：删除指定的角色。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | 角色主键 `id`   |

##### 响应

- 成功：返回 `204 No Content`
- 失败：如果该角色下有关联的谷子，将返回错误（受外键保护）

---

### 5.3 品类 CRUD 接口

#### 5.3.1 获取品类列表

- **URL**：`GET /api/categories/`
- **说明**：获取所有品类列表，用于筛选器下拉选项。

##### 查询参数（全部可选）

| 参数名   | 类型   | 说明                                    |
| -------- | ------ | --------------------------------------- |
| `name`   | string | 按品类名精确或模糊匹配（`exact` / `icontains`） |
| `search` | string | 轻量搜索：在 `name` 上匹配              |

##### 响应示例

```json
[
  {
    "id": 1,
    "name": "吧唧"
  },
  {
    "id": 2,
    "name": "立牌"
  },
  {
    "id": 3,
    "name": "色纸"
  }
]
```

**字段说明**：
- `id`：品类 ID，用于后续筛选参数。
- `name`：品类名称。

---

#### 5.3.2 获取品类详情

- **URL**：`GET /api/categories/{id}/`
- **说明**：获取单个品类的详细信息。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | 品类主键 `id`   |

##### 响应示例

```json
{
  "id": 1,
  "name": "吧唧"
}
```

---

#### 5.3.3 创建品类

- **URL**：`POST /api/categories/`
- **说明**：创建新品类。

##### 请求体（JSON）

```json
{
  "name": "吧唧"
}
```

##### 字段说明

| 字段名 | 类型   | 必填 | 说明                     |
| ------ | ------ | ---- | ------------------------ |
| `name` | string | 是   | 品类名，必须唯一，最大长度50字符 |

##### 响应

返回创建后的品类详情（同 5.3.2）。

---

#### 5.3.4 更新品类

- **URL**：`PUT /api/categories/{id}/`（完整更新）
- **URL**：`PATCH /api/categories/{id}/`（部分更新）
- **说明**：更新品类信息。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | 品类主键 `id`   |

##### 请求体（JSON）

```json
{
  "name": "吧唧（更新）"
}
```

##### 响应

返回更新后的品类详情（同 5.3.2）。

---

#### 5.3.5 删除品类

- **URL**：`DELETE /api/categories/{id}/`
- **说明**：删除指定的品类。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | 品类主键 `id`   |

##### 响应

- 成功：返回 `204 No Content`
- 失败：如果该品类下有关联的谷子，将返回错误（受外键保护）

---

## 六、限流与性能注意事项（给前端的协作建议）

### 6.1 限流（Throttling）

- 后端对谷子检索接口设置了**每分钟 60 次**的速率限制：
  - 作用范围：`GET /api/goods/`
  - 建议前端：
    - 做输入防抖（例如搜索框 300ms 防抖）。
    - 避免滚动时同时触发大量并发请求。

### 6.2 搜索与筛选使用建议

- 优先使用 **精确过滤参数**（`ip`、`characters`、`category`、`status`、`location`），减少模糊搜索范围。
- 搜索框建议映射到 `search` 参数，仅在确认输入后再发起请求（点回车 / 失焦）。

---

## 七、前端集成建议（示例流程）

1. **初始化加载**
   - 启动时请求：`GET /api/location/tree/`，将位置树缓存到 Pinia/Vuex，用于侧边栏展示和筛选。
   - 预加载基础数据：
     - `GET /api/ips/`：IP作品列表，用于筛选器
     - `GET /api/characters/`：角色列表，用于筛选器（可按需按IP过滤）
     - `GET /api/categories/`：品类列表，用于筛选器
   - 建议将这些数据缓存到前端状态管理，避免重复请求。

2. **云展柜列表页**
   - 使用 `GET /api/goods/`，根据筛选条件拼 query：
     - `ip` / `characters` / `characters__in` / `category` / `status` / `status__in` / `location` / `search`。
   - 列表 Item 展示：
     - 主图：`main_photo`
     - 标题：`name`
     - 副标题：`ip.name + characters.map(c => c.name).join('、') + category.name`（多个角色用顿号连接）
     - 位置：`location_path`

3. **详情页**
   - 路由进入时，用 `id` 调用：`GET /api/goods/{id}/`。
   - 展示：
     - 主图 + `additional_photos` 做画廊
     - 右侧信息卡：`ip/characters/category/location_path/price/purchase_date/is_official/status/notes`。
     - `characters` 为数组，可展示多个角色标签或角色头像。

若你后续确定前端框架（如 Vue3 + Pinia），可以在此基础上再补一份前端接口封装示例（TypeScript 类型 + Axios 封装）。***

---

## 八、BGM 角色导入辅助接口

> 说明：本章节接口用于**从 Bangumi(BGM) API 拉取角色**并**批量写入本系统的 IP / Character 表**。  
> 这两个接口是**互相独立**的：搜索接口只调用外部 API，不改数据库；创建接口只操作本地数据库，不再调用外部 API。

### 8.1 搜索 IP 作品并获取角色列表

- **URL**：`POST /api/bgm/search-characters/`
- **说明**：
  - 前端输入 IP 名称（如「崩坏：星穹铁道」），后端调用 BGM 官方 API 搜索条目并拉取其角色列表。
  - **不会**写入本地数据库，仅用于给前端展示「候选角色列表」，供用户勾选确认。
  - 若未找到对应作品，将返回 `404 Not Found`。

#### 请求体（JSON）

```json
{
  "ip_name": "崩坏：星穹铁道"
}
```

字段说明：

| 字段名   | 类型   | 必填 | 说明                        |
| -------- | ------ | ---- | --------------------------- |
| `ip_name` | string | 是   | IP 作品名，用于在 BGM 中搜索 |

#### 响应体（成功示例）

```json
{
  "ip_name": "崩坏：星穹铁道",
  "characters": [
    {
      "name": "流萤",
      "relation": "主角",
      "avatar": "https://lain.bgm.tv/pic/crt/l/xx/xx/12345.jpg"
    },
    {
      "name": "花火",
      "relation": "配角",
      "avatar": "https://lain.bgm.tv/pic/crt/l/yy/yy/67890.jpg"
    }
  ]
}
```

字段说明：

| 字段名        | 类型           | 说明                                      |
| ------------- | -------------- | ----------------------------------------- |
| `ip_name`     | string         | BGM 返回的作品显示名（优先中文名）        |
| `characters`  | array[object]  | 角色对象数组                              |
| `name`        | string         | 角色名（已解码 HTML 实体，如 `&amp;`）    |
| `relation`    | string         | 角色与作品关系：如「主角」「配角」「客串」 |
| `avatar`      | string         | 角色头像 URL（当前可忽略，仅展示用）      |

> 注意：
> - 后端会对 `relation` 做排序，返回结果中**主角在前、配角其后、客串/其他在最后**。
> - 当前版本不会将头像下载/保存，只透传头像 URL 给前端。

#### 响应体（未找到示例）

```json
{
  "detail": "未找到与 'xxx' 相关的作品"
}
```

状态码：`404 Not Found`

---

### 8.2 根据角色列表批量创建 IP / 角色

- **URL**：`POST /api/bgm/create-characters/`
- **说明**：
  - 前端在「BGM 搜索」页勾选需要导入的角色后，将勾选结果回传给后端。
  - 后端会根据 `ip_name` 和 `character_name` 在本地数据库中**批量创建 IP 和角色**：
    - IP 不存在时：自动创建 `IP` 记录；
    - IP 已存在时：直接在该 IP 下创建角色；
    - 角色已存在（同一 IP 下同名角色）：跳过创建，返回 `already_exists`。
  - 该接口**不调用 BGM API**，只操作本地数据库。

#### 请求体（JSON）

```json
{
  "characters": [
    {
      "ip_name": "崩坏：星穹铁道",
      "character_name": "流萤"
    },
    {
      "ip_name": "崩坏：星穹铁道",
      "character_name": "花火"
    }
  ]
}
```

字段说明：

| 字段名              | 类型            | 必填 | 说明                                  |
| ------------------- | --------------- | ---- | ------------------------------------- |
| `characters`        | array[object]   | 是   | 待创建的角色列表                      |
| `ip_name`           | string          | 是   | IP 作品名，对应 `IP.name`            |
| `character_name`    | string          | 是   | 角色名，对应 `Character.name`        |

> 约束 / 行为：
> - 使用模型约束 `unique_together (ip, name)` 保证**同一 IP 下角色名唯一**；
> - 对于已存在的 (ip, name) 组合，接口会返回 `already_exists`，不会抛异常；
> - 性别 `gender`、头像 `avatar` 当前由后端默认处理：`gender` 默认 `female`，`avatar` 为空。

#### 响应体（成功示例）

```json
{
  "created": 2,
  "skipped": 1,
  "details": [
    {
      "ip_name": "崩坏：星穹铁道",
      "character_name": "流萤",
      "status": "created",
      "ip_id": 1,
      "character_id": 5
    },
    {
      "ip_name": "崩坏：星穹铁道",
      "character_name": "花火",
      "status": "created",
      "ip_id": 1,
      "character_id": 6
    },
    {
      "ip_name": "崩坏：星穹铁道",
      "character_name": "景元",
      "status": "already_exists",
      "ip_id": 1,
      "character_id": 3
    }
  ]
}
```

字段说明：

| 字段名           | 类型          | 说明                                       |
| ---------------- | ------------- | ------------------------------------------ |
| `created`        | integer       | 本次**新创建**的角色数量                   |
| `skipped`        | integer       | 因已存在而被跳过的角色数量                 |
| `details`        | array[object] | 每个请求角色的处理结果明细                 |
| `status`         | string        | `created` / `already_exists` / `error`     |
| `ip_id`          | integer       | 对应 `IP` 记录的主键 ID                    |
| `character_id`   | integer       | 对应 `Character` 记录的主键 ID（若有）     |
| `error`          | string        | 当 `status="error"` 时返回错误信息         |

#### 错误示例

```json
{
  "characters": [
    {
      "ip_name": [
        "This field may not be blank."
      ]
    }
  ]
}
```

状态码：`400 Bad Request`（请求体验证失败，如字段缺失/为空等）

---

### 8.3 推荐的前端使用流程（简版）

1. 用户在前端输入 IP 名称并点击「搜索 BGM」：
   - 调用 `POST /api/bgm/search-characters/` 获取候选角色列表。
2. 前端展示从 BGM 返回的角色列表，用户勾选需要导入的角色：
   - 将勾选结果映射为 `{ ip_name, character_name }` 数组。
3. 用户点击「确认导入」：
   - 调用 `POST /api/bgm/create-characters/`；
   - 导入完成后，前端可以根据返回的 `ip_id` / `character_id` 刷新本地 `IP` / `Character` 列表或直接追加。


