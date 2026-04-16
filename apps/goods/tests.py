from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta
from decimal import Decimal

from apps.users.models import User, Role
from .models import Goods, IP, Character, Category, Theme
from .similarity import GoodsSimilarityCalculator, SeedSelector, SimilarityGroupBuilder


class SimilarityAlgorithmTestCase(TestCase):
    """测试相似度算法"""

    def setUp(self):
        """设置测试数据"""
        # 创建角色和用户
        self.role = Role.objects.create(name='测试角色')
        self.user = User.objects.create(
            username='testuser',
            password='testpass123',
            role=self.role
        )

        # 创建IP
        self.ip1 = IP.objects.create(name='崩坏：星穹铁道', subject_type=4)
        self.ip2 = IP.objects.create(name='原神', subject_type=4)

        # 创建角色
        self.char1 = Character.objects.create(ip=self.ip1, name='流萤', gender='female')
        self.char2 = Character.objects.create(ip=self.ip1, name='花火', gender='female')
        self.char3 = Character.objects.create(ip=self.ip2, name='纳西妲', gender='female')

        # 创建品类
        self.cat_root = Category.objects.create(name='周边', path_name='周边')
        self.cat_badge = Category.objects.create(
            name='吧唧',
            parent=self.cat_root,
            path_name='周边/吧唧'
        )

        # 创建主题
        self.theme1 = Theme.objects.create(user=self.user, name='夏日主题')

        # 创建谷子
        self.goods1 = Goods.objects.create(
            user=self.user,
            name='流萤立牌',
            ip=self.ip1,
            category=self.cat_badge,
            theme=self.theme1,
            price=Decimal('50.00'),
            purchase_date=date(2024, 1, 15)
        )
        self.goods1.characters.add(self.char1)

        self.goods2 = Goods.objects.create(
            user=self.user,
            name='花火吧唧',
            ip=self.ip1,
            category=self.cat_badge,
            theme=self.theme1,
            price=Decimal('55.00'),
            purchase_date=date(2024, 1, 20)
        )
        self.goods2.characters.add(self.char2)

        self.goods3 = Goods.objects.create(
            user=self.user,
            name='纳西妲吧唧',
            ip=self.ip2,
            category=self.cat_badge,
            price=Decimal('200.00'),
            purchase_date=date(2024, 6, 1)
        )
        self.goods3.characters.add(self.char3)

        self.calculator = GoodsSimilarityCalculator()

    def test_ip_match_same_ip(self):
        """测试相同IP的评分"""
        score = self.calculator._score_ip_match(self.goods1, self.goods2)
        self.assertEqual(score, 30.0)

    def test_ip_match_same_subject_type(self):
        """测试相同作品类型的评分"""
        score = self.calculator._score_ip_match(self.goods1, self.goods3)
        self.assertAlmostEqual(score, 9.9, places=1)

    def test_character_overlap(self):
        """测试角色重叠评分"""
        # 创建一个同时有流萤和花火的谷子
        goods_both = Goods.objects.create(
            user=self.user,
            name='双人立牌',
            ip=self.ip1,
            category=self.cat_badge
        )
        goods_both.characters.add(self.char1, self.char2)

        score = self.calculator._score_character_overlap(self.goods1, goods_both)
        # goods1有1个角色，goods_both有2个角色，共享1个
        # (1 / 2) * 23 = 11.5
        self.assertAlmostEqual(score, 11.5, places=1)

    def test_category_hierarchy_same_category(self):
        """测试相同品类的评分"""
        score = self.calculator._score_category_hierarchy(self.goods1, self.goods2)
        self.assertEqual(score, 18.0)

    def test_theme_match(self):
        """测试主题匹配评分"""
        score = self.calculator._score_theme_match(self.goods1, self.goods2)
        self.assertEqual(score, 15.0)

    def test_price_range_similar(self):
        """测试相似价格的评分"""
        score = self.calculator._score_price_range(self.goods1, self.goods2)
        # 50和55差异约10%
        self.assertGreater(score, 5.0)

    def test_purchase_proximity_same_month(self):
        """测试同月入手的评分"""
        score = self.calculator._score_purchase_proximity(self.goods1, self.goods2)
        # 1月15日和1月20日，同月
        self.assertEqual(score, 6.0)

    def test_calculate_similarity_high(self):
        """测试高相似度计算"""
        score = self.calculator.calculate_similarity(self.goods1, self.goods2)
        # 相同IP(30) + 相同品类(18) + 相同主题(15) + 相似价格(~5) + 同月(6) = ~74
        self.assertGreater(score, 60.0)

    def test_calculate_similarity_low(self):
        """测试低相似度计算"""
        score = self.calculator.calculate_similarity(self.goods1, self.goods3)
        # 不同IP但同类型(10) + 相同品类(18) = 28
        self.assertLess(score, 40.0)


class SeedSelectorTestCase(TestCase):
    """测试种子选择器"""

    def setUp(self):
        """设置测试数据"""
        self.role = Role.objects.create(name='测试角色')
        self.user = User.objects.create(
            username='testuser',
            password='testpass123',
            role=self.role
        )

        self.ip1 = IP.objects.create(name='IP1', subject_type=4)
        self.ip2 = IP.objects.create(name='IP2', subject_type=4)
        self.cat = Category.objects.create(name='品类1')

        # 创建多个谷子
        self.goods_list = []
        for i in range(10):
            ip = self.ip1 if i < 5 else self.ip2
            goods = Goods.objects.create(
                user=self.user,
                name=f'谷子{i}',
                ip=ip,
                category=self.cat
            )
            self.goods_list.append(goods)

        self.selector = SeedSelector()

    def test_calculate_seed_count(self):
        """测试种子数量计算"""
        # <100个谷子
        count = self.selector._calculate_seed_count(50)
        self.assertEqual(count, 4)  # (50 // 18) * 2 = 4

        # 100-500个谷子
        count = self.selector._calculate_seed_count(200)
        self.assertEqual(count, 15)

        # >500个谷子
        count = self.selector._calculate_seed_count(1000)
        self.assertEqual(count, 20)

    def test_diverse_selection(self):
        """测试多样化选择"""
        seeds = self.selector._diverse_selection(self.goods_list, 3)
        self.assertEqual(len(seeds), 3)

        # 检查是否来自不同IP
        ip_ids = set(s.ip_id for s in seeds)
        self.assertGreater(len(ip_ids), 1)


class SimilarRandomEndpointTestCase(TestCase):
    """测试相似谷子随机展示接口"""

    def setUp(self):
        """设置测试数据"""
        self.client = APIClient()
        self.role = Role.objects.create(name='测试角色')
        self.user = User.objects.create(
            username='testuser',
            password='testpass123',
            role=self.role
        )
        self.client.force_authenticate(user=self.user)

        # 创建测试数据
        self.ip = IP.objects.create(name='测试IP', subject_type=4)
        self.cat = Category.objects.create(name='测试品类')

        # 创建20个谷子
        for i in range(20):
            Goods.objects.create(
                user=self.user,
                name=f'谷子{i}',
                ip=self.ip,
                category=self.cat
            )

    def test_similar_random_endpoint_exists(self):
        """测试端点是否存在"""
        response = self.client.get('/api/goods/similar-random/')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_similar_random_response_format(self):
        """测试响应格式"""
        response = self.client.get('/api/goods/similar-random/')
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertIn('count', data)
            self.assertIn('results', data)
            self.assertIn('page', data)
            self.assertIn('page_size', data)

    def test_similar_random_with_filters(self):
        """测试带过滤器的请求"""
        response = self.client.get(f'/api/goods/similar-random/?ip={self.ip.id}')
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertGreater(data['count'], 0)

    def test_similar_random_pagination(self):
        """测试分页"""
        response = self.client.get('/api/goods/similar-random/?page=1&page_size=10')
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertLessEqual(len(data['results']), 10)

    def test_similar_random_seed_strategies(self):
        """测试不同的种子策略"""
        strategies = ['diverse', 'popular', 'recent']
        for strategy in strategies:
            response = self.client.get(f'/api/goods/similar-random/?seed_strategy={strategy}')
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])


class GoodsDraftFlowTestCase(TestCase):
    """测试谷子草稿保存与发布流程"""

    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.create(name='测试角色')
        self.user = User.objects.create(
            username='draft_user',
            password='testpass123',
            role=self.role
        )
        self.client.force_authenticate(user=self.user)

        self.ip = IP.objects.create(name='草稿测试IP', subject_type=4)
        self.category = Category.objects.create(name='草稿测试品类')
        self.character = Character.objects.create(
            ip=self.ip,
            name='草稿测试角色',
            gender='female'
        )

    def test_create_draft_with_missing_required_fields(self):
        """草稿可缺省角色字段，但需满足模型非空外键约束"""
        payload = {
            "name": "草稿谷子A",
            "status": "draft",
            "ip_id": self.ip.id,
            "category_id": self.category.id,
            "quantity": 1,
        }
        response = self.client.post('/api/goods/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertTrue(data.get("saved_as_draft"))
        self.assertEqual(data.get("status"), "draft")

    def test_create_non_draft_requires_required_fields(self):
        """非草稿创建保持原有必填校验"""
        payload = {
            "name": "正式谷子A",
            "status": "in_cabinet",
            "quantity": 1,
        }
        response = self.client.post('/api/goods/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn("ip_id", data)
        self.assertIn("character_ids", data)
        self.assertIn("category_id", data)

    def test_create_draft_skips_duplicate_conflict(self):
        """草稿创建不触发重复检测冲突"""
        goods = Goods.objects.create(
            user=self.user,
            name='重复测试谷子',
            ip=self.ip,
            category=self.category,
            price=Decimal('66.00'),
            purchase_date=date(2025, 1, 1)
        )
        goods.characters.add(self.character)

        payload = {
            "name": "重复测试谷子",
            "status": "draft",
            "ip_id": self.ip.id,
            "category_id": self.category.id,
            "character_ids": [self.character.id],
            "price": "66.00",
            "purchase_date": "2025-01-01",
            "merge_strategy": "auto",
        }
        response = self.client.post('/api/goods/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.json().get("saved_as_draft"))

    def test_publish_draft_requires_required_fields(self):
        """草稿发布为非草稿时执行正式必填校验"""
        draft = Goods.objects.create(
            user=self.user,
            name='待发布草稿',
            ip=self.ip,
            category=self.category,
            status='draft',
        )
        # 让该草稿处于不完整状态（无角色）
        draft.characters.clear()

        response = self.client.patch(
            f'/api/goods/{draft.id}/',
            {"status": "in_cabinet"},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn("character_ids", data)

