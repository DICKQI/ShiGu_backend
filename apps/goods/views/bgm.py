"""
BGM API 相关的视图函数
"""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..bgm_service import search_ip_characters
from ..models import Character, IP
from ..serializers import (
    BGMCreateCharactersRequestSerializer,
    BGMSearchRequestSerializer,
    BGMSearchResponseSerializer,
)


@api_view(['POST'])
def bgm_search_characters(request):
    """
    搜索IP作品并获取角色列表
    
    POST /api/bgm/search-characters/
    
    请求体:
    {
        "ip_name": "崩坏：星穹铁道",
        "subject_type": 4  // 可选，作品类型：1=书籍, 2=动画, 3=音乐, 4=游戏, 6=三次元
    }
    
    响应:
    {
        "ip_name": "崩坏：星穹铁道",
        "characters": [
            {
                "name": "流萤",
                "relation": "主角",
                "avatar": "https://..."
            },
            ...
        ]
    }
    """
    serializer = BGMSearchRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    ip_name = serializer.validated_data['ip_name']
    subject_type = serializer.validated_data.get('subject_type')
    
    try:
        display_name, characters = search_ip_characters(ip_name, subject_type)
        
        if display_name is None:
            return Response(
                {"detail": f"未找到与 '{ip_name}' 相关的作品"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        response_data = {
            "ip_name": display_name,
            "characters": characters
        }
        
        response_serializer = BGMSearchResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"detail": f"搜索失败: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def bgm_create_characters(request):
    """
    根据角色列表创建IP和角色到数据库
    
    POST /api/bgm/create-characters/
    
    请求体:
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
    
    响应:
    {
        "created": 2,
        "skipped": 0,
        "details": [
            {
                "ip_name": "崩坏：星穹铁道",
                "character_name": "流萤",
                "status": "created",
                "ip_id": 1,
                "character_id": 1
            },
            ...
        ]
    }
    """
    serializer = BGMCreateCharactersRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    characters_data = serializer.validated_data['characters']
    
    created_count = 0
    skipped_count = 0
    details = []
    
    for char_data in characters_data:
        ip_name = char_data['ip_name']
        character_name = char_data['character_name']
        subject_type = char_data.get('subject_type')  # 可选字段
        avatar = char_data.get('avatar')  # 可选字段，头像URL
        
        try:
            # 获取或创建IP
            # 如果提供了 subject_type，在创建新 IP 时使用它
            ip_obj, ip_created = IP.objects.get_or_create(
                name=ip_name,
                defaults={'subject_type': subject_type} if subject_type else {}
            )
            # 如果 IP 已存在但 subject_type 为空，且提供了 subject_type，则更新它
            if not ip_created and ip_obj.subject_type is None and subject_type:
                ip_obj.subject_type = subject_type
                ip_obj.save(update_fields=['subject_type'])
            
            # 获取或创建角色（使用unique_together约束避免重复）
            character_obj, char_created = Character.objects.get_or_create(
                ip=ip_obj,
                name=character_name,
                defaults={'avatar': avatar.strip() if avatar and avatar.strip() else None} if avatar else {}
            )
            
            # 如果角色已存在，但提供了头像URL且角色当前没有头像，则更新头像
            if not char_created and avatar and avatar.strip():
                if not character_obj.avatar:
                    character_obj.avatar = avatar.strip()
                    character_obj.save(update_fields=['avatar'])
            
            if char_created:
                created_count += 1
                status_msg = "created"
            else:
                skipped_count += 1
                status_msg = "already_exists"
            
            details.append({
                "ip_name": ip_name,
                "character_name": character_name,
                "status": status_msg,
                "ip_id": ip_obj.id,
                "character_id": character_obj.id
            })
            
        except Exception as e:
            details.append({
                "ip_name": ip_name,
                "character_name": character_name,
                "status": "error",
                "error": str(e)
            })
    
    return Response({
        "created": created_count,
        "skipped": skipped_count,
        "details": details
    }, status=status.HTTP_200_OK)
