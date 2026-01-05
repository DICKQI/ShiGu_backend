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
| `character`    | FK -> `Character`            | 所属角色                                                             |
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
- `image`：如走表单上传，可使用 `multipart/form-data`；本项目示例以 URL 存储为主。

---

## 四、谷子检索与详情 API

### 4.1 谷子列表检索（高性能列表）

- **URL**：`GET /api/goods/`
- **说明**：
  - 用于“快速检索页 / 云展柜列表页”。
  - 返回瘦身字段：**不包含备注、补充图等大字段**。
  - 支持多维过滤（IP/角色/品类/状态/位置）+ 文本搜索。

#### 查询参数（全部可选）

| 参数名       | 类型   | 说明                                                                                          |
| ------------ | ------ | --------------------------------------------------------------------------------------------- |
| `ip`         | int    | IP ID，精确过滤，例如 `/api/goods/?ip=1`                                                     |
| `character`  | int    | 角色 ID，精确过滤                                                                            |
| `category`   | int    | 品类 ID，精确过滤                                                                            |
| `status`     | string | 状态：`in_cabinet` / `outdoor` / `sold`                                                      |
| `location`   | int    | 位置节点 ID，过滤收纳在某一具体节点下的谷子                                                 |
| `search`     | string | 轻量模糊搜索：会同时在 `Goods.name`、`IP.name`、`IPKeyword.value` 上匹配    |
| `page`       | int    | 分页页码（DRF 默认）                                                                         |

> 示例 1：检索“星铁 + 流萤 + 吧唧，当前在馆”的所有谷子：
>
> `/api/goods/?ip=1&character=5&category=2&status=in_cabinet&search=流萤`
>
> 示例 2：如果 IP `崩坏：星穹铁道` 额外配置了关键词 `崩铁`、`HSR`，则：
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
- `id`：谷子 UUID，后续详情/编辑都用此 ID。
- `ip` / `character` / `category`：已展开为简单对象，避免前端再二次请求。
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
- `location`：位置节点 ID，可用于前端联动高亮位置树。
- `additional_photos`：补充图片数组，适合做详情页图片画廊。

---

### 4.3 新建 / 编辑谷子（含幂等性）

> 说明：目前后端对幂等性做了**简易保护**，防止重复录入完全相同的谷子。

- **URL**：`POST /api/goods/`
- **URL**：`PUT /api/goods/{id}/`

#### POST 请求体示例

```json
{
  "name": "流萤限定吧唧",
  "ip": 1,
  "character": 5,
  "category": 1,
  "location": 3,
  "quantity": 1,
  "price": "35.00",
  "purchase_date": "2024-09-20",
  "is_official": true,
  "status": "in_cabinet",
  "notes": "线下展会购入"
}
```

说明：
- 图片上传（`main_photo`、补充图）若通过表单上传，需要由前端改用 `multipart/form-data`。
- 后端会根据以下组合判断是否重复：
  - `ip + character + name + purchase_date + price`
  - 若已存在同组合的记录，则不会新建，而是返回已有实例（幂等）。

**响应**：返回创建后的完整详情（同 4.2）。

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
    "name": "崩坏：星穹铁道"
  },
  {
    "id": 2,
    "name": "原神"
  }
]
```

**字段说明**：
- `id`：IP作品 ID，用于后续筛选参数。
- `name`：完整作品名。

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
  "name": "崩坏：星穹铁道"
}
```

---

#### 5.1.3 创建IP作品

- **URL**：`POST /api/ips/`
- **说明**：创建新的IP作品。

##### 请求体（JSON）

```json
{
  "name": "崩坏：星穹铁道"
}
```

##### 字段说明

| 字段名 | 类型   | 必填 | 说明                     |
| ------ | ------ | ---- | ------------------------ |
| `name` | string | 是   | 作品名，必须唯一，最大长度100字符 |

##### 响应

返回创建后的IP作品详情（同 5.1.2）。

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

```json
{
  "name": "崩坏：星穹铁道（更新）"
}
```

##### 响应

返回更新后的IP作品详情（同 5.1.2）。

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
    "avatar": null
  },
  {
    "id": 6,
    "name": "花火",
    "ip": {
      "id": 1,
      "name": "崩坏：星穹铁道"
    },
    "avatar": "https://cdn.example.com/characters/huohuo.jpg"
  }
]
```

**字段说明**：
- `id`：角色 ID，用于后续筛选参数。
- `name`：角色名。
- `ip`：所属IP作品信息（已展开，避免前端二次请求）。
- `avatar`：角色头像 URL（可选）。

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
  "avatar": null
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
  "avatar": null
}
```

##### 字段说明

| 字段名   | 类型   | 必填 | 说明                                                         |
| -------- | ------ | ---- | ------------------------------------------------------------ |
| `name`   | string | 是   | 角色名，最大长度100字符，同一IP下必须唯一                    |
| `ip_id`  | int    | 是   | 所属IP作品ID（使用 `ip_id` 而非 `ip`）                       |
| `avatar` | string | 否   | 角色头像 URL，如通过表单上传可使用 `multipart/form-data` |

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
  "avatar": "https://cdn.example.com/characters/liuying.jpg"
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

- 优先使用 **精确过滤参数**（`ip`、`character`、`category`、`status`、`location`），减少模糊搜索范围。
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
     - `ip` / `character` / `category` / `status` / `location` / `search`。
   - 列表 Item 展示：
     - 主图：`main_photo`
     - 标题：`name`
     - 副标题：`ip.name + character.name + category.name`
     - 位置：`location_path`

3. **详情页**
   - 路由进入时，用 `id` 调用：`GET /api/goods/{id}/`。
   - 展示：
     - 主图 + `additional_photos` 做画廊
     - 右侧信息卡：`ip/character/category/location_path/price/purchase_date/is_official/status/notes`。

若你后续确定前端框架（如 Vue3 + Pinia），可以在此基础上再补一份前端接口封装示例（TypeScript 类型 + Axios 封装）。***

