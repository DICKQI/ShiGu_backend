"""
BGM API 相关的序列化器
"""
from rest_framework import serializers


class BGMSearchRequestSerializer(serializers.Serializer):
    """BGM搜索IP角色请求序列化器"""
    ip_name = serializers.CharField(
        max_length=200,
        required=True,
        help_text="IP作品名称，例如：崩坏：星穹铁道"
    )
    subject_type = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="作品类型筛选：1=书籍, 2=动画, 3=音乐, 4=游戏, 6=三次元。不传则搜索所有类型"
    )


class BGMCharacterSerializer(serializers.Serializer):
    """BGM角色信息序列化器（用于搜索接口返回）"""
    name = serializers.CharField(help_text="角色名称")
    relation = serializers.CharField(help_text="角色关系，如：主角、配角、客串")
    avatar = serializers.CharField(allow_blank=True, help_text="角色头像URL")


class BGMSearchResponseSerializer(serializers.Serializer):
    """BGM搜索IP角色响应序列化器"""
    ip_name = serializers.CharField(help_text="IP作品名称")
    characters = BGMCharacterSerializer(many=True, help_text="角色列表")


class BGMCreateCharacterRequestSerializer(serializers.Serializer):
    """BGM创建角色请求序列化器"""
    ip_name = serializers.CharField(
        max_length=100,
        required=True,
        help_text="IP作品名称"
    )
    character_name = serializers.CharField(
        max_length=100,
        required=True,
        help_text="角色名称"
    )
    subject_type = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="作品类型：1=书籍, 2=动画, 3=音乐, 4=游戏, 6=三次元/特摄。可选，创建IP时使用"
    )
    avatar = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="角色头像URL。可以是BGM返回的头像URL（如 https://lain.bgm.tv/pic/crt/l/xx/xx/12345.jpg）或其他外部URL。可选"
    )


class BGMCreateCharactersRequestSerializer(serializers.Serializer):
    """BGM批量创建角色请求序列化器"""
    characters = BGMCreateCharacterRequestSerializer(
        many=True,
        required=True,
        help_text="角色列表，每个角色包含ip_name和character_name"
    )


# ==================== 新增：两步式搜索相关序列化器 ====================

class BGMSubjectSerializer(serializers.Serializer):
    """BGM作品信息序列化器"""
    id = serializers.IntegerField(help_text="BGM作品ID")
    name = serializers.CharField(help_text="作品原名")
    name_cn = serializers.CharField(allow_blank=True, help_text="作品中文名")
    type = serializers.IntegerField(help_text="作品类型代码：1=书籍, 2=动画, 3=音乐, 4=游戏, 6=三次元/特摄")
    type_name = serializers.CharField(help_text="作品类型名称")
    image = serializers.CharField(allow_blank=True, help_text="作品封面图URL")


class BGMSearchSubjectsRequestSerializer(serializers.Serializer):
    """搜索IP作品列表请求序列化器"""
    keyword = serializers.CharField(
        max_length=200,
        required=True,
        help_text="搜索关键词，例如：崩坏"
    )
    subject_type = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="作品类型筛选：1=书籍, 2=动画, 3=音乐, 4=游戏, 6=三次元。不传则搜索所有类型"
    )


class BGMSearchSubjectsResponseSerializer(serializers.Serializer):
    """搜索IP作品列表响应序列化器"""
    subjects = BGMSubjectSerializer(many=True, help_text="作品列表")


class BGMGetCharactersBySubjectIdRequestSerializer(serializers.Serializer):
    """根据BGM作品ID获取角色请求序列化器"""
    subject_id = serializers.IntegerField(
        required=True,
        help_text="BGM作品ID"
    )


class BGMGetCharactersBySubjectIdResponseSerializer(serializers.Serializer):
    """根据BGM作品ID获取角色响应序列化器"""
    subject_id = serializers.IntegerField(help_text="BGM作品ID")
    subject_name = serializers.CharField(help_text="作品名称")
    characters = BGMCharacterSerializer(many=True, help_text="角色列表")
