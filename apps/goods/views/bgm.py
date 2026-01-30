"""
BGM API 相关的视图函数
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..bgm_service import search_ip_characters, search_subjects_list, get_subject_info, get_characters
from ..models import Character, IP
from ..serializers import (
    BGMCreateCharactersRequestSerializer,
    BGMSearchRequestSerializer,
    BGMSearchResponseSerializer,
    BGMSearchSubjectsRequestSerializer,
    BGMSearchSubjectsResponseSerializer,
    BGMGetCharactersBySubjectIdRequestSerializer,
    BGMGetCharactersBySubjectIdResponseSerializer,
)


@extend_schema(
    summary="搜索IP作品并获取角色列表",
    description="通过IP名称搜索作品，并返回该作品下的角色列表。",
    request=BGMSearchRequestSerializer,
    responses={200: BGMSearchResponseSerializer}
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


@extend_schema(
    summary="批量创建IP和角色",
    description="只能根据已有角色列表批量创建或更新IP和角色信息。",
    request=BGMCreateCharactersRequestSerializer,
    responses={200: None}  # 响应结构较复杂，暂时省略或后续补充Serializer
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


# ==================== 新增：两步式搜索接口 ====================

@extend_schema(
    summary="搜索IP作品列表（第一步）",
    description="通过关键字搜索相关的IP作品列表。这是两步搜索的第一步。",
    request=BGMSearchSubjectsRequestSerializer,
    responses={200: BGMSearchSubjectsResponseSerializer}
)
@api_view(['POST'])
def bgm_search_subjects(request):
    """
    搜索IP作品列表（第一步）
    
    POST /api/bgm/search-subjects/
    
    请求体:
    {
        "keyword": "崩坏",
        "subject_type": 4  // 可选，作品类型：1=书籍, 2=动画, 3=音乐, 4=游戏, 6=三次元
    }
    
    响应:
    {
        "subjects": [
            {
                "id": 12345,
                "name": "崩坏：星穹铁道",
                "name_cn": "崩坏：星穹铁道",
                "type": 4,
                "type_name": "游戏",
                "image": "https://..."
            },
            ...
        ]
    }
    """
    serializer = BGMSearchSubjectsRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    keyword = serializer.validated_data['keyword']
    subject_type = serializer.validated_data.get('subject_type')
    
    try:
        subjects = search_subjects_list(keyword, subject_type)
        
        response_data = {
            "subjects": subjects
        }
        
        response_serializer = BGMSearchSubjectsResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"detail": f"搜索失败: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="根据BGM作品ID获取角色列表（第二步）",
    description="根据选定的作品ID，获取该作品下的角色信息。这是两步搜索的第二步。",
    request=BGMGetCharactersBySubjectIdRequestSerializer,
    responses={200: BGMGetCharactersBySubjectIdResponseSerializer}
)
@api_view(['POST'])
def bgm_get_characters_by_subject_id(request):
    """
    根据BGM作品ID获取角色列表（第二步）
    
    POST /api/bgm/get-characters-by-id/
    
    请求体:
    {
        "subject_id": 12345
    }
    
    响应:
    {
        "subject_id": 12345,
        "subject_name": "崩坏：星穹铁道",
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
    serializer = BGMGetCharactersBySubjectIdRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    subject_id = serializer.validated_data['subject_id']
    
    try:
        # 获取作品信息
        subject_info = get_subject_info(subject_id)
        if not subject_info:
            return Response(
                {"detail": f"未找到ID为 {subject_id} 的作品"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 获取角色列表
        characters = get_characters(subject_id)
        
        response_data = {
            "subject_id": subject_id,
            "subject_name": subject_info.get("display_name", ""),
            "characters": characters
        }
        
        response_serializer = BGMGetCharactersBySubjectIdResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"detail": f"获取角色失败: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
