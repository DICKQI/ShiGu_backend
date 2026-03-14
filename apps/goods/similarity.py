"""
谷子相似度计算模块

提供基于多维度加权评分的相似度算法，用于智能推荐和分组展示。
"""

import random
from collections import defaultdict
from datetime import timedelta


class GoodsSimilarityCalculator:
    """
    计算谷子之间的相似度分数（0-100分）

    基于6个维度的加权评分：
    - IP匹配（30分）
    - 角色重叠（25分）
    - 品类层级（20分）
    - 主题匹配（10分）
    - 价格区间（8分）
    - 入手日期接近度（7分）
    """

    WEIGHTS = {
        'ip_match': 30,
        'character_overlap': 25,
        'category_hierarchy': 20,
        'theme_match': 10,
        'price_range': 8,
        'purchase_proximity': 7,
    }

    def __init__(self, category_tree_cache=None):
        """
        初始化相似度计算器

        Args:
            category_tree_cache: 品类树缓存字典，用于优化层级查询
        """
        self.category_tree_cache = category_tree_cache or {}

    def calculate_similarity(self, goods_a, goods_b):
        """
        计算两个谷子之间的总相似度分数

        Args:
            goods_a: 谷子对象A
            goods_b: 谷子对象B

        Returns:
            float: 相似度分数（0-100）
        """
        score = 0.0
        score += self._score_ip_match(goods_a, goods_b)
        score += self._score_character_overlap(goods_a, goods_b)
        score += self._score_category_hierarchy(goods_a, goods_b)
        score += self._score_theme_match(goods_a, goods_b)
        score += self._score_price_range(goods_a, goods_b)
        score += self._score_purchase_proximity(goods_a, goods_b)
        return score

    def _score_ip_match(self, a, b):
        """
        IP相似度评分

        - 相同IP：30分
        - 相同作品类型：10分
        - 不同：0分
        """
        if a.ip_id == b.ip_id:
            return self.WEIGHTS['ip_match']

        # 检查作品类型是否相同
        if (hasattr(a.ip, 'subject_type') and hasattr(b.ip, 'subject_type') and
            a.ip.subject_type and b.ip.subject_type and
            a.ip.subject_type == b.ip.subject_type):
            return self.WEIGHTS['ip_match'] * 0.33

        return 0.0

    def _score_character_overlap(self, a, b):
        """
        角色重叠度评分

        公式：(共享角色数 / 总角色数) * 25
        """
        chars_a = set(c.id for c in a.characters.all())
        chars_b = set(c.id for c in b.characters.all())

        if not chars_a and not chars_b:
            return 0.0

        shared = len(chars_a & chars_b)
        total_unique = len(chars_a | chars_b)

        if total_unique == 0:
            return 0.0

        return (shared / total_unique) * self.WEIGHTS['character_overlap']

    def _score_category_hierarchy(self, a, b):
        """
        品类层级相似度评分

        - 相同叶子品类：20分
        - 相同父级：12分
        - 相同祖父级：6分
        - 相同根品类：3分
        - 不同根：0分
        """
        if a.category_id == b.category_id:
            return self.WEIGHTS['category_hierarchy']

        # 获取祖先路径
        ancestors_a = self._get_category_ancestors(a.category)
        ancestors_b = self._get_category_ancestors(b.category)

        # 查找共同祖先层级
        for level, (anc_a, anc_b) in enumerate(zip(reversed(ancestors_a), reversed(ancestors_b))):
            if anc_a == anc_b:
                # 在第N层找到共同祖先
                if level == 1:  # 相同父级
                    return self.WEIGHTS['category_hierarchy'] * 0.6
                elif level == 2:  # 相同祖父级
                    return self.WEIGHTS['category_hierarchy'] * 0.3
                elif level >= 3:  # 相同根品类
                    return self.WEIGHTS['category_hierarchy'] * 0.15

        return 0.0

    def _score_theme_match(self, a, b):
        """
        主题匹配评分

        - 相同主题：10分
        - 都有主题但不同：2分
        - 一个或两个都没有主题：0分
        """
        if a.theme_id and b.theme_id:
            if a.theme_id == b.theme_id:
                return self.WEIGHTS['theme_match']
            else:
                return self.WEIGHTS['theme_match'] * 0.2
        return 0.0

    def _score_price_range(self, a, b):
        """
        价格区间相似度评分

        - 都没有价格：4分（中性相似）
        - 一个有价格一个没有：0分
        - 都有价格：
          - 差异≤10%：8分
          - 差异≤25%：5分
          - 差异≤50%：3分
          - 差异≤100%：1分
          - 差异>100%：0分
        """
        if a.price is None and b.price is None:
            return self.WEIGHTS['price_range'] * 0.5

        if a.price is None or b.price is None:
            return 0.0

        # 计算百分比差异
        avg_price = (float(a.price) + float(b.price)) / 2
        diff_pct = abs(float(a.price) - float(b.price)) / avg_price if avg_price > 0 else 0

        if diff_pct <= 0.1:
            return self.WEIGHTS['price_range']
        elif diff_pct <= 0.25:
            return self.WEIGHTS['price_range'] * 0.625
        elif diff_pct <= 0.5:
            return self.WEIGHTS['price_range'] * 0.375
        elif diff_pct <= 1.0:
            return self.WEIGHTS['price_range'] * 0.125

        return 0.0

    def _score_purchase_proximity(self, a, b):
        """
        入手日期接近度评分

        - 都没有日期：3分（中性）
        - 一个有日期一个没有：0分
        - 都有日期：
          - 同月：7分
          - 3个月内：5分
          - 6个月内：3分
          - 1年内：1分
          - 超过1年：0分
        """
        if a.purchase_date is None and b.purchase_date is None:
            return self.WEIGHTS['purchase_proximity'] * 0.43

        if a.purchase_date is None or b.purchase_date is None:
            return 0.0

        diff_days = abs((a.purchase_date - b.purchase_date).days)

        if diff_days <= 30:  # 同月
            return self.WEIGHTS['purchase_proximity']
        elif diff_days <= 90:  # 3个月内
            return self.WEIGHTS['purchase_proximity'] * 0.71
        elif diff_days <= 180:  # 6个月内
            return self.WEIGHTS['purchase_proximity'] * 0.43
        elif diff_days <= 365:  # 1年内
            return self.WEIGHTS['purchase_proximity'] * 0.14

        return 0.0

    def _get_category_ancestors(self, category):
        """
        获取品类的祖先ID列表（从根到当前）

        Args:
            category: 品类对象

        Returns:
            list: 祖先ID列表，从根到当前
        """
        if category.id in self.category_tree_cache:
            return self.category_tree_cache[category.id]

        ancestors = []
        current = category
        while current:
            ancestors.append(current.id)
            current = current.parent

        ancestors.reverse()  # 根在前
        self.category_tree_cache[category.id] = ancestors
        return ancestors


class SeedSelector:
    """
    选择多样化的种子谷子用于分组

    支持三种策略：
    - diverse: 多轮选择确保IP和品类多样性（默认）
    - popular: 从热门IP中选择
    - recent: 从最近添加的谷子中选择
    """

    def select_seeds(self, goods_list, strategy='diverse', count=None):
        """
        根据策略选择N个种子谷子

        Args:
            goods_list: 谷子列表
            strategy: 选择策略（'diverse', 'popular', 'recent'）
            count: 种子数量，None则自动计算

        Returns:
            list: 种子谷子列表
        """
        if count is None:
            count = self._calculate_seed_count(len(goods_list))

        if strategy == 'diverse':
            return self._diverse_selection(goods_list, count)
        elif strategy == 'popular':
            return self._popular_selection(goods_list, count)
        elif strategy == 'recent':
            return self._recent_selection(goods_list, count)

        return self._diverse_selection(goods_list, count)

    def _calculate_seed_count(self, total_goods):
        """
        计算最优种子数量

        Args:
            total_goods: 谷子总数

        Returns:
            int: 种子数量
        """
        if total_goods < 100:
            return max(2, (total_goods // 18) * 2)
        elif total_goods <= 500:
            return 15
        else:
            return 20

    def _diverse_selection(self, goods_list, count):
        """
        多轮多样化种子选择

        第一轮：从每个不同的IP中选择1个
        第二轮：从热门品类中补充
        第三轮：随机填充

        Args:
            goods_list: 谷子列表
            count: 目标种子数量

        Returns:
            list: 种子谷子列表
        """
        seeds = []
        used_ids = set()

        # 第一轮：每个IP选一个
        ip_groups = defaultdict(list)
        for good in goods_list:
            ip_groups[good.ip_id].append(good)

        for ip_id, ip_goods in ip_groups.items():
            if len(seeds) >= count:
                break
            seed = random.choice(ip_goods)
            seeds.append(seed)
            used_ids.add(seed.id)

        # 第二轮：从热门品类中补充
        if len(seeds) < count:
            category_groups = defaultdict(list)
            for good in goods_list:
                if good.id not in used_ids:
                    category_groups[good.category_id].append(good)

            # 按品类热度排序
            sorted_categories = sorted(
                category_groups.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )

            for cat_id, cat_goods in sorted_categories:
                if len(seeds) >= count:
                    break
                seed = random.choice(cat_goods)
                seeds.append(seed)
                used_ids.add(seed.id)

        # 第三轮：随机填充
        if len(seeds) < count:
            remaining = [g for g in goods_list if g.id not in used_ids]
            random.shuffle(remaining)
            for good in remaining:
                if len(seeds) >= count:
                    break
                seeds.append(good)

        return seeds

    def _popular_selection(self, goods_list, count):
        """
        从热门IP中选择种子

        Args:
            goods_list: 谷子列表
            count: 目标种子数量

        Returns:
            list: 种子谷子列表
        """
        ip_groups = defaultdict(list)
        for good in goods_list:
            ip_groups[good.ip_id].append(good)

        # 按IP热度排序
        sorted_ips = sorted(
            ip_groups.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )

        seeds = []
        for ip_id, ip_goods in sorted_ips:
            if len(seeds) >= count:
                break
            seed = random.choice(ip_goods)
            seeds.append(seed)

        return seeds

    def _recent_selection(self, goods_list, count):
        """
        从最近添加的谷子中选择种子

        Args:
            goods_list: 谷子列表
            count: 目标种子数量

        Returns:
            list: 种子谷子列表
        """
        sorted_goods = sorted(goods_list, key=lambda g: g.created_at, reverse=True)

        seeds = []
        used_ips = set()

        # 尝试从最近的谷子中获取不同IP的种子
        for good in sorted_goods:
            if len(seeds) >= count:
                break
            if good.ip_id not in used_ips:
                seeds.append(good)
                used_ips.add(good.ip_id)

        # 如果还不够，继续添加最近的谷子
        if len(seeds) < count:
            for good in sorted_goods:
                if len(seeds) >= count:
                    break
                if good not in seeds:
                    seeds.append(good)

        return seeds


class SimilarityGroupBuilder:
    """
    构建相似谷子分组

    围绕种子谷子构建分组，并强制执行多样性规则
    """

    def __init__(self, calculator):
        """
        初始化分组构建器

        Args:
            calculator: GoodsSimilarityCalculator实例
        """
        self.calculator = calculator

    def build_groups(self, seeds, all_goods, group_size=5, min_similarity=40):
        """
        围绕种子谷子构建分组

        Args:
            seeds: 种子谷子列表
            all_goods: 所有谷子列表
            group_size: 每组大小（包括种子）
            min_similarity: 最小相似度阈值

        Returns:
            list[list[Goods]]: 分组列表，每个分组是一个谷子列表
        """
        groups = []
        used_ids = set()

        for seed in seeds:
            if seed.id in used_ids:
                continue

            group = [seed]
            used_ids.add(seed.id)

            # 计算与剩余谷子的相似度
            candidates = []
            for good in all_goods:
                if good.id in used_ids:
                    continue
                score = self.calculator.calculate_similarity(seed, good)
                if score >= min_similarity:
                    candidates.append((score, good))

            # 按分数排序并取前K个
            candidates.sort(reverse=True, key=lambda x: x[0])
            for score, good in candidates[:group_size-1]:
                group.append(good)
                used_ids.add(good.id)

            groups.append(group)

        # 添加剩余未分组的谷子作为单独的"组"
        remaining = [g for g in all_goods if g.id not in used_ids]
        random.shuffle(remaining)
        for good in remaining:
            groups.append([good])

        return groups

    def interleave_groups(self, groups):
        """
        交错排列分组以实现多样性，同时保持组内聚集

        策略：
        1. 按IP对分组进行分类
        2. 轮流从不同IP中取出分组
        3. 同一IP的分组之间插入其他IP的分组

        Args:
            groups: 分组列表 list[list[Goods]]

        Returns:
            list[Goods]: 扁平化的谷子列表
        """
        if len(groups) <= 1:
            return [g for group in groups for g in group]

        # 按IP分类分组
        ip_groups = defaultdict(list)
        for group in groups:
            if group:
                # 使用组内第一个谷子的IP作为分组标识
                ip_id = group[0].ip_id
                ip_groups[ip_id].append(group)

        # 轮流从不同IP中取出分组
        result = []
        ip_ids = list(ip_groups.keys())
        random.shuffle(ip_ids)  # 随机化IP顺序

        while ip_groups:
            for ip_id in ip_ids[:]:
                if ip_id not in ip_groups:
                    continue

                # 从当前IP取出一个分组
                group = ip_groups[ip_id].pop(0)
                result.extend(group)

                # 如果该IP没有更多分组，移除
                if not ip_groups[ip_id]:
                    del ip_groups[ip_id]
                    ip_ids.remove(ip_id)

        return result
