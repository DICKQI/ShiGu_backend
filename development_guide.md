# 二次元谷子收纳系统 - RBAC多租户架构开发需求文档 v2.0

## 1. 项目概述

### 1.1 背景与目标
当前系统为单机版二次元周边管理系统。本阶段目标是将其升级为**多用户（SaaS/家庭版）系统**，支持多账号登录。
核心要求：
1.  **数据隔离**：用户只能管理自己的私有资产（谷子、展柜、分类等）。
2.  **精细化权限控制 (RBAC)**：采用 **用户-角色-权限** 三级模型，配合**装饰器**模式，实现对每一个 API 接口（包括自定义 Action）的精细控制。
3.  **公共资源共享**：IP 作品库和角色库为全局共享资源，但需通过权限控制其维护权。

### 1.2 核心技术栈
*   **后端框架**: Django REST Framework (DRF)
*   **认证方式**: JWT (SimpleJWT)
*   **权限模型**: RBAC (Role-Based Access Control)
*   **控制方式**: 自定义装饰器 `@require_permission`

---

## 2. 数据库设计 (Schema Design)

需新增 `apps/rbac` 应用，并扩展 `apps/users` 应用。

### 2.1 RBAC 核心三表

#### A. 权限表 (Permission)
定义系统所有可执行的原子操作。

```python
class Permission(models.Model):
    name = models.CharField("权限名称", max_length=50)   # 例：查看谷子列表
    code = models.CharField("权限标识", max_length=100, unique=True)  # 例：goods:list
    group = models.CharField("权限分组", max_length=50)  # 例：资产管理（用于前端菜单折叠）
    
    class Meta:
        verbose_name = "权限"
        ordering = ["group", "code"]
```

#### B. 角色表 (Role)
权限的集合。

```python
class Role(models.Model):
    name = models.CharField("角色名称", max_length=50, unique=True) # 例：普通用户、IP管理员
    description = models.CharField("角色描述", max_length=200, blank=True)
    permissions = models.ManyToManyField(Permission, verbose_name="拥有权限", blank=True)
    is_active = models.BooleanField("是否启用", default=True)

    class Meta:
        verbose_name = "角色"
```

#### C. 用户表扩展 (User)
在 `users` 应用中扩展 Django 的 AbstractUser。

```python
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    nickname = models.CharField("昵称", max_length=50, blank=True)
    avatar = models.ImageField("头像", upload_to="users/avatars/", null=True, blank=True)
    
    # 核心关联：用户与角色的多对多关系
    roles = models.ManyToManyField("rbac.Role", verbose_name="所属角色", blank=True)
    
    class Meta:
        verbose_name = "用户"
```

### 2.2 业务表字段变更
需要在现有业务表中增加归属权字段。

| 模型 (Model) | 新增字段 | 类型 | 说明 | 数据隔离策略 |
| :--- | :--- | :--- | :--- | :--- |
| **Goods** | `user` | ForeignKey(User) | 所属用户 | **私有** (仅自己可见) |
| **Showcase** | `user` | ForeignKey(User) | 所属用户 | **私有** (仅自己可见) |
| **Theme** | `user` | ForeignKey(User) | 所属用户 | **私有** (仅自己可见) |
| **Category** | `user` | ForeignKey(User) | 所属用户 | **私有** (仅自己可见) |
| **StorageNode** | `user` | ForeignKey(User) | 所属用户 | **私有** (仅自己可见) |
| **IP** | `created_by` | ForeignKey(User) | 创建人 | **公共** (所有人可见，修改需权限) |
| **Character** | `created_by` | ForeignKey(User) | 创建人 | **公共** (所有人可见，修改需权限) |

---

## 3. 核心鉴权逻辑实现 (RBAC Core)

### 3.1 装饰器实现 (`utils/decorators.py`)
利用 Python 函数属性，将权限 Code 绑定到 ViewSet 的方法上。

```python
from functools import wraps

def require_permission(permission_code):
    """
    权限控制装饰器。
    使用方法：
    @require_permission('goods:create')
    def create(self, request, ...):
    """
    def decorator(func):
        # 将权限标识符附加到函数对象上，供 Permission 类读取
        func.required_permission = permission_code
        
        @wraps(func)
        def wrapper(view_instance, request, *args, **kwargs):
            return func(view_instance, request, *args, **kwargs)
        return wrapper
    return decorator
```

### 3.2 DRF 权限类实现 (`apps/rbac/permissions.py`)
在请求进入视图前进行拦截校验。

```python
from rest_framework.permissions import BasePermission

class RBACPermission(BasePermission):
    """
    基于装饰器标记的精细化 RBAC 权限控制
    """
    def has_permission(self, request, view):
        # 1. 超级管理员拥有上帝权限
        if request.user.is_superuser:
            return True

        # 2. 获取当前请求对应的视图方法
        # view.action 是 DRF ViewSet 的当前方法名 (如 list, create, upload_main_photo)
        if not hasattr(view, view.action):
            return False
            
        handler = getattr(view, view.action)
        
        # 3. 读取装饰器注入的权限标识
        required_code = getattr(handler, 'required_permission', None)
        
        # 如果方法没有加装饰器：
        # 策略：默认拒绝访问（安全优先），或者仅校验登录状态
        if not required_code:
            return True # 这里暂设为 True，依赖 IsAuthenticated 做基础防护

        # 4. 校验用户是否拥有该权限
        # 建议在 Login 时将权限列表缓存至 Redis 或 Token 中，避免频繁查库
        user_permissions = self._get_user_permissions(request.user)
        
        return required_code in user_permissions

    def _get_user_permissions(self, user):
        """获取用户所有角色的权限并去重"""
        if not user.is_authenticated:
            return set()
        
        # 使用 Django ORM 跨表查询
        perms = Permission.objects.filter(role__user=user).values_list('code', flat=True)
        return set(perms)
```

---

## 4. 业务模块改造方案

### 4.1 全局配置
在 `settings.py` 或 ViewSet 基类中配置权限类：
```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated', # 必须登录
        'apps.rbac.permissions.RBACPermission',       # RBAC 校验
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}
```

### 4.2 Goods (谷子) 模块改造
**文件**: `apps/goods/views.py`
**逻辑**: 必须同时满足 RBAC 权限（能不能做）和 数据隔离（对谁做）。

```python
from ..utils.decorators import require_permission

class GoodsViewSet(viewsets.ModelViewSet):
    # ... 原有配置 ...

    # === 1. 数据隔离 (Scope) ===
    def get_queryset(self):
        # 仅返回当前用户的数据
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        # 创建时自动绑定当前用户
        serializer.save(user=self.request.user)

    # === 2. RBAC 权限控制 (Permission) ===
    
    @require_permission('goods:list')
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @require_permission('goods:retrieve')
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @require_permission('goods:create')
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @require_permission('goods:update')
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @require_permission('goods:delete')
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    # 自定义 Action 也要加权限
    @action(detail=True, methods=["post"])
    @require_permission('goods:move')
    def move(self, request, pk=None):
        # ... 原有逻辑 ...
        pass

    @action(detail=True, methods=["post"])
    @require_permission('goods:upload_photo')
    def upload_main_photo(self, request, pk=None):
        # ... 原有逻辑 ...
        pass
```

### 4.3 IP / Character (公共资源) 模块改造
**文件**: `apps/ip/views.py`
**逻辑**: 所有人可读，但仅特定角色可写。

```python
class IPViewSet(viewsets.ModelViewSet):
    # 公共数据，无需 user 过滤，直接 all()
    queryset = IP.objects.all()...

    @require_permission('ip:view')
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # 创建 IP 需要更高级的权限
    @require_permission('ip:create')
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
        
    def perform_create(self, serializer):
        # 记录是谁创建的
        serializer.save(created_by=self.request.user)
```

### 4.4 Category (品类) 模块改造
**文件**: `apps/category/views.py`
**逻辑**: 私有数据。因为品类是树形结构，需确保用户无法将自己的节点挂载到别人的父节点下。

1.  **ViewSet**: 加上 `get_queryset` 过滤 `user=request.user`。
2.  **Serializer**: 修改 `CategoryDetailSerializer`，校验 `parent` 是否属于当前用户。

### 4.5 BGM (Bangumi 导入) 模块改造
**文件**: `apps/bgm/bgm.py` (函数视图)
**逻辑**: 将函数视图改为类视图（APIView）或直接在 `api_view` 上应用装饰器。

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated]) # 可以在这里手动加 RBAC 逻辑
def bgm_search_characters(request):
    # 如果要加 RBAC，建议封装 check_permission 辅助函数
    # if not request.user.has_perm('bgm:search'): raise PermissionDenied
    ...
```
*建议：将 BGM 相关功能重构为 `BGMViewSet`，便于统一管理权限。*

---

## 5. 权限清单 (Permission Registry)

需要在系统初始化（Migration）时预置以下权限 Code。

### 5.1 谷子管理 (Goods)
| 权限名称 | 权限标识 Code | 说明 |
| :--- | :--- | :--- |
| 查看谷子列表 | `goods:list` | 基础权限 |
| 查看谷子详情 | `goods:retrieve` | 含详情及补充图 |
| 创建谷子 | `goods:create` | |
| 编辑谷子 | `goods:update` | |
| 删除谷子 | `goods:delete` | |
| 移动排序 | `goods:move` | 拖拽排序 |
| 上传主图 | `goods:upload_main` | |
| 上传补充图 | `goods:upload_extra` | |
| 查看统计 | `goods:stats` | 查看图表 |

### 5.2 展柜管理 (Showcase)
| 权限名称 | 权限标识 Code | 说明 |
| :--- | :--- | :--- |
| 查看展柜 | `showcase:view` | |
| 创建展柜 | `showcase:create` | |
| 编辑展柜 | `showcase:update` | |
| 删除展柜 | `showcase:delete` | |
| 展柜内谷子管理 | `showcase:manage_goods` | 添加/移除/排序 |

### 5.3 IP/角色库 (IP & Character)
| 权限名称 | 权限标识 Code | 说明 |
| :--- | :--- | :--- |
| 查看IP库 | `ip:view` | 所有用户默认拥有 |
| 创建IP/角色 | `ip:create` | 建议仅限“资深用户”或“管理员” |
| 编辑IP/角色 | `ip:update` | 修正错误信息 |
| 删除IP/角色 | `ip:delete` | 仅限管理员 |
| BGM搜索导入 | `ip:bgm_import` | 调用外部API |

### 5.4 系统基础 (Category/Theme/Location)
| 权限名称 | 权限标识 Code | 说明 |
| :--- | :--- | :--- |
| 分类管理 | `sys:category` | CRUD 私有分类 |
| 主题管理 | `sys:theme` | CRUD 私有主题 |
| 位置管理 | `sys:location` | CRUD 私有存储位置 |

---

## 6. 初始化与迁移策略

### 6.1 用户初始化体验 (User Onboarding)
新用户注册后，数据库是空的，体验极差。需要使用 Django Signals 自动初始化数据。

**apps/users/signals.py**:
```python
@receiver(post_save, sender=User)
def init_user_data(sender, instance, created, **kwargs):
    if created:
        # 1. 分配默认角色 "普通用户"
        default_role = Role.objects.get(name="普通用户")
        instance.roles.add(default_role)
        
        # 2. 创建默认根分类
        Category.objects.create(name="默认分类", user=instance)
        
        # 3. 创建默认收纳位置
        StorageNode.objects.create(name="我的房间", user=instance)
```

### 6.2 现有数据迁移
1.  创建超级管理员账号 (ID=1)。
2.  编写 Migration 脚本，将所有现存的 Goods, Showcase, Category 等数据的 `user_id` 更新为 1。
3.  初始化 `Permission` 表，插入上述所有权限 Code。
4.  初始化 `Role` 表，创建“普通用户”和“IP管理员”，并关联对应权限。

---

## 7. API 接口定义变更

### 7.1 认证模块 (`api/auth/`)
*   `POST /login`: 返回 JWT Token。**响应中应额外包含 `permissions` 列表**，供前端控制按钮显示。
    ```json
    {
        "access": "...",
        "refresh": "...",
        "nickname": "Otaku",
        "permissions": ["goods:list", "goods:create", "ip:view"]
    }
    ```

### 7.2 RBAC 管理模块 (`api/rbac/` - 仅管理员可用)
*   `GET /roles/`: 角色列表。
*   `POST /roles/`: 创建新角色。
*   `POST /roles/{id}/assign_permissions/`: 给角色分配权限。
*   `POST /users/{id}/assign_roles/`: 给用户分配角色。

---

## 8. 开发注意事项

1.  **文件路径隔离**:
    *   修改 `AvatarField` 和 `compress_image`，文件保存路径应改为 `uploads/users/{user_id}/...`，避免文件名冲突且方便清理用户数据。
2.  **关联校验**:
    *   在 Serializer 中，凡是 `PrimaryKeyRelatedField` (如 category_id, theme_id)，必须在 `__init__` 中根据 `request.user` 过滤 QuerySet，防止用户 A 关联了用户 B 的分类。
3.  **缓存**:
    *   用户权限计算涉及多表查询 (User -> Role -> Permission)，建议在 Redis 中缓存 `user_id:permissions` 集合，过期时间与 Token 一致。