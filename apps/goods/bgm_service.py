"""
BGM API 服务模块
提供搜索IP作品和获取角色列表的核心功能
"""
import html
import urllib.parse

import requests

# --- 配置部分 ---
# 请在这里填入你的 Access Token
ACCESS_TOKEN = "4H4xs6oRhS6AJ6p8WNWZxEJvTEalqPlH3OZMGR5P"
# 指定的 User-Agent
USER_AGENT = "DSCWWW/ShiGu(https://github.com/DICKQI/ShiGu_backend)"

# API 基础 URL
API_HOST = "https://api.bgm.tv"


def get_headers():
    """
    构造请求头，包含 User-Agent 和 Authorization
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    if ACCESS_TOKEN and "你的个人令牌" not in ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
    return headers


def search_subject(keyword):
    """
    搜索条目，返回第一个匹配结果的 ID 和 名称。
    使用 Legacy Search API 进行模糊匹配。
    
    Args:
        keyword: 搜索关键词（IP名称）
    
    Returns:
        tuple: (subject_id, display_name) 或 (None, None) 如果未找到
    """
    encoded_keyword = urllib.parse.quote(keyword)
    # 搜索接口
    url = f"{API_HOST}/search/subject/{encoded_keyword}?responseGroup=small"
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "list" in data and data["list"]:
            first_result = data["list"][0]
            subject_id = first_result.get("id")
            name = first_result.get("name")
            name_cn = first_result.get("name_cn")
            
            # 优先显示中文名，并解码HTML实体
            display_name = name_cn if name_cn else name
            if display_name:
                display_name = html.unescape(display_name)
            if name:
                name = html.unescape(name)
            
            return subject_id, display_name
        else:
            return None, None

    except requests.exceptions.RequestException as e:
        raise Exception(f"搜索请求失败: {str(e)}")


def get_characters(subject_id):
    """
    获取指定条目 ID 下的所有角色名。
    针对附件提供的 JSON 结构进行解析。
    
    Args:
        subject_id: BGM条目ID
    
    Returns:
        list: 角色列表，每个角色包含 name, relation, avatar 字段
    """
    url = f"{API_HOST}/v0/subjects/{subject_id}/characters"
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        data = response.json()
        
        characters = []
        
        if isinstance(data, list):
            for item in data:
                # 根据附件 JSON，name 和 relation 直接在 item 根节点
                name = item.get("name")
                relation = item.get("relation", "未知")
                
                # 提取头像URL (grid尺寸)
                images = item.get("images", {})
                avatar_url = ""
                if isinstance(images, dict):
                    avatar_url = images.get("grid", "")
                
                # 只有当名字存在时才添加，并解码HTML实体（如 &amp; -> &）
                if name:
                    name = html.unescape(name)  # 解码HTML实体编码
                    characters.append({
                        "name": name,
                        "relation": relation,
                        "avatar": avatar_url
                    })
            
            # --- 排序逻辑 ---
            # 定义关系优先级：主角 > 配角 > 客串 > 其他
            priority = {"主角": 1, "配角": 2, "客串": 3}
            
            # 使用 lambda 进行排序，未知的关系放到最后(99)
            characters.sort(key=lambda x: priority.get(x["relation"], 99))
            
            return characters
        else:
            return []

    except requests.exceptions.RequestException as e:
        raise Exception(f"获取角色请求失败: {str(e)}")


def search_ip_characters(ip_name):
    """
    搜索IP作品并获取其角色列表的便捷方法
    
    Args:
        ip_name: IP作品名称
    
    Returns:
        tuple: (ip_display_name, characters_list) 或 (None, []) 如果未找到
    """
    subject_id, display_name = search_subject(ip_name)
    if subject_id and display_name:
        characters = get_characters(subject_id)
        return display_name, characters
    return None, []

