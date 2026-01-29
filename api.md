## 谷子检索系统 API 文档（后端：Django + DRF）

面向：前端工程师（Vue / React 等）

说明：
- 所有接口默认返回 `application/json`。
- 谷子列表接口（`GET /api/goods/`）已启用分页，返回格式包含总数、当前页码、上一页/下一页页码等信息。其他列表接口暂未启用分页。
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

| 字段名         | 类型                  | 说明                                                  |
| -------------- | --------------------- | ----------------------------------------------------- |
| `id`           | Integer (PK)          | 自增主键                                              |
| `name`         | Char(100), 唯一, 索引 | 作品名，如：`崩坏：星穹铁道`                          |
| `subject_type` | Integer (可空)        | 作品类型：`1`=书籍, `2`=动画, `3`=音乐, `4`=游戏, `6`=三次元/特摄 |

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
| `avatar` | Char(500，可空)    | 角色头像路径或URL。可以是服务器内的相对路径（如 `characters/xxx.jpg`）或外部URL（如 `https://example.com/avatar.jpg`）。支持文件上传和URL字符串两种方式  |
| `gender` | Char(10)            | 角色性别：`male`(男) / `female`(女) / `other`(其他)，默认 `female` |

> 约束：同一 `ip` 下 `name` 唯一。

#### `Category` 品类表

用于表示品类的树状结构，例如：`周边` -> `吧唧` -> `圆形吧唧`。

| 字段名     | 类型                    | 说明                                                                 |
| ---------- | ----------------------- | -------------------------------------------------------------------- |
| `id`       | Integer (PK)            | 自增主键                                                             |
| `name`     | Char(50)                | 品类名，如：`吧唧`、`立牌`。不同父节点下可以有同名子节点              |
| `parent`   | FK -> `Category` (可空)  | 父级品类 ID，顶层品类为 `null`                                       |
| `path_name`| Char(200), 索引         | 冗余完整路径，如：`周边/吧唧/圆形吧唧`                              |
| `color_tag`| Char(20，可空)          | 颜色标签，用于UI展示的颜色标识，例如：`#FF5733`                    |
| `order`    | Integer                 | 同级展示顺序，越小越靠前，默认 0                                     |

#### `Theme` 主题表

| 字段名       | 类型              | 说明                                      |
| ------------ | ----------------- | ----------------------------------------- |
| `id`         | Integer (PK)      | 自增主键                                  |
| `name`       | Char(100), 唯一, 索引 | 主题名称，如：`夏日主题`、`节日主题`、`限定主题` |
| `description`| Text，可空        | 主题描述，如：`2024年夏季限定主题`         |
| `created_at` | DateTime，可空    | 创建时间                                  |

#### `Goods` 谷子核心表

| 字段名         | 类型                         | 说明                                                                 |
| -------------- | ---------------------------- | -------------------------------------------------------------------- |
| `id`           | UUID (PK)                    | 谷子唯一资产编号（字符串 UUID）                                     |
| `name`         | Char(200), 索引              | 谷子名称，如：`流萤花火双人立牌`                                   |
| `ip`           | FK -> `IP`                   | 所属作品                                                             |
| `characters`   | M2M -> `Character[]`         | 关联角色列表（多对多关系），例如双人立牌可同时关联流萤和花火       |
| `category`     | FK -> `Category`             | 品类                                                                 |
| `theme`        | FK -> `Theme` (可空)         | 主题，允许为空（如：夏日主题、节日主题等）                            |
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

#### `Showcase` 展柜表

用于自定义展示谷子，用户可以创建多个展柜，每个展柜可以包含多个分类（归纳）。

| 字段名        | 类型                  | 说明                                                                 |
| ------------- | --------------------- | -------------------------------------------------------------------- |
| `id`          | UUID (PK)             | 展柜唯一ID（字符串 UUID）                                            |
| `name`        | Char(200), 索引       | 展柜名称                                                             |
| `description` | Text，可空            | 展柜描述                                                             |
| `cover_image` | Image(URL，可空)       | 封面图片 URL                                                         |
| `order`       | BigInteger            | 排序值，值越小越靠前，默认0                                          |
| `is_public`   | Boolean               | 是否公开，默认 `true`（预留字段，用于未来扩展）                      |
| `created_at`  | DateTime              | 创建时间                                                             |
| `updated_at`  | DateTime              | 更新时间                                                             |

#### `ShowcaseGoods` 展柜谷子关联表

用于将谷子添加到展柜中，同一谷子在同一展柜中只能出现一次。

| 字段名      | 类型                         | 说明                                                                 |
| ----------- | ---------------------------- | -------------------------------------------------------------------- |
| `id`        | UUID (PK)                    | 关联唯一ID（字符串 UUID）                                            |
| `showcase`  | FK -> `Showcase`             | 所属展柜                                                             |
| `goods`     | FK -> `Goods`                | 关联谷子（PROTECT，防止误删谷子）                                   |
| `order`     | BigInteger                   | 排序值，用于在分类内排序，值越小越靠前，默认0                         |
| `notes`     | Text，可空                   | 备注，在展柜中的特殊说明                                             |
| `created_at`| DateTime                     | 创建时间                                                             |
| `updated_at`| DateTime                     | 更新时间                                                             |

> 约束：同一展柜下同一谷子唯一（`unique_together (showcase, goods)`）。

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
        "name": "崩坏：星穹铁道",
        "subject_type": 4
      },
      "character": {
        "id": 5,
        "name": "流萤",
        "ip": {
          "id": 1,
          "name": "崩坏：星穹铁道",
          "subject_type": 4
        }
      },
      "category": {
        "id": 2,
        "name": "立牌",
        "parent": 1,
        "path_name": "周边/立牌",
        "color_tag": "#FFC300",
        "order": 10
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
| `character`   | int    | 单个角色 ID，精确过滤，例如 `?character=5`。匹配包含该角色的谷子                             |
| `category`    | int    | **品类树筛选**：传入任意层级品类 ID，匹配该品类及其所有子品类下的谷子。例如：<br>- 选择"吧唧"（ID=2）可筛选出"58mm吧唧"和"75mm吧唧"等所有子品类下的谷子<br>- 选择"58mm吧唧"（ID=5）只筛选出该品类下的谷子 |
| `theme`       | int    | 主题 ID，精确过滤，例如 `/api/goods/?theme=1`                                               |
| `status`      | string | 单状态过滤：`in_cabinet` / `outdoor` / `sold`                                               |
| `status__in`  | string | **多状态过滤**：逗号分隔的状态列表，如：`in_cabinet,sold`                                   |
| `is_official` | bool   | 是否官谷筛选：`true`=只看官谷，`false`=只看非官谷。不传则不过滤                               |
| `location`    | int    | 位置节点 ID，过滤收纳在某一具体节点下的谷子                                                 |
| `search`      | string | 轻量模糊搜索：会同时在 `Goods.name`、`IP.name`、`IPKeyword.value` 上匹配    |
| `page`        | int    | 分页页码，从 1 开始，例如 `?page=1` 表示第一页                                               |
| `page_size`   | int    | 每页数量，默认 18 条，最大 100 条，例如 `?page_size=50`                                      |

> 示例 1：检索"星铁 + 流萤 + 吧唧（包含所有子品类），当前在馆"的所有谷子：
>
> `/api/goods/?ip=1&character=5&category=2&status=in_cabinet&search=流萤`
>
> 说明：如果品类是树形结构（如"吧唧"下有"58mm吧唧/75mm吧唧"），使用 `category=2`（"吧唧"的ID）会自动包含所有子品类的谷子。如果只想筛选"58mm吧唧"，使用 `category=5`（"58mm吧唧"的ID）即可。
>
> 示例 2：检索"星铁 + 流萤 + 吧唧（包含所有子品类），当前在馆 **或 已售出**"的所有谷子（多状态）：
>
> `/api/goods/?ip=1&character=5&category=2&status__in=in_cabinet,sold&search=流萤`
>
> 示例 3：只检索 **官谷**：
>
> `/api/goods/?is_official=true`
>
> 示例 4：只检索 **非官谷**：
>
> `/api/goods/?is_official=false`
>
> 示例 5：如果 IP `崩坏：星穹铁道` 额外配置了关键词 `崩铁`、`HSR`，则：
>
> `/api/goods/?search=崩铁` 或 `/api/goods/?search=HSR` 也可以命中该 IP 及其下所有相关谷子。
>
> 示例 6：检索指定主题的谷子：
>
> `/api/goods/?theme=1`（筛选主题ID为1的所有谷子）

#### 响应示例（分页）

**第一页示例**：

```json
{
  "count": 45,
  "page": 1,
  "page_size": 18,
  "next": 2,
  "previous": null,
  "results": [
    {
      "id": "e4c1cb33-5cd3-4f94-bfc7-9de0b99f5a10",
      "name": "流萤花火双人立牌",
      "ip": {
        "id": 1,
        "name": "崩坏：星穹铁道",
        "subject_type": 4
      },
      "characters": [
        {
          "id": 5,
          "name": "流萤",
          "ip": {
            "id": 1,
            "name": "崩坏：星穹铁道",
            "subject_type": 4
          },
          "avatar": null,
          "gender": "female"
        },
        {
          "id": 6,
          "name": "花火",
          "ip": {
            "id": 1,
            "name": "崩坏：星穹铁道",
            "subject_type": 4
          },
          "avatar": "https://cdn.example.com/characters/huohuo.jpg",
          "gender": "female"
        }
      ],
      "category": {
        "id": 2,
        "name": "立牌"
      },
      "theme": {
        "id": 1,
        "name": "夏日主题",
        "description": "2024年夏季限定主题",
        "created_at": "2024-06-01T00:00:00Z"
      },
      "location_path": "卧室/书桌左侧柜子/第一层",
      "main_photo": "https://cdn.example.com/goods/main/xxx.jpg",
      "status": "in_cabinet",
      "quantity": 1
    }
  ]
}
```

**中间页示例**（例如第 2 页）：

```json
{
  "count": 45,
  "page": 2,
  "page_size": 18,
  "next": 3,
  "previous": 1,
  "results": [...]
}
```

**最后一页示例**（例如第 3 页）：

```json
{
  "count": 45,
  "page": 3,
  "page_size": 18,
  "next": null,
  "previous": 2,
  "results": [...]
}
```

**分页字段说明**：
- `count`：总记录数（整数）。
- `page`：当前页码（整数，从 1 开始）。
- `page_size`：每页数量（整数，默认 18，最大 100）。
- `next`：下一页页码（整数），如果没有下一页则为 `null`。
- `previous`：上一页页码（整数），如果没有上一页则为 `null`。
- `results`：当前页的数据列表（数组）。

**数据字段说明**：
- `id`：谷子 UUID，后续详情/编辑都用此 ID。
- `ip` / `characters` / `category`：已展开为简单对象，避免前端再二次请求。`characters` 为数组，可包含多个角色。
- `location_path`：人类可读的完整路径（前端直接展示即可）。
- `main_photo`：主图 URL，可直接用作列表缩略图（后续可以替换为缩略图 URL）。

**使用示例**：
- 获取第一页（默认每页 18 条）：`GET /api/goods/`
- 获取第二页：`GET /api/goods/?page=2`
- 自定义每页数量：`GET /api/goods/?page=1&page_size=50`
- 组合筛选和分页：`GET /api/goods/?ip=1&character=5&page=2&page_size=30`

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
    "name": "崩坏：星穹铁道",
    "subject_type": 4
  },
  "characters": [
    {
      "id": 5,
      "name": "流萤",
      "ip": {
        "id": 1,
        "name": "崩坏：星穹铁道",
        "subject_type": 4
      },
      "avatar": null,
      "gender": "female"
    },
    {
      "id": 6,
      "name": "花火",
      "ip": {
        "id": 1,
        "name": "崩坏：星穹铁道",
        "subject_type": 4
      },
      "avatar": "https://cdn.example.com/characters/huohuo.jpg",
      "gender": "female"
    }
  ],
  "category": {
    "id": 2,
    "name": "立牌",
    "parent": 1,
    "path_name": "周边/立牌",
    "color_tag": "#FFC300",
    "order": 10
  },
  "theme": {
    "id": 1,
    "name": "夏日主题",
    "description": "2024年夏季限定主题",
    "created_at": "2024-06-01T00:00:00Z"
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
- `theme`：主题信息（可选），如果谷子关联了主题，则显示主题的详细信息；如果未关联主题，则为 `null`。
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
  "theme_id": 1,
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
- `theme_id`：主题ID（可选），例如 `1` 表示"夏日主题"。不传或传 `null` 表示不关联主题。
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

#### 4.3.2 附加图片上传 / 更新接口

- **URL**：`POST /api/goods/{id}/upload-additional-photos/`
- **请求方式**：`multipart/form-data`
- **字段**：
  - `additional_photos`（文件数组，可选）：可一次上传多张图片
  - `photo_ids`（整数数组，可选）：图片ID数组，用于更新已有图片
  - `label`（字符串，可选）：为本次上传的所有图片添加统一标签，例如："背板细节"、"瑕疵点"等

**使用场景**：

1. **创建新图片**：只提供 `additional_photos`（不提供 `photo_ids`）
2. **更新图片和标签**：同时提供 `additional_photos` 和 `photo_ids`（数量必须一致）
3. **只更新标签**：只提供 `photo_ids` 和 `label`（不提供 `additional_photos`）

**说明**：
- 至少需要提供 `additional_photos` 或 `photo_ids` 之一
- 如果同时提供 `photo_ids` 和 `additional_photos`，数量必须一致
- 后台会自动压缩每张图片到约 300KB 以下（若需要）
- 如果提供了 `label`，则本次操作的所有图片都会使用该标签
- 如果不提供 `label`，则图片标签会被设置为空（更新模式下）

##### 场景1：创建新图片（form-data，上传多张图片）

```
additional_photos: <file1>
additional_photos: <file2>
additional_photos: <file3>
label: "背板细节"
```

或者只上传单张图片：

```
additional_photos: <file>
label: "瑕疵点"
```

##### 场景2：更新图片和标签（form-data）

假设已有图片的 ID 为 10、11、12，要更新这些图片：

```
additional_photos: <new_file1>
additional_photos: <new_file2>
additional_photos: <new_file3>
photo_ids: 10
photo_ids: 11
photo_ids: 12
label: "更新后的标签"
```

**注意**：
- `photo_ids` 数组中的每个 ID 必须对应 `additional_photos` 数组中相同位置的图片文件
- 例如：`photo_ids[0]` 对应 `additional_photos[0]`，`photo_ids[1]` 对应 `additional_photos[1]`，以此类推
- 如果提供的 `photo_id` 不存在或不属于该谷子，会返回错误

##### 场景3：只更新标签（form-data）

假设已有图片的 ID 为 10、11、12，只想更新这些图片的标签，不修改图片文件：

```
photo_ids: 10
photo_ids: 11
photo_ids: 12
label: "新的标签"
```

或者清空标签（不提供 label 或提供空字符串）：

```
photo_ids: 10
photo_ids: 11
```

**注意**：
- 只更新标签时，不需要提供 `additional_photos` 文件
- 如果提供了 `label`，所有指定的图片都会更新为该标签
- 如果不提供 `label` 或提供空字符串，标签会被清空

响应：返回更新后的谷子详情（同 4.2），包含所有附加图片信息。

#### 4.3.3 删除附加图片接口

支持两种删除方式：删除单张图片或批量删除多张图片。

##### 方式1：删除单张附加图片

- **URL**：`DELETE /api/goods/{id}/additional-photos/{photo_id}/`
- **说明**：删除指定ID的附加图片
- **参数**：
  - `{id}`：谷子ID（路径参数）
  - `{photo_id}`：附加图片ID（路径参数）

**示例**：

删除 ID 为 10 的附加图片：
```
DELETE /api/goods/abc123/additional-photos/10/
```

**响应**：
- 成功：返回更新后的谷子详情（同 4.2），包含所有附加图片信息
- 失败：`404 Not Found`（图片不存在或不属于该谷子）

##### 方式2：批量删除附加图片

- **URL**：`DELETE /api/goods/{id}/additional-photos/?photo_ids=10,11,12`
- **说明**：批量删除多张附加图片
- **查询参数**：
  - `photo_ids`（字符串，必填）：多个图片ID，用逗号分隔

**示例**：

批量删除 ID 为 10、11、12 的附加图片：
```
DELETE /api/goods/abc123/additional-photos/?photo_ids=10,11,12
```

**响应**：
- 成功：返回更新后的谷子详情（同 4.2），包含所有附加图片信息
- 失败：
  - `400 Bad Request`：如果某些图片ID不存在或不属于该谷子，会返回错误信息
  - `400 Bad Request`：如果 `photo_ids` 参数格式错误

**注意**：
- 批量删除时，如果提供的图片ID中有任何一个不存在或不属于该谷子，整个操作会失败并返回错误
- 删除图片后，存储中的图片文件会根据 Django 的配置自动处理（如果配置了信号处理器）

### 4.4 删除谷子

- **URL**：`DELETE /api/goods/{id}/`
- **说明**：删除指定谷子。关联的补充图片 `GuziImage` 会因外键级联一并删除；若需物理删除存储中的图片，请根据存储后端自行处理。
- **响应**：
  - 成功：`204 No Content`
  - 失败：`404 Not Found`（ID 不存在）

---

### 4.5 谷子排序移动

- **URL**：`POST /api/goods/{id}/move/`
- **说明**：
  - 用于前端拖拽排序场景，实现“将谷子 A 移动到谷子 B 的前面/后面”。
  - 该接口支持跨页排序（只需提供目标位置的锚点 ID 即可），且仅需传输极少量数据，性能高效。

#### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | UUID | 被移动的谷子 ID |

#### 请求体（JSON）

```json
{
  "anchor_id": "a1b2c3d4-...",
  "position": "before"
}
```

字段说明：

| 字段名      | 类型   | 必填 | 说明                                     |
| ----------- | ------ | ---- | ---------------------------------------- |
| `anchor_id` | UUID   | 是   | 锚点谷子 ID（即参考物）                  |
| `position`  | string | 是   | 移动方向：`before`（之前）/ `after`（之后） |

#### 逻辑示例

假设列表顺序为：A(order=10) -> B(order=20) -> C(order=30)。

操作：将 C 移动到 A 之前。  
请求：`POST /api/goods/{C_ID}/move/`，Body: `{"anchor_id": "{A_ID}", "position": "before"}`

结果：
- A 及后续元素自动后移：A(11), B(21)
- C 插入目标位置：C(10)
- 新顺序：C -> A -> B

操作：将 A 移动到 B 之后。  
请求：`POST /api/goods/{A_ID}/move/`，Body: `{"anchor_id": "{B_ID}", "position": "after"}`

结果（示意）：
- 目标位置为 \(B.order + 1 = 21\)（若发生碰撞，后续元素会自动 +1）
- 实际数据库会执行类似：`UPDATE goods SET order = order + 1 WHERE order >= 21`
- A 更新为 21
- 新顺序：B -> A（注：具体数值取决于数据库当前状态，但相对顺序保证正确）

#### 响应示例

```json
{
  "detail": "排序更新成功",
  "id": "e4c1cb33-5cd3-4f94-bfc7-9de0b99f5a10",
  "new_order": 105
}
```

---

### 4.6 谷子统计图表数据（Dashboard）

- **URL**：`GET /api/goods/stats/`
- **说明**：
  - 为前端**统计看板 / 图表页**提供一次性汇总数据，适合用于：
    - 概览卡片（资产数量、金额、数据质量）
    - 饼图 / 柱状图（状态、官谷/同人、作品类型、品类/IP/角色/位置 TopN）
    - 折线 / 面积图（入手趋势、录入趋势）
  - **完全复用** `GET /api/goods/` 的过滤与搜索逻辑（包括树形品类、树形位置），因此：
    - 列表页与统计页的筛选条件可以共用一套 UI（只需切路由或切 Tab）
    - 前端只需把当前筛选条件原样拼到 `/api/goods/stats/` 上即可

#### 查询参数

> 所有参数均为**可选**，未传时按全量数据统计。

- **与列表接口共用的筛选 / 搜索参数**（语义与 4.1 完全一致）：

| 参数名        | 类型   | 说明                                                                                          |
| ------------- | ------ | --------------------------------------------------------------------------------------------- |
| `ip`          | int    | IP ID，精确过滤                                                                               |
| `character`   | int    | 单个角色 ID，匹配**包含该角色**的所有谷子                                                     |
| `category`    | int    | 树形品类筛选：传任意层级品类 ID，自动包含其所有子品类                                        |
| `theme`       | int    | 主题 ID                                                                                       |
| `status`      | string | 单状态过滤：`in_cabinet` / `outdoor` / `sold`                                               |
| `status__in`  | string | 多状态过滤，逗号分隔，如：`in_cabinet,sold`                                                 |
| `is_official` | bool   | 是否官谷：`true`=只看官谷，`false`=只看非官谷                                                 |
| `location`    | int    | 树形位置筛选：节点 ID，自动包含该节点及其所有子节点                                          |
| `search`      | string | 轻量搜索：在 `Goods.name`、`IP.name`、`IPKeyword.value` 上匹配                                |

- **统计专用参数**：

| 参数名           | 类型   | 说明                                                                                                       |
| ---------------- | ------ | ---------------------------------------------------------------------------------------------------------- |
| `top`            | int    | TopN 数量（默认 `10`，最小 1，最大 50），影响：品类/IP/角色/位置 Top 列表的长度                           |
| `group_by`       | string | 趋势时间粒度：`month`（默认）、`week`、`day`。影响 `trends.purchase_date` 和 `trends.created_at` 的 bucket |
| `purchase_start` | date   | 按入手日期下界（含），格式 `YYYY-MM-DD`                                                                   |
| `purchase_end`   | date   | 按入手日期上界（含），格式 `YYYY-MM-DD`                                                                   |
| `created_start`  | date   | 按创建时间下界（含），格式 `YYYY-MM-DD`                                                                   |
| `created_end`    | date   | 按创建时间上界（含），格式 `YYYY-MM-DD`                                                                   |

> 建议用法示例：
>
> - 「只看星铁 IP + 流萤相关 + 在馆 / 已售出，按月统计最近一年的入手情况」：
>   - `/api/goods/stats/?ip=1&character=5&status__in=in_cabinet,sold&group_by=month&purchase_start=2024-01-01`
> - 「只看官谷，观察不同作品类型的占比 + 各 IP Top10」：
>   - `/api/goods/stats/?is_official=true&top=10`

#### 响应结构总览

```json
{
  "meta": { ... },
  "overview": { ... },
  "distributions": { ... },
  "trends": { ... }
}
```

- `meta`：本次统计的**元信息**（如传入的 top / group_by / 时间范围）
- `overview`：概览卡片数据（数量、金额、数据质量）
- `distributions`：各类分布/TopN（适合饼图 / 柱状图 / 条形图）
- `trends`：时间维度趋势（适合折线图 / 面积图）

#### 字段详情

##### 1）`meta` 元信息

```json
{
  "top": 10,
  "group_by": "month",
  "purchase_start": "2024-01-01",
  "purchase_end": null,
  "created_start": null,
  "created_end": null
}
```

说明：
- `top`：当前生效的 TopN 数量（后端已做 1~50 之间的裁剪）
- `group_by`：时间粒度，取值：`month` / `week` / `day`
- 其余字段为时间范围，未传则为 `null`

##### 2）`overview` 概览卡片（适合做上方统计卡）

```json
{
  "goods_count": 120,
  "quantity_sum": 180,
  "value_sum": "10240.50",
  "with_price_count": 100,
  "missing_price_count": 20,
  "with_purchase_date_count": 110,
  "missing_purchase_date_count": 10,
  "with_location_count": 95,
  "missing_location_count": 25,
  "with_main_photo_count": 115,
  "missing_main_photo_count": 5
}
```

推荐前端用法：
- 资产规模类卡片：
  - 「总件数」：`goods_count`
  - 「总数量」：`quantity_sum`
  - 「估算总金额」：`value_sum`（`quantity * price` 汇总，price 为空按 0 处理）
- 数据质量类卡片/进度条：
  - 价格填写率：`with_price_count / goods_count`
  - 入手日期填写率：`with_purchase_date_count / goods_count`
  - 位置填写率：`with_location_count / goods_count`
  - 主图填写率：`with_main_photo_count / goods_count`

##### 3）`distributions` 各类分布 / TopN

结构示例：

```json
{
  "status": [
    {
      "status": "in_cabinet",
      "label": "在馆",
      "goods_count": 80,
      "quantity_sum": 120
    },
    {
      "status": "sold",
      "label": "已售出",
      "goods_count": 20,
      "quantity_sum": 30
    }
  ],
  "is_official": [
    {
      "is_official": true,
      "label": "官谷",
      "goods_count": 90,
      "quantity_sum": 130
    },
    {
      "is_official": false,
      "label": "同人/非官谷",
      "goods_count": 30,
      "quantity_sum": 50
    }
  ],
  "ip_subject_type": [
    {
      "ip__subject_type": 4,
      "label": "游戏",
      "goods_count": 70,
      "quantity_sum": 100
    }
  ],
  "category_top": [
    {
      "category_id": 2,
      "category__name": "立牌",
      "category__path_name": "周边/立牌",
      "category__color_tag": "#FFC300",
      "goods_count": 40,
      "quantity_sum": 60,
      "value_sum": "3500.00"
    }
  ],
  "ip_top": [
    {
      "ip_id": 1,
      "ip__name": "崩坏：星穹铁道",
      "ip__subject_type": 4,
      "subject_type_label": "游戏",
      "goods_count": 50,
      "quantity_sum": 80,
      "value_sum": "5200.00"
    }
  ],
  "character_top": [
    {
      "characters__id": 5,
      "characters__name": "流萤",
      "characters__ip__id": 1,
      "characters__ip__name": "崩坏：星穹铁道",
      "goods_count": 25,
      "quantity_sum": 35,
      "value_sum": "1800.00"
    }
  ],
  "location_top": [
    {
      "location_id": 3,
      "location__name": "第一层",
      "location__path_name": "卧室/书桌左侧柜子/第一层",
      "goods_count": 30,
      "quantity_sum": 45,
      "value_sum": "2600.00"
    }
  ]
}
```

前端图表建议：
- `status`：
  - 饼图：不同状态的占比（使用 `label` + `goods_count`）
  - 条形图：状态 vs `quantity_sum`
- `is_official`：
  - 饼图：官谷 vs 同人占比
- `ip_subject_type`：
  - 饼图/柱状图：作品类型结构（动画/游戏/三次元…）
- `category_top` / `ip_top` / `character_top` / `location_top`：
  - 横向条形图 TopN：
    - x 轴：`goods_count` 或 `value_sum`
    - y 轴：名称（如 `category__path_name`、`ip__name`、`characters__name`、`location__path_name`）
  - 颜色：
    - 可直接使用 `category__color_tag` 渲染品类图表的主色

##### 4）`trends` 时间趋势

结构示例：

```json
{
  "purchase_date": [
    {
      "bucket": "2024-01-01",
      "goods_count": 5,
      "quantity_sum": 7,
      "value_sum": "420.00"
    },
    {
      "bucket": "2024-02-01",
      "goods_count": 8,
      "quantity_sum": 10,
      "value_sum": "680.00"
    }
  ],
  "created_at": [
    {
      "bucket": "2024-01-01",
      "goods_count": 10,
      "quantity_sum": 12
    }
  ]
}
```

说明：
- `bucket`：
  - 按 `group_by` 归并后的时间桶，已序列化为 ISO 字符串（`YYYY-MM-DD`）
  - `group_by=month` 时：通常为每月的第一天，例如 `2024-01-01`
  - `group_by=week` 时：起始日期（Django `TruncWeek` 的行为）
  - `group_by=day` 时：具体日期
- `purchase_date`：
  - 以**入手日期**为时间轴，更贴近真实购入节奏
  - 适合做「购入趋势 / 消费曲线」折线图（x=`bucket`，y=`value_sum` 或 `goods_count`）
- `created_at`：
  - 以**录入系统时间**为时间轴，适合观察录入节奏、补录高峰

前端图表建议：
- 折线图 / 面积图：
  - x 轴：`bucket`（配合日期格式化）
  - y 轴：可以叠加多条线：
    - 「件数」：`goods_count`
    - 「总数量」：`quantity_sum`
    - 「估算金额」：`value_sum`（仅 `purchase_date` 有）
- 可通过切换 `group_by=month|week|day` 做时间粒度切换（注意前端缓存，避免频繁请求）

#### 与列表接口的典型联动示例

1. 用户在列表页设置好筛选条件（IP/角色/品类/状态/位置等）。
2. 点击「统计看板」Tab：
   - 前端直接复用当前 querystring，将 `/api/goods/` 替换为 `/api/goods/stats/`。
   - 示例：列表页 URL 为  
     `/api/goods/?ip=1&character=5&category=2&status__in=in_cabinet,sold`  
     切换到统计页时请求：  
     `/api/goods/stats/?ip=1&character=5&category=2&status__in=in_cabinet,sold&group_by=month&top=10`
3. 使用上文 `overview` / `distributions` / `trends` 分别渲染：
   - 顶部统计卡片（总数/金额/数据质量）
   - 中间一行饼图/条形图（状态、官谷/同人、作品类型）
   - 下方多列 TopN 条形图（品类/IP/角色/位置）
   - 底部趋势折线图（`purchase_date` vs `value_sum`）

> 这样，前端可以在**不再额外设计后端接口**的前提下，完成大部分统计/图表需求。

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
| `subject_type` | int | 按作品类型精确匹配，例如：`4` 表示游戏类型 |
| `subject_type__in` | string | **多类型筛选**：逗号分隔的类型列表，如：`2,4` 表示动画或游戏类型 |
| `search` | string | 轻量搜索：在 `name`、`keywords__value` 上匹配 |

##### 响应示例

```json
[
  {
    "id": 1,
    "name": "崩坏：星穹铁道",
    "subject_type": 4,
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
    "subject_type": null,
    "keywords": [],
    "character_count": 3
  }
]
```

**字段说明**：
- `id`：IP作品 ID，用于后续筛选参数。
- `name`：完整作品名。
- `subject_type`：作品类型，可选值：`1`=书籍, `2`=动画, `3`=音乐, `4`=游戏, `6`=三次元/特摄。可为 `null`。
- `keywords`：IP关键词/别名数组，每个关键词包含 `id` 和 `value` 字段。
- `character_count`：该IP下的角色数量（整数）。

**使用示例**：
- 筛选游戏类型的IP：`GET /api/ips/?subject_type=4`
- 筛选动画或游戏类型的IP：`GET /api/ips/?subject_type__in=2,4`
- 组合筛选：`GET /api/ips/?subject_type=4&name__icontains=星铁`

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
  "subject_type": 4,
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
- `subject_type`：作品类型，可选值：`1`=书籍, `2`=动画, `3`=音乐, `4`=游戏, `6`=三次元/特摄。可为 `null`。
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
  "subject_type": 4,
  "keywords": ["星铁", "崩铁", "HSR"]
}
```

##### 字段说明

| 字段名         | 类型           | 必填 | 说明                                                                 |
| -------------- | -------------- | ---- | -------------------------------------------------------------------- |
| `name`         | string         | 是   | 作品名，必须唯一，最大长度100字符                                    |
| `subject_type` | integer        | 否   | 作品类型：`1`=书籍, `2`=动画, `3`=音乐, `4`=游戏, `6`=三次元/特摄。可为 `null` |
| `keywords`     | array[string]  | 否   | 关键词/别名列表，例如：`["星铁", "崩铁", "HSR"]`。每个关键词最大长度50字符，会自动去重和去空 |

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
  "subject_type": 4,
  "keywords": ["星铁", "崩铁", "HSR", "星穹铁道"]
}
```

**部分更新（PATCH）**：

```json
{
  "subject_type": 2,
  "keywords": ["星铁", "崩铁"]
}
```

##### 字段说明

| 字段名         | 类型           | 必填 | 说明                                                                 |
| -------------- | -------------- | ---- | -------------------------------------------------------------------- |
| `name`         | string         | 否   | 作品名，最大长度100字符（PUT 必填，PATCH 可选）                      |
| `subject_type` | integer        | 否   | 作品类型：`1`=书籍, `2`=动画, `3`=音乐, `4`=游戏, `6`=三次元/特摄。可为 `null`（PUT 可选，PATCH 可选） |
| `keywords`     | array[string]  | 否   | 关键词/别名列表，例如：`["星铁", "崩铁", "HSR"]`。每个关键词最大长度50字符。更新时会**完全替换**现有关键词列表（删除不在列表中的关键词，添加新关键词） |

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
      "name": "崩坏：星穹铁道",
      "subject_type": 4
    },
    "avatar": null,
    "gender": "female"
  },
  {
    "id": 6,
    "name": "花火",
    "ip": {
      "id": 1,
      "name": "崩坏：星穹铁道",
      "subject_type": 4
    },
    "avatar": "https://cdn.example.com/characters/huohuo.jpg",
    "gender": "female"
  }
]
```

**字段说明**：
- `id`：角色 ID，用于后续筛选参数。
- `name`：角色名。
- `ip`：所属IP作品信息（已展开，避免前端二次请求），包含 `subject_type` 字段。
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
      "name": "崩坏：星穹铁道",
      "subject_type": 4
    },
    "avatar": null,
    "gender": "female"
  },
  {
    "id": 6,
    "name": "花火",
    "ip": {
      "id": 1,
      "name": "崩坏：星穹铁道",
      "subject_type": 4
    },
    "avatar": "https://cdn.example.com/characters/huohuo.jpg",
    "gender": "female"
  }
]
```

**字段说明**：
- `id`：角色 ID，用于后续筛选参数。
- `name`：角色名。
- `ip`：所属IP作品信息（已展开，避免前端二次请求），包含 `subject_type` 字段。
- `avatar`：角色头像URL或路径。可以是：
  - 服务器内路径：返回完整URL（如 `http://your-domain.com/media/characters/xxx.jpg`）
  - 外部URL：直接返回（如 `https://example.com/avatar.jpg`）
  - `null`：未设置头像
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
    "name": "崩坏：星穹铁道",
    "subject_type": 4
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

**方式一：使用URL字符串（JSON格式）**

```json
{
  "name": "流萤",
  "ip_id": 1,
  "avatar": "https://example.com/avatar.jpg",
  "gender": "female"
}
```

**方式二：文件上传（multipart/form-data格式）**

```
name: 流萤
ip_id: 1
avatar: <file>
gender: female
```

##### 字段说明

| 字段名   | 类型   | 必填 | 说明                                                         |
| -------- | ------ | ---- | ------------------------------------------------------------ |
| `name`   | string | 是   | 角色名，最大长度100字符，同一IP下必须唯一                    |
| `ip_id`  | int    | 是   | 所属IP作品ID（使用 `ip_id` 而非 `ip`）                       |
| `avatar` | string/file | 否   | 角色头像。支持两种方式：<br>1. **URL字符串**：直接传入外部URL（如 `https://example.com/avatar.jpg`）<br>2. **文件上传**：使用 `multipart/form-data` 上传图片文件，后端会自动压缩到约300KB以下并保存到服务器，返回服务器路径的完整URL |
| `gender` | string | 否   | 角色性别：`male`(男) / `female`(女) / `other`(其他)，不传时后端默认保存为 `female` |

> **头像字段说明**：
> - 如果上传的是文件：文件会被自动压缩（最大300KB），保存到服务器的 `media/characters/` 目录，接口返回完整URL（如 `http://your-domain.com/media/characters/xxx.jpg`）
> - 如果传入的是URL字符串：URL会被直接存储，接口直接返回该URL（如 `https://example.com/avatar.jpg`）
> - 如果传入空字符串或 `null`：不设置头像

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

**方式一：使用URL字符串（JSON格式）**

```json
{
  "name": "流萤（更新）",
  "ip_id": 1,
  "avatar": "https://cdn.example.com/characters/liuying.jpg",
  "gender": "female"
}
```

**方式二：文件上传（multipart/form-data格式）**

```
name: 流萤（更新）
ip_id: 1
avatar: <file>
gender: female
```

> **更新说明**：更新时支持与创建时相同的两种头像方式（URL字符串或文件上传）。如果上传新文件，旧的头像文件（仅限本地文件）会被自动删除。

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

品类支持树形结构，类似位置（StorageNode）的设计，支持无限级层级。

#### 5.3.1 获取品类列表

- **URL**：`GET /api/categories/`
- **说明**：获取所有品类列表，支持按父节点过滤，用于筛选器下拉选项。

##### 查询参数（全部可选）

| 参数名        | 类型   | 说明                                                                 |
| ------------ | ------ | -------------------------------------------------------------------- |
| `name`       | string | 按品类名精确或模糊匹配（`exact` / `icontains`）                      |
| `parent`     | int    | 父级品类 ID，精确过滤，例如 `/api/categories/?parent=1`              |
| `parent__isnull` | boolean | 是否根节点，`true` 表示只获取顶层品类（没有父节点的品类）        |
| `search`     | string | 轻量搜索：在 `name`、`path_name` 上匹配                             |

> 示例：
> - 获取所有顶层品类：`GET /api/categories/?parent__isnull=true`
> - 获取某个品类下的所有子品类：`GET /api/categories/?parent=1`

##### 响应示例

```json
[
  {
    "id": 1,
    "name": "周边",
    "parent": null,
    "path_name": "周边",
    "color_tag": "#FF5733",
    "order": 0
  },
  {
    "id": 2,
    "name": "吧唧",
    "parent": 1,
    "path_name": "周边/吧唧",
    "color_tag": "#33C3F0",
    "order": 0
  },
  {
    "id": 3,
    "name": "圆形吧唧",
    "parent": 2,
    "path_name": "周边/吧唧/圆形吧唧",
    "color_tag": null,
    "order": 0
  },
  {
    "id": 4,
    "name": "立牌",
    "parent": 1,
    "path_name": "周边/立牌",
    "color_tag": "#FFC300",
    "order": 10
  }
]
```

**字段说明**：
- `id`：品类 ID，用于后续筛选参数。
- `name`：品类名称。
- `parent`：父级品类 ID，顶层品类为 `null`。
- `path_name`：完整路径，如：`周边/吧唧/圆形吧唧`。
- `color_tag`：颜色标签，用于UI展示，例如：`#FF5733`。可为 `null`。
- `order`：排序值，控制同级节点的展示顺序，值越小越靠前。

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
  "id": 2,
  "name": "吧唧",
  "parent": 1,
  "path_name": "周边/吧唧",
  "color_tag": "#33C3F0",
  "order": 0
}
```

**字段说明**：同 5.3.1 响应示例。

---

#### 5.3.3 创建品类

- **URL**：`POST /api/categories/`
- **说明**：创建新品类，支持树形结构。如果不提供 `path_name`，系统会根据父节点自动生成。

##### 请求体（JSON）

**创建根节点品类**：

```json
{
  "name": "周边",
  "color_tag": "#FF5733",
  "order": 0
}
```

**创建子品类**：

```json
{
  "name": "吧唧",
  "parent": 1,
  "color_tag": "#33C3F0",
  "order": 0
}
```

**指定完整路径**：

```json
{
  "name": "圆形吧唧",
  "parent": 2,
  "path_name": "周边/吧唧/圆形吧唧",
  "order": 0
}
```

##### 字段说明

| 字段名     | 类型   | 必填 | 说明                                                                 |
| ---------- | ------ | ---- | -------------------------------------------------------------------- |
| `name`     | string | 是   | 品类名，最大长度50字符                                                |
| `parent`   | int    | 否   | 父级品类 ID，顶层品类可为 `null`                                     |
| `path_name`| string | 否   | 完整路径，**可选字段**。如果不提供，系统会根据父节点自动生成：<br>- 有父节点：`父节点路径 + "/" + 当前节点名称`<br>- 无父节点（根节点）：直接使用节点名称 |
| `color_tag`| string | 否   | 颜色标签，用于UI展示，例如：`#FF5733`。最大长度20字符                |
| `order`    | int    | 否   | 排序值，默认 0，控制同级节点的展示顺序                                |

##### 响应

返回创建后的品类详情（同 5.3.2）。

---

#### 5.3.4 更新品类

- **URL**：`PUT /api/categories/{id}/`（完整更新）
- **URL**：`PATCH /api/categories/{id}/`（部分更新）
- **说明**：更新品类信息。当父节点或名称改变时，系统会自动更新 `path_name`。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | 品类主键 `id`   |

##### 请求体（JSON）

**完整更新（PUT）**：

```json
{
  "name": "吧唧（更新）",
  "parent": 1,
  "path_name": "周边/吧唧（更新）",
  "color_tag": "#33C3F0",
  "order": 10
}
```

**部分更新（PATCH）**：

```json
{
  "name": "吧唧（更新）",
  "order": 10
}
```

##### 字段说明

| 字段名     | 类型   | 必填 | 说明                                                                 |
| ---------- | ------ | ---- | -------------------------------------------------------------------- |
| `name`     | string | 否   | 品类名，最大长度50字符（PUT 必填，PATCH 可选）                        |
| `parent`   | int    | 否   | 父级品类 ID，顶层品类可为 `null`（PUT 可选，PATCH 可选）             |
| `path_name`| string | 否   | 完整路径，**可选字段**。如果不提供且父节点或名称改变，系统会自动重新生成 |
| `color_tag`| string | 否   | 颜色标签，用于UI展示，例如：`#FF5733`。最大长度20字符                |
| `order`    | int    | 否   | 排序值，默认 0，控制同级节点的展示顺序                                |

##### 响应

返回更新后的品类详情（同 5.3.2）。

> **注意**：
> - 如果更新了 `parent` 或 `name`，且未提供 `path_name`，系统会自动根据新的父节点和名称重新生成 `path_name`。
> - 如果明确提供了 `path_name`，则使用提供的值。

---

#### 5.3.5 删除品类

- **URL**：`DELETE /api/categories/{id}/`
- **说明**：删除指定的品类。删除父节点时，会**级联删除所有子节点**。删除前会检查是否有商品关联到此品类或其子品类。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | 品类主键 `id`   |

##### 删除行为说明

1. **级联删除**：删除父节点时，会递归删除所有子节点（包括子节点的子节点等）。
2. **商品关联检查**：删除节点前，系统会检查是否有商品关联到该节点及其所有子节点。如果有商品关联，将返回错误，不会执行删除操作。
3. **事务保护**：删除操作在数据库事务中执行，确保原子性。

##### 响应

- **成功**：返回 `204 No Content`
- **失败**：
  - `400 Bad Request`：如果有商品关联到此品类或其子品类，返回错误信息，例如：
    ```json
    {
      "detail": "无法删除：有 5 个商品关联到此品类或其子品类，请先解除关联"
    }
    ```
  - `404 Not Found`：如果品类不存在

##### 示例

假设有以下品类结构：
```
周边 (id: 1)
  └── 吧唧 (id: 2)
      └── 圆形吧唧 (id: 3)
```

删除 `吧唧`（id: 2）时：
- 会同时删除 `圆形吧唧`（id: 3）
- 如果有商品关联到品类 2 或品类 3，删除操作会失败并返回错误

---

#### 5.3.6 获取品类树（一次性下发）

- **URL**：`GET /api/categories/tree/`
- **说明**：
  - 返回所有 `Category` 的扁平列表（含父子关系）。
  - 前端在内存中使用 `id`/`parent` 组装树结构（建议存入 Pinia/Vuex）。
  - 更新频率极低，后续可在此视图外层加缓存（例如 Redis）。

##### 请求参数

无（后续如需分页/筛选再扩展）。

##### 响应示例

```json
[
  {
    "id": 1,
    "name": "周边",
    "parent": null,
    "path_name": "周边",
    "color_tag": "#FF5733",
    "order": 0
  },
  {
    "id": 2,
    "name": "吧唧",
    "parent": 1,
    "path_name": "周边/吧唧",
    "color_tag": "#33C3F0",
    "order": 0
  },
  {
    "id": 3,
    "name": "圆形吧唧",
    "parent": 2,
    "path_name": "周边/吧唧/圆形吧唧",
    "color_tag": null,
    "order": 0
  },
  {
    "id": 4,
    "name": "立牌",
    "parent": 1,
    "path_name": "周边/立牌",
    "color_tag": "#FFC300",
    "order": 10
  }
]
```

**字段说明**：同 5.3.1 响应示例。

---

#### 5.3.7 批量更新品类排序

- **URL**：`POST /api/categories/batch-update-order/`
- **说明**：批量更新多个品类的排序值。用于前端通过拖拽等方式调整品类顺序后，批量更新排序值。支持同时更新多个品类的 `order` 字段。

##### 请求体（JSON）

```json
{
  "items": [
    {
      "id": 1,
      "order": 10
    },
    {
      "id": 2,
      "order": 20
    },
    {
      "id": 4,
      "order": 30
    }
  ]
}
```

##### 字段说明

| 字段名 | 类型           | 必填 | 说明                                                                 |
| ------ | -------------- | ---- | -------------------------------------------------------------------- |
| `items`| array[object]  | 是   | 品类排序项列表，每个项包含 `id` 和 `order` 字段                      |
| `id`   | integer        | 是   | 品类ID                                                               |
| `order`| integer        | 是   | 排序值，值越小越靠前。用于控制同级节点的展示顺序                    |

##### 约束说明

- `items` 列表不能为空
- `items` 列表中不能有重复的品类ID
- 所有提供的品类ID必须存在，否则会返回错误

##### 响应示例

**成功响应**：

```json
{
  "detail": "成功更新 3 个品类的排序",
  "updated_count": 3,
  "categories": [
    {
      "id": 1,
      "name": "周边",
      "parent": null,
      "path_name": "周边",
      "color_tag": "#FF5733",
      "order": 10
    },
    {
      "id": 2,
      "name": "吧唧",
      "parent": 1,
      "path_name": "周边/吧唧",
      "color_tag": "#33C3F0",
      "order": 20
    },
    {
      "id": 4,
      "name": "立牌",
      "parent": 1,
      "path_name": "周边/立牌",
      "color_tag": "#FFC300",
      "order": 30
    }
  ]
}
```

**字段说明**：
- `detail`：操作结果描述
- `updated_count`：成功更新的品类数量
- `categories`：更新后的品类列表（按新的 `order` 值排序）

##### 错误响应

**品类ID不存在**：

```json
{
  "detail": "以下品类ID不存在: [5, 6]"
}
```

状态码：`400 Bad Request`

**请求体验证失败**：

```json
{
  "items": [
    {
      "id": ["This field is required."]
    }
  ]
}
```

状态码：`400 Bad Request`

**items列表为空**：

```json
{
  "items": ["items列表不能为空"]
}
```

状态码：`400 Bad Request`

**有重复的品类ID**：

```json
{
  "items": ["items列表中不能有重复的品类ID"]
}
```

状态码：`400 Bad Request`

##### 使用场景

- **拖拽排序**：前端实现拖拽排序功能后，将新的顺序通过此接口批量更新
- **手动调整顺序**：管理员手动调整品类顺序后，批量提交更新
- **批量初始化排序**：批量设置多个品类的初始排序值

##### 注意事项

1. **事务保护**：更新操作在数据库事务中执行，确保原子性。如果任何一个品类更新失败，整个操作会回滚。
2. **排序范围**：排序值 `order` 只在**同级节点**之间有效。不同父节点下的子节点可以拥有相同的 `order` 值。
3. **性能考虑**：建议前端在用户完成拖拽操作后再调用此接口，避免频繁请求。可以使用防抖（debounce）或节流（throttle）来优化。

##### 示例

假设有以下品类结构：
```
周边 (id: 1, order: 0)
  ├── 吧唧 (id: 2, order: 0)
  └── 立牌 (id: 4, order: 10)
```

用户通过拖拽将顺序调整为：立牌 -> 吧唧，则请求：

```json
{
  "items": [
    {
      "id": 4,
      "order": 0
    },
    {
      "id": 2,
      "order": 10
    }
  ]
}
```

更新后，同级节点（都是"周边"的子节点）的排序变为：
```
周边 (id: 1, order: 0)
  ├── 立牌 (id: 4, order: 0)  ← 现在排在前面
  └── 吧唧 (id: 2, order: 10) ← 现在排在后面
```

---

### 5.4 主题 CRUD 接口

主题用于对谷子进行分类标记，例如：夏日主题、节日主题、限定主题等。

#### 5.4.1 获取主题列表

- **URL**：`GET /api/themes/`
- **说明**：获取所有主题列表，用于筛选器下拉选项。

##### 查询参数（全部可选）

| 参数名      | 类型   | 说明                                    |
| ----------- | ------ | --------------------------------------- |
| `name`      | string | 按主题名精确或模糊匹配（`exact` / `icontains`） |
| `search`    | string | 轻量搜索：在 `name`、`description` 上匹配 |

##### 响应示例

```json
[
  {
    "id": 1,
    "name": "夏日主题",
    "description": "2024年夏季限定主题",
    "created_at": "2024-06-01T00:00:00Z"
  },
  {
    "id": 2,
    "name": "节日主题",
    "description": "节日限定主题",
    "created_at": "2024-09-01T00:00:00Z"
  }
]
```

**字段说明**：
- `id`：主题 ID，用于后续筛选参数。
- `name`：主题名称。
- `description`：主题描述（可选）。
- `created_at`：创建时间。

**使用示例**：
- 搜索主题：`GET /api/themes/?search=夏日`
- 精确匹配：`GET /api/themes/?name=夏日主题`

---

#### 5.4.2 获取主题详情

- **URL**：`GET /api/themes/{id}/`
- **说明**：获取单个主题的详细信息。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | 主题主键 `id`   |

##### 响应示例

```json
{
  "id": 1,
  "name": "夏日主题",
  "description": "2024年夏季限定主题",
  "created_at": "2024-06-01T00:00:00Z"
}
```

**字段说明**：同 5.4.1 响应示例。

---

#### 5.4.3 创建主题

- **URL**：`POST /api/themes/`
- **说明**：创建新主题。

##### 请求体（JSON）

```json
{
  "name": "夏日主题",
  "description": "2024年夏季限定主题"
}
```

##### 字段说明

| 字段名       | 类型   | 必填 | 说明                                      |
| ------------ | ------ | ---- | ----------------------------------------- |
| `name`       | string | 是   | 主题名称，必须唯一，最大长度100字符       |
| `description`| string | 否   | 主题描述，最大长度不限                    |

##### 响应

返回创建后的主题详情（同 5.4.2）。

---

#### 5.4.4 更新主题

- **URL**：`PUT /api/themes/{id}/`（完整更新）
- **URL**：`PATCH /api/themes/{id}/`（部分更新）
- **说明**：更新主题信息。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | 主题主键 `id`   |

##### 请求体（JSON）

**完整更新（PUT）**：

```json
{
  "name": "夏日主题（更新）",
  "description": "2024年夏季限定主题（已更新）"
}
```

**部分更新（PATCH）**：

```json
{
  "description": "2024年夏季限定主题（已更新）"
}
```

##### 字段说明

| 字段名       | 类型   | 必填 | 说明                                      |
| ------------ | ------ | ---- | ----------------------------------------- |
| `name`       | string | 否   | 主题名称，最大长度100字符（PUT 必填，PATCH 可选） |
| `description`| string | 否   | 主题描述（PUT 可选，PATCH 可选）          |

##### 响应

返回更新后的主题详情（同 5.4.2）。

---

#### 5.4.5 删除主题

- **URL**：`DELETE /api/themes/{id}/`
- **说明**：删除指定的主题。删除主题时，关联到该主题的谷子的 `theme` 字段会被设置为 `null`（因为使用了 `SET_NULL` 策略）。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | int  | 主题主键 `id`   |

##### 删除行为说明

1. **关联处理**：删除主题时，所有关联到该主题的谷子的 `theme` 字段会被自动设置为 `null`，不会删除谷子记录。
2. **事务保护**：删除操作在数据库事务中执行，确保原子性。

##### 响应

- **成功**：返回 `204 No Content`
- **失败**：`404 Not Found`（主题不存在）

##### 示例

假设有以下数据：
- 主题：`夏日主题`（id: 1）
- 谷子 A（id: abc123）关联到主题 1

删除 `夏日主题`（id: 1）时：
- 主题记录被删除
- 谷子 A 的 `theme` 字段会被设置为 `null`

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
     - `GET /api/categories/tree/`：品类树（扁平列表），用于筛选器和树形展示
     - `GET /api/themes/`：主题列表，用于筛选器
   - 建议将这些数据缓存到前端状态管理，避免重复请求。

2. **云展柜列表页**
   - 使用 `GET /api/goods/`，根据筛选条件拼 query：
     - `ip` / `character` / `category` / `theme` / `status` / `status__in` / `location` / `search`。
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

**基础示例（搜索所有类型）：**

```json
{
  "ip_name": "崩坏：星穹铁道"
}
```

**指定作品类型示例（仅搜索游戏）：**

```json
{
  "ip_name": "崩坏：星穹铁道",
  "subject_type": 4
}
```

字段说明：

| 字段名        | 类型    | 必填 | 说明                                                                 |
| ------------- | ------- | ---- | -------------------------------------------------------------------- |
| `ip_name`     | string  | 是   | IP 作品名，用于在 BGM 中搜索                                         |
| `subject_type`| integer | 否   | 作品类型筛选：`1`=书籍, `2`=动画, `3`=音乐, `4`=游戏, `6`=三次元/特摄。不传则搜索所有类型 |

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
| `avatar`      | string         | 角色头像 URL（来自BGM API）。可以在后续创建角色时使用此URL作为角色头像  |

> 注意：
> - 后端会对 `relation` 做排序，返回结果中**主角在前、配角其后、客串/其他在最后**。
> - `avatar` 字段包含从 BGM API 获取的头像 URL。在创建角色时，可以将此 URL 传递给后端进行保存（见下方 8.2 接口说明）。
> - `subject_type` 参数用于在 BGM 中筛选特定类型的作品。例如，当搜索「原神」时，如果只想搜索游戏版本，可以传入 `subject_type: 4`；如果不传，则会搜索所有类型（可能包括动画、游戏等）。

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

**基础示例（不指定作品类型和头像）：**

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

**指定作品类型和头像URL示例（推荐）：**

```json
{
  "characters": [
    {
      "ip_name": "崩坏：星穹铁道",
      "character_name": "流萤",
      "subject_type": 4,
      "avatar": "https://lain.bgm.tv/pic/crt/l/xx/xx/12345.jpg"
    },
    {
      "ip_name": "崩坏：星穹铁道",
      "character_name": "花火",
      "subject_type": 4,
      "avatar": "https://lain.bgm.tv/pic/crt/l/yy/yy/67890.jpg"
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
| `subject_type`      | integer         | 否   | 作品类型：`1`=书籍, `2`=动画, `3`=音乐, `4`=游戏, `6`=三次元/特摄。可选，创建新 IP 时使用；如果 IP 已存在但 `subject_type` 为空，且提供了此字段，则更新 IP 的 `subject_type` |
| `avatar`            | string          | 否   | 角色头像 URL。可以是 BGM API 返回的头像 URL（如 `https://lain.bgm.tv/pic/crt/l/xx/xx/12345.jpg`）或其他外部 URL。如果角色已存在且没有头像，会更新头像；如果角色已存在且有头像，则不会覆盖 |

> 约束 / 行为：
> - 使用模型约束 `unique_together (ip, name)` 保证**同一 IP 下角色名唯一**；
> - 对于已存在的 (ip, name) 组合，接口会返回 `already_exists`，不会抛异常；
> - 性别 `gender` 当前由后端默认处理：默认 `female`；
> - 头像 `avatar`：
>   - 如果创建新角色时提供了 `avatar`，会保存该URL；
>   - 如果角色已存在且当前没有头像，会更新头像；
>   - 如果角色已存在且已有头像，则不会覆盖现有头像（保持现有头像不变）；
>   - 可以从 8.1 接口（搜索角色）返回的结果中获取 `avatar` 字段并传递给此接口。
> - `subject_type` 字段：如果创建新 IP 时提供了此字段，会在创建 IP 时设置作品类型；如果 IP 已存在但 `subject_type` 为 `null`，且提供了此字段，则更新 IP 的 `subject_type`。

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
   - 调用 `POST /api/bgm/search-characters/` 获取候选角色列表（包含角色名、关系、头像URL等信息）。
2. 前端展示从 BGM 返回的角色列表，用户勾选需要导入的角色：
   - 将勾选结果映射为包含 `ip_name`、`character_name`、`avatar`（可选）的数组。
   - **推荐**：将 BGM 返回的 `avatar` URL 也一起传递，这样创建的角色会自动包含头像。
3. 用户点击「确认导入」：
   - 调用 `POST /api/bgm/create-characters/`，传递角色信息（包含头像URL）；
   - 导入完成后，前端可以根据返回的 `ip_id` / `character_id` 刷新本地 `IP` / `Character` 列表或直接追加。

> **完整示例**：
> 
> 假设从 8.1 接口返回的角色列表为：
> ```json
> {
>   "ip_name": "崩坏：星穹铁道",
>   "characters": [
>     {
>       "name": "流萤",
>       "relation": "主角",
>       "avatar": "https://lain.bgm.tv/pic/crt/l/xx/xx/12345.jpg"
>     }
>   ]
> }
> ```
>

---

## 九、展柜 API（自定义展示功能）

展柜功能用于自定义展示谷子，与 `GET /api/goods/` 接口的区别在于：
- `GET /api/goods/`：显示**所有谷子**，用于检索和管理所有资产
- 展柜功能：只显示**用户选择加入展柜的谷子**，用于自定义展示特定谷子

展柜采用结构：**展柜 → 谷子**

### 9.1 展柜 CRUD 接口

#### 9.1.1 获取展柜列表

- **URL**：`GET /api/showcases/`
- **说明**：获取所有展柜列表，支持分页。

##### 查询参数（全部可选）

| 参数名      | 类型   | 说明                                    |
| ----------- | ------ | --------------------------------------- |
| `page`      | int    | 分页页码，从 1 开始，例如 `?page=1`     |
| `page_size` | int    | 每页数量，默认 20 条，最大 100 条        |

##### 响应示例（分页）

```json
{
  "count": 5,
  "page": 1,
  "page_size": 20,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "name": "我的收藏展柜",
      "description": "展示我最喜欢的谷子",
      "cover_image": "https://cdn.example.com/showcases/covers/xxx.jpg",
      "order": 0,
      "created_at": "2024-09-21T10:00:00Z"
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
      "name": "星铁主题展柜",
      "description": "崩坏：星穹铁道相关谷子",
      "cover_image": null,
      "order": 1000,
      "created_at": "2024-09-22T10:00:00Z"
    }
  ]
}
```

**字段说明**：
- `id`：展柜 UUID，用于后续操作
- `name`：展柜名称
- `description`：展柜描述（可选）
- `cover_image`：封面图片 URL（可选）
- `order`：排序值，值越小越靠前
- `created_at`：创建时间

---

#### 9.1.2 获取展柜详情

- **URL**：`GET /api/showcases/{id}/`
- **说明**：获取单个展柜的详细信息，包含所有分类和谷子。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | UUID | 展柜主键 `id`   |

##### 响应示例

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "我的收藏展柜",
  "description": "展示我最喜欢的谷子",
  "cover_image": "https://cdn.example.com/showcases/covers/xxx.jpg",
  "order": 0,
  "is_public": true,
  "showcase_goods": [
    {
      "id": "e5f6a7b8-c9d0-1234-ef56-567890123456",
      "goods": {
        "id": "e4c1cb33-5cd3-4f94-bfc7-9de0b99f5a10",
        "name": "流萤花火双人立牌",
        "ip": {
          "id": 1,
          "name": "崩坏：星穹铁道",
          "subject_type": 4
        },
        "characters": [
          {
            "id": 5,
            "name": "流萤",
            "ip": {
              "id": 1,
              "name": "崩坏：星穹铁道",
              "subject_type": 4
            },
            "avatar": null,
            "gender": "female"
          }
        ],
        "category": {
          "id": 2,
          "name": "立牌"
        },
        "theme": null,
        "location_path": "卧室/书桌左侧柜子/第一层",
        "main_photo": "https://cdn.example.com/goods/main/xxx.jpg",
        "status": "in_cabinet",
        "quantity": 1,
        "is_official": true,
        "order": 0
      },
      "order": 0,
      "notes": "最喜欢的立牌",
      "created_at": "2024-09-21T10:00:00Z",
      "updated_at": "2024-09-21T10:00:00Z"
    }
  ],
  "created_at": "2024-09-21T10:00:00Z",
  "updated_at": "2024-09-21T10:00:00Z"
}
```

**字段说明**：
- `showcase_goods`：展柜中的所有谷子关联列表，包含完整的谷子信息（使用 `GoodsListSerializer`）

---

#### 9.1.3 创建展柜

- **URL**：`POST /api/showcases/`
- **说明**：创建新展柜。

##### 请求体（JSON）

```json
{
  "name": "我的收藏展柜",
  "description": "展示我最喜欢的谷子",
  "cover_image": null,
  "is_public": true
}
```

##### 字段说明

| 字段名        | 类型    | 必填 | 说明                                      |
| ------------- | ------- | ---- | ----------------------------------------- |
| `name`        | string  | 是   | 展柜名称，最大长度200字符                 |
| `description` | string  | 否   | 展柜描述                                  |
| `cover_image` | file    | 否   | 封面图片，支持 `multipart/form-data` 上传 |
| `is_public`   | boolean | 否   | 是否公开，默认 `true`                     |

> **封面图片说明**：
> - 如果使用 JSON 格式，`cover_image` 字段暂不支持（需后续单独上传）
> - 如果使用 `multipart/form-data` 格式，可以同时上传封面图片，后台会自动压缩到约 300KB 以下

#### 9.1.3.1 展柜封面上传 / 更新接口

- **URL**：`POST /api/showcases/{id}/upload-cover-image/`
- **请求方式**：`multipart/form-data`
- **字段**：`cover_image`（文件，必填）
- **说明**：独立上传或更新展柜封面，后台会自动压缩到约 300KB 以下（若需要）。

示例（form-data）：

```
cover_image: <file>
```

响应：返回更新后的展柜详情（同 9.1.2）。

##### 响应

返回创建后的展柜详情（同 9.1.2）。

---

#### 9.1.4 更新展柜

- **URL**：`PUT /api/showcases/{id}/`（完整更新）
- **URL**：`PATCH /api/showcases/{id}/`（部分更新）
- **说明**：更新展柜信息。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | UUID | 展柜主键 `id`   |

##### 请求体（JSON）

**完整更新（PUT）**：

```json
{
  "name": "我的收藏展柜（更新）",
  "description": "更新后的描述",
  "is_public": true
}
```

**部分更新（PATCH）**：

```json
{
  "description": "更新后的描述"
}
```

##### 字段说明

| 字段名        | 类型    | 必填 | 说明                                      |
| ------------- | ------- | ---- | ----------------------------------------- |
| `name`        | string  | 否   | 展柜名称，最大长度200字符（PUT 必填，PATCH 可选） |
| `description` | string  | 否   | 展柜描述（PUT 可选，PATCH 可选）          |
| `cover_image` | file    | 否   | 封面图片，支持 `multipart/form-data` 上传 |
| `is_public`   | boolean | 否   | 是否公开（PUT 可选，PATCH 可选）          |

##### 响应

返回更新后的展柜详情（同 9.1.2）。

---

#### 9.1.5 删除展柜

- **URL**：`DELETE /api/showcases/{id}/`
- **说明**：删除指定的展柜。删除展柜时，会**级联删除所有分类和谷子关联**。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | UUID | 展柜主键 `id`   |

##### 删除行为说明

1. **级联删除**：删除展柜时，会同时删除：
   - 该展柜下的所有分类（`ShowcaseCategory`）
   - 该展柜下的所有谷子关联（`ShowcaseGoods`）
2. **不影响谷子**：删除展柜不会删除谷子本身（`Goods` 记录），只是移除了展柜关联
3. **事务保护**：删除操作在数据库事务中执行，确保原子性

##### 响应

- **成功**：返回 `204 No Content`
- **失败**：`404 Not Found`（展柜不存在）

---

### 9.2 展柜谷子管理接口

#### 9.2.1 获取展柜中的所有谷子

- **URL**：`GET /api/showcases/{id}/goods/`
- **说明**：获取指定展柜中的所有谷子。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | UUID | 展柜主键 `id`   |

##### 响应示例

```json
[
  {
    "id": "e5f6a7b8-c9d0-1234-ef56-567890123456",
    "goods": {
      "id": "e4c1cb33-5cd3-4f94-bfc7-9de0b99f5a10",
      "name": "流萤花火双人立牌",
      "ip": {
        "id": 1,
        "name": "崩坏：星穹铁道",
        "subject_type": 4
      },
      "characters": [
        {
          "id": 5,
          "name": "流萤",
          "ip": {
            "id": 1,
            "name": "崩坏：星穹铁道",
            "subject_type": 4
          },
          "avatar": null,
          "gender": "female"
        }
      ],
      "category": {
        "id": 2,
        "name": "立牌"
      },
      "theme": null,
      "location_path": "卧室/书桌左侧柜子/第一层",
      "main_photo": "https://cdn.example.com/goods/main/xxx.jpg",
      "status": "in_cabinet",
      "quantity": 1,
      "is_official": true,
      "order": 0
    },
    "order": 0,
    "notes": "最喜欢的立牌",
    "created_at": "2024-09-21T10:00:00Z",
    "updated_at": "2024-09-21T10:00:00Z"
  }
]
```

**字段说明**：
- `goods`：完整的谷子信息（使用 `GoodsListSerializer`）
- `order`：在分类内的排序值
- `notes`：在展柜中的备注

**使用示例**：
- 获取展柜中的所有谷子：`GET /api/showcases/{id}/goods/`

---

#### 9.2.2 添加谷子到展柜

- **URL**：`POST /api/showcases/{id}/add-goods/`
- **说明**：将谷子添加到展柜中。同一谷子在同一展柜中只能出现一次。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | UUID | 展柜主键 `id`   |

##### 请求体（JSON）

```json
{
  "goods_id": "e4c1cb33-5cd3-4f94-bfc7-9de0b99f5a10",
  "notes": "最喜欢的立牌"
}
```

##### 字段说明

| 字段名       | 类型   | 必填 | 说明                                    |
| ------------ | ------ | ---- | --------------------------------------- |
| `goods_id`   | UUID   | 是   | 谷子ID                                  |
| `notes`      | string | 否   | 备注，在展柜中的特殊说明                 |

##### 约束说明

- 同一谷子在同一展柜中只能出现一次
- 如果谷子不存在，会返回 `404 Not Found`

##### 响应示例

**成功响应**：

```json
{
  "id": "e5f6a7b8-c9d0-1234-ef56-567890123456",
  "goods": {
    "id": "e4c1cb33-5cd3-4f94-bfc7-9de0b99f5a10",
    "name": "流萤花火双人立牌",
    ...
  },
  "order": -1000,
  "notes": "最喜欢的立牌",
  "created_at": "2024-09-21T10:00:00Z",
  "updated_at": "2024-09-21T10:00:00Z"
}
```

**错误响应**：

```json
{
  "detail": "该谷子已在此展柜中"
}
```

状态码：`400 Bad Request`

---

#### 9.2.3 从展柜移除谷子

- **URL**：`POST /api/showcases/{id}/remove-goods/`
- **说明**：从展柜中移除指定的谷子。移除操作不会删除谷子本身，只是移除了展柜关联。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | UUID | 展柜主键 `id`   |

##### 请求体（JSON）

```json
{
  "goods_id": "e4c1cb33-5cd3-4f94-bfc7-9de0b99f5a10"
}
```

##### 字段说明

| 字段名     | 类型 | 必填 | 说明   |
| ---------- | ---- | ---- | ------ |
| `goods_id` | UUID | 是   | 谷子ID |

##### 响应示例

**成功响应**：

```json
{
  "detail": "已从展柜移除"
}
```

**错误响应**：

```json
{
  "detail": "该谷子不在此展柜中"
}
```

状态码：`404 Not Found`

---

#### 9.2.4 移动展柜中谷子的位置

- **URL**：`POST /api/showcases/{id}/move-goods/`
- **说明**：移动展柜中谷子的位置。使用稀疏排序算法，性能高效。

##### 路径参数

| 参数名 | 类型 | 说明            |
| ------ | ---- | --------------- |
| `id`   | UUID | 展柜主键 `id`   |

##### 请求体（JSON）

**同一分类内移动**：

```json
{
  "goods_id": "e4c1cb33-5cd3-4f94-bfc7-9de0b99f5a10",
  "anchor_goods_id": "f5a6b7c8-d9e0-2345-fa67-678901234567",
  "position": "before"
}
```

##### 字段说明

| 字段名            | 类型   | 必填 | 说明                                                                 |
| ----------------- | ------ | ---- | -------------------------------------------------------------------- |
| `goods_id`        | UUID   | 是   | 要移动的谷子ID                                                       |
| `anchor_goods_id` | UUID   | 是   | 锚点谷子ID（即要移动到哪个谷子的前面或后面）                         |
| `position`        | string | 是   | 移动位置：`before`（之前）/ `after`（之后）                          |

##### 逻辑示例

假设展柜中"流萤相关"分类下的顺序为：A(order=10) -> B(order=20) -> C(order=30)。

**操作1**：将 C 移动到 A 之前  
请求：`POST /api/showcases/{id}/move-goods/`，Body: `{"goods_id": "{C_ID}", "anchor_goods_id": "{A_ID}", "position": "before"}`  
结果：C 插入到 A 之前，新顺序：C -> A -> B

**操作2**：将 A 移动到 B 之后  
请求：`POST /api/showcases/{id}/move-goods/`，Body: `{"goods_id": "{A_ID}", "anchor_goods_id": "{B_ID}", "position": "after"}`  
结果：A 移动到 B 之后，新顺序：B -> A -> C

##### 响应示例

```json
{
  "detail": "排序更新成功",
  "id": "e5f6a7b8-c9d0-1234-ef56-567890123456",
  "new_order": 105
}
```

**字段说明**：
- `detail`：操作结果描述
- `id`：移动的展柜谷子关联ID
- `new_order`：新的排序值

---

### 9.4 展柜功能使用建议

#### 9.4.1 前端集成流程

1. **创建展柜**
   - 用户创建新展柜：`POST /api/showcases/`
   - 创建后可以上传封面图片（可选）

2. **创建分类**
   - 本版本不包含“展柜分类”功能，直接管理展柜内谷子列表

3. **添加谷子**
   - 从谷子列表中选择谷子添加到展柜：`POST /api/showcases/{id}/add-goods/`

4. **管理展柜**
   - 查看展柜详情：`GET /api/showcases/{id}/`（包含所有分类和谷子）
   - 查看展柜中的谷子：`GET /api/showcases/{id}/goods/`
   - 移动谷子位置：`POST /api/showcases/{id}/move-goods/`（支持拖拽排序）
   - 移除谷子：`POST /api/showcases/{id}/remove-goods/`

#### 9.4.2 与现有功能的对比

| 功能 | 现有 Goods 接口 | 展柜功能 |
|------|----------------|---------|
| 数据范围 | 所有谷子 | 用户选择的谷子 |
| 组织方式 | 按 IP/角色/品类等维度筛选 | 按展柜和分类组织 |
| 用途 | 检索和管理所有资产 | 自定义展示特定谷子 |
| 排序 | 全局排序 | 展柜内排序 |

#### 9.4.3 典型使用场景

- **主题展柜**：创建一个"星铁主题展柜"，添加多个分类（如"流萤相关"、"花火相关"），将相关谷子添加到对应分类
- **收藏展柜**：创建一个"我的收藏展柜"，将最喜欢的谷子添加进去
- **展示展柜**：创建一个公开展柜，用于向他人展示自己的收藏

---
 用户勾选后，传递给 8.2 接口的数据应为：
> ```json
> {
>   "characters": [
>     {
>       "ip_name": "崩坏：星穹铁道",
>       "character_name": "流萤",
>       "avatar": "https://lain.bgm.tv/pic/crt/l/xx/xx/12345.jpg"
>     }
>   ]
> }
> ```


