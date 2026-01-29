"""
BGM API 服务模块
提供搜索IP作品和获取角色列表的核心功能
支持按作品类型（动画、游戏、书籍等）筛选
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

# --- 作品类型常量 (Subject Type) ---
SUBJECT_TYPE_BOOK = 1   # 书籍
SUBJECT_TYPE_ANIME = 2  # 动画
SUBJECT_TYPE_MUSIC = 3  # 音乐
SUBJECT_TYPE_GAME = 4   # 游戏
SUBJECT_TYPE_REAL = 6   # 三次元/特摄

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


def search_subject(keyword, subject_type=None):
    """
    搜索条目，返回第一个匹配结果的 ID 和 名称。
    使用 Legacy Search API 进行模糊匹配。
    
    Args:
        keyword (str): 搜索关键词（IP名称）
        subject_type (int, optional): 作品类型 (1:书籍, 2:动画, 3:音乐, 4:游戏, 6:三次元). 默认为 None (搜索所有).
    
    Returns:
        tuple: (subject_id, display_name) 或 (None, None) 如果未找到
    """
    # URL 路径中的关键词仍需手动编码
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"{API_HOST}/search/subject/{encoded_keyword}"
    
    # 构造查询参数
    params = {
        "responseGroup": "small"
    }
    # 如果指定了类型，则添加到参数中
    if subject_type:
        params["type"] = subject_type
    
    try:
        # requests 会自动处理 params 的拼接
        response = requests.get(url, headers=get_headers(), params=params, timeout=10)
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


def search_subjects_list(keyword, subject_type=None):
    """
    搜索条目，返回所有匹配结果的列表。
    使用 Legacy Search API 进行模糊匹配。
    
    Args:
        keyword (str): 搜索关键词（IP名称）
        subject_type (int, optional): 作品类型 (1:书籍, 2:动画, 3:音乐, 4:游戏, 6:三次元). 默认为 None (搜索所有).
    
    Returns:
        list: 作品列表，每个作品包含 id, name, name_cn, type, type_name, image 等字段
    """
    # 作品类型映射
    TYPE_NAMES = {
        1: "书籍",
        2: "动画",
        3: "音乐",
        4: "游戏",
        6: "三次元/特摄"
    }
    
    # URL 路径中的关键词需要手动编码
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"{API_HOST}/search/subject/{encoded_keyword}"
    
    # 构造查询参数
    params = {
        "responseGroup": "small"
    }
    # 如果指定了类型，则添加到参数中
    if subject_type:
        params["type"] = subject_type
    
    try:
        # requests 会自动处理 params 的拼接
        response = requests.get(url, headers=get_headers(), params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        subjects = []
        if "list" in data and data["list"]:
            for item in data["list"]:
                subject_id = item.get("id")
                name = item.get("name", "")
                name_cn = item.get("name_cn", "")
                subject_type_code = item.get("type")
                
                # 解码HTML实体
                if name:
                    name = html.unescape(name)
                if name_cn:
                    name_cn = html.unescape(name_cn)
                
                # 获取封面图
                images = item.get("images", {})
                image_url = ""
                if isinstance(images, dict):
                    # 优先使用 large，其次 common，最后 medium
                    image_url = images.get("large") or images.get("common") or images.get("medium", "")
                
                subjects.append({
                    "id": subject_id,
                    "name": name,
                    "name_cn": name_cn,
                    "type": subject_type_code,
                    "type_name": TYPE_NAMES.get(subject_type_code, "未知"),
                    "image": image_url
                })
        
        return subjects

    except requests.exceptions.RequestException as e:
        raise Exception(f"搜索请求失败: {str(e)}")


def get_subject_info(subject_id):
    """
    根据BGM作品ID获取作品基本信息
    
    Args:
        subject_id (int): BGM作品ID
    
    Returns:
        dict: 作品信息，包含 id, name, name_cn 等字段，如果未找到返回 None
    """
    url = f"{API_HOST}/v0/subjects/{subject_id}"
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        data = response.json()
        
        name = data.get("name", "")
        name_cn = data.get("name_cn", "")
        
        # 解码HTML实体
        if name:
            name = html.unescape(name)
        if name_cn:
            name_cn = html.unescape(name_cn)
        
        # 优先返回中文名
        display_name = name_cn if name_cn else name
        
        return {
            "id": subject_id,
            "name": name,
            "name_cn": name_cn,
            "display_name": display_name
        }

    except requests.exceptions.RequestException as e:
        raise Exception(f"获取作品信息失败: {str(e)}")


def search_ip_characters(ip_name, subject_type=None):
    """
    搜索IP作品并获取其角色列表的便捷方法
    
    Args:
        ip_name (str): IP作品名称
        subject_type (int, optional): 作品类型 (1:书籍, 2:动画, 3:音乐, 4:游戏, 6:三次元). 默认为 None.
    
    Returns:
        tuple: (ip_display_name, characters_list) 或 (None, []) 如果未找到
    """
    subject_id, display_name = search_subject(ip_name, subject_type)
    if subject_id and display_name:
        # print(f"找到作品: {display_name} (ID: {subject_id})") # 调试用
        characters = get_characters(subject_id)
        return display_name, characters
    return None, []

