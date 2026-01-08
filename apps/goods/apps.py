from django.apps import AppConfig


class GoodsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.goods'

    def ready(self):
        # 导入信号，确保模型文件清理逻辑生效
        import apps.goods.signals  # noqa: F401
        
        # 初始化品类数据
        self._init_categories()
    
    def _init_categories(self):
        """系统启动时自动创建默认品类"""
        from apps.goods.models import Category
        
        default_categories = [
            "吧唧",
            "异形吧唧",
            "金属徽章",
            "亚克力立牌",
            "摇摇乐",
            "流沙摆件",
            "色纸",
            "亚克力挂件",
            "拍立得",
            "镭射票",
            "透卡",
            "小卡",
            "明信片",
            "棉花娃娃",
            "团子",
            "痛包",
            "印章",
            "胶带",
        ]
        
        for category_name in default_categories:
            Category.objects.get_or_create(name=category_name)