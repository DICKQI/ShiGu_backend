这份需求文档旨在指导 AI Agent（如 Cursor）在一个现有的 Django 谷子收纳系统中集成 RBAC（基于角色的访问控制）权限系统。

文档遵循你的核心需求：**基于装饰器/Permission类控制接口**、**数据归属隔离**以及**公共数据与私有数据的权限区分**。

---

# 开发需求文档：谷子收纳系统 RBAC 权限与账号体系集成

## 1. 项目概述与目标
当前系统包含 `goods` (谷子资产) 和 `location` (收纳位置) 两个核心 App。目前所有数据均为全局共享，无用户区分。
**本次开发目标**：引入用户账号体系，实现基于角色的访问控制（RBAC），确保数据安全与隐私隔离。

## 2. 核心角色定义 (Roles)
系统包含两类角色：
1.  **普通用户 (User)**：
    *   拥有自己的“私有空间”。
    *   只能对自己创建的数据进行 CRUD（增删改查）。
    *   只能查看（只读）公共元数据。
2.  **管理员 (Admin)**：
    *   拥有最高权限。
    *   可以管理公共元数据（IP、角色、品类）。
    *   可以查看所有用户的数据（用于运维，可选），但在业务逻辑上主要负责维护公共库。

## 3. 权限范围矩阵 (Permission Matrix)

| 模型 (Model) | 归属类型 | 普通用户权限 | 管理员权限 | 备注 |
| :--- | :--- | :--- | :--- | :--- |
| **IP (作品)** | 公共 | Read Only | CRUD | 公共元数据 |
| **Character (角色)** | 公共 | Read Only | CRUD | 公共元数据 |
| **Category (品类)** | 公共 | Read Only | CRUD | 公共元数据 |
| **Theme (主题)** | **私有** | CRUD (仅限本人数据) | CRUD (所有) | 用户自定义收藏主题 |
| **Goods (谷子)** | **私有** | CRUD (仅限本人数据) | CRUD (所有) | 核心资产，严格隔离 |
| **Showcase (展柜)** | **私有** | CRUD (仅限本人数据) | CRUD (所有) | *注：含 is_public 字段，需特殊处理* |
| **StorageNode (位置)**| **私有** | CRUD (仅限本人数据) | CRUD (所有) | 用户的物理收纳结构 |

## 4. 数据库变更需求 (Database Schema Changes)

需要对现有模型进行迁移，增加用户关联字段。

### 4.1 新增/修改 App: `users`
*   创建或配置 Django 自带的 `User` 模型，建议扩展一个 `UserProfile` 或直接使用 AbstractUser 以备未来扩展。

### 4.2 模型字段变更
以下模型需要添加 `user` 外键字段（`on_delete=models.CASCADE`），并建立索引：
1.  `goods.models.Goods`
2.  `goods.models.Theme`
3.  `goods.models.Showcase`
4.  `location.models.StorageNode`

**注意**：
*   `Category`, `IP`, `Character` **不需要**添加 user 字段，它们默认为系统公共资源。
*   数据迁移策略：如果数据库中已有数据，需设置默认归属为管理员账号（ID=1）。

## 5. 权限枚举与工具类设计 (Core Logic)

为了满足“使用装饰器/配置控制接口”的需求，需要定义清晰的权限策略枚举和 DRF Permission 类。

### 5.1 权限枚举类 (enums.py)
在 `utils/permissions.py` 或 `core/constants.py` 中定义权限标识：

```python
from enum import Enum

class PermissionPolicy(Enum):
    # 公共只读，管理员可写 (用于 IP, Character, Category)
    PUBLIC_READ_ADMIN_WRITE = "public_read_admin_write"
    
    # 私有隔离 (用于 Goods, Theme, StorageNode)
    OWNER_ISOLATION = "owner_isolation"
    
    # 混合模式 (用于 Showcase - 只有自己能改，但如果是公开的别人能看)
    OWNER_WRITE_PUBLIC_READ = "owner_write_public_read"
```

### 5.2 自定义权限类 (permissions.py)
基于 DRF `BasePermission` 实现以下类：

1.  `IsAdminOrReadOnly`:
    *   Safe methods (GET, HEAD, OPTIONS) -> Allow Any/Authenticated.
    *   Unsafe methods (POST, PUT, DELETE) -> Only Admin.
2.  `IsOwnerOnly`:
    *   所有操作仅允许 `obj.user == request.user`。
3.  `IsOwnerOrPublicReadOnly`:
    *   Read -> Allow if `obj.is_public` is True OR `obj.user == request.user`.
    *   Write -> Only `obj.user == request.user`.

## 6. 视图层改造 (View Layer Refactoring)

所有 ViewSet 需要进行两方面的改造：
1.  **权限控制**：配置 `permission_classes`。
2.  **数据隔离**：重写 `get_queryset` 和 `perform_create`。

### 6.1 公共资源视图 (`IPViewSet`, `CharacterViewSet`, `CategoryViewSet`)
*   **权限配置**: `permission_classes = [IsAdminOrReadOnly]`
*   **查询集**: 保持 `objects.all()`，无需按用户过滤。

### 6.2 私有资源视图 (`GoodsViewSet`, `ThemeViewSet`, `StorageNodeViewSet`)
*   **权限配置**: `permission_classes = [IsAuthenticated, IsOwnerOnly]`
*   **查询集**: 重写 `get_queryset`。
    ```python
    def get_queryset(self):
        # 管理员可以看到所有（可选），普通用户只能看自己的
        if self.request.user.is_staff:
            return super().get_queryset()
        return super().get_queryset().filter(user=self.request.user)
    ```
*   **创建逻辑**: 重写 `perform_create` 自动注入 user。
    ```python
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    ```

### 6.3 特殊资源视图 (`ShowcaseViewSet`)
*   **权限配置**: `permission_classes = [IsAuthenticated, IsOwnerOrPublicReadOnly]`
*   **查询集**:
    ```python
    def get_queryset(self):
        user = self.request.user
        # 返回：属于自己的 OR (别人的 AND is_public=True)
        return Showcase.objects.filter(Q(user=user) | Q(is_public=True))
    ```

## 7. 搜索与聚合接口改造
*   **Stats (统计接口)**: `GoodsViewSet.stats` 需要确保统计数据仅基于 `get_queryset` 过滤后的结果（即只统计用户自己的谷子）。
*   **BGM 接口**: 这是一个外部工具接口，建议设置为 `IsAuthenticated` (登录用户均可使用)。

## 8. 具体实施步骤 (Step-by-Step for Agent)

请按以下顺序执行代码编写：

1.  **Step 1: 模型迁移**
    *   修改 `Goods`, `Theme`, `Showcase`, `StorageNode` 模型，添加 `user` ForeignKey。
    *   生成并应用 Migration 文件（注意处理 nullable 或 default value）。

2.  **Step 2: 权限类实现**
    *   在共有目录下创建 `permissions.py`，实现 `IsAdminOrReadOnly` 和 `IsOwnerOnly`。

3.  **Step 3: 改造 IP/Character/Category 视图**
    *   引入权限类。
    *   移除这些视图中可能的 `perform_create` 逻辑（如果之前有硬编码逻辑），确保只有 Admin 能调。

4.  **Step 4: 改造 Goods/Theme/StorageNode 视图**
    *   实现数据隔离逻辑 (`filter(user=request.user)`).
    *   实现自动归属逻辑 (`save(user=request.user)`).
    *   修复 FilterSet，确保过滤条件是基于用户私有数据的。

5.  **Step 5: 验证 BGM 与上传接口**
    *   确保 `@action` 装饰的自定义接口（如 `upload_cover_image`）也继承了 ViewSet 的权限配置或显式指定了权限。

## 9. 验收标准
1.  **普通用户登录后**：
    *   `GET /api/ips/` -> 成功。
    *   `POST /api/ips/` -> 403 Forbidden。
    *   `GET /api/goods/` -> 只能看到自己创建的谷子。
    *   `POST /api/goods/` -> 创建成功，数据库中该记录 `user_id` 为当前用户。
2.  **未登录用户**：
    *   访问任何 API 均返回 401 Unauthorized（除登录/注册接口外）。
3.  **管理员登录后**：
    *   可以 CRUD 所有 IP/Character/Category。

---

**给 Cursor 的提示词 (Prompt):**
"请基于上述《谷子收纳系统 RBAC 权限需求文档》，对现有的 `goods` 和 `location` 代码进行重构。首先进行 Model 的变更，然后编写自定义 Permission 类，最后修改 ViewSet 以实现数据隔离和权限控制。请确保代码风格与现有代码保持一致。"