import requests
import json
import os
import base64
import hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from functools import lru_cache
import time

# 加载环境变量
load_dotenv()

# 全局会话对象，用于连接复用
notion_session = requests.Session()
github_session = requests.Session()

# 线程锁
print_lock = threading.Lock()

def safe_print(*args, **kwargs):
    """线程安全的打印函数"""
    with print_lock:
        print(*args, **kwargs)

NOTION_API_KEY = os.getenv('NOTION_API_KEY')
# 支持多个数据库ID（优先使用NOTION_DATABASE_IDS）
NOTION_DATABASE_IDS = os.getenv('NOTION_DATABASE_IDS')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')  # 兼容旧版本
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')
GITHUB_OWNER = os.getenv('GITHUB_OWNER')
GITHUB_PATH = os.getenv('GITHUB_PATH', 'notes')

# 同步模式配置
SYNC_MODE = os.getenv('SYNC_MODE', 'all')  # 'databases', 'pages', 'all'
BATCH_COMMIT = os.getenv('BATCH_COMMIT', 'true').lower() == 'true'  # 是否批量提交
SKIP_COMMIT = os.getenv('SKIP_COMMIT', 'false').lower() == 'true'  # 是否跳过提交

# 文件夹分类配置
CATEGORY_PROPERTIES = os.getenv('CATEGORY_PROPERTIES', 'Status,Category,Type,状态,分类,类型,Stage,阶段').split(',')
ENABLE_CATEGORIZATION = os.getenv('ENABLE_CATEGORIZATION', 'true').lower() == 'true'  # 是否启用分类

# 数据库表格显示配置
DATABASE_TABLE_PROPERTIES = os.getenv('DATABASE_TABLE_PROPERTIES', '').strip()  # 用户自定义表格属性

# 存储待提交的文件
pending_files = []

# 文件位置映射表文件
MAPPING_FILE = 'file_mapping.json'

# 设置会话Headers
def setup_sessions():
    """设置全局会话的默认headers"""
    notion_session.headers.update({
        'Authorization': f'Bearer {NOTION_API_KEY}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    })
    
    github_session.headers.update({
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    })

# 缓存装饰器
@lru_cache(maxsize=1000)
def cached_get_page_info(page_id):
    """缓存的页面信息获取"""
    return get_page_info_direct(page_id)

def get_page_info_direct(page_id):
    """直接获取页面信息（不使用缓存）"""
    url = f'https://api.notion.com/v1/pages/{page_id}'
    try:
        response = notion_session.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        safe_print(f"获取页面 {page_id} 信息时出错: {e}")
        return None

def process_page_parallel(page_data, database_title, parent_title, file_mapping):
    """并行处理单个页面"""
    try:
        page_id = page_data['id']
        
        # 获取页面属性
        page_properties = get_page_properties(page_data)
        
        # 生成文件名
        title = get_page_title(page_data)
        if not title:
            title = f"页面_{page_id}"
        
        # 生成文件夹路径
        folder_path = generate_folder_path(database_title, page_properties, parent_title)
        
        # 获取页面内容
        content_data = get_page_content(page_id)
        
        # 转换为Markdown
        source_info = f"数据库: {database_title}"
        markdown_content = convert_notion_to_markdown(page_data, content_data, source_info)
        
        # 生成文件名
        filename = clean_filename(title)
        new_file_path = f"{GITHUB_PATH}/{folder_path}/{filename}.md"
        
        # 检查是否需要删除旧位置的文件
        if page_id in file_mapping:
            old_file_path = file_mapping[page_id]
            if old_file_path != new_file_path:
                safe_print(f"🔄 检测到文件位置变更: {page_id}")
                safe_print(f"   旧位置: {old_file_path}")
                safe_print(f"   新位置: {new_file_path}")
                # 删除旧位置的文件
                delete_github_file(old_file_path)
        
        # 更新映射表
        file_mapping[page_id] = new_file_path
        
        return {
            'success': True,
            'page_id': page_id,
            'title': title,
            'folder_path': folder_path,
            'filename': filename,
            'content': markdown_content,
            'new_file_path': new_file_path
        }
    except Exception as e:
        safe_print(f"处理页面 {page_data.get('id', 'unknown')} 时出错: {e}")
        return {'success': False, 'error': str(e)}

def batch_check_github_files(file_paths):
    """批量检查GitHub文件是否存在和内容"""
    results = {}
    
    def check_single_file(file_path):
        try:
            url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{file_path}'
            response = github_session.get(url)
            if response.status_code == 200:
                existing_data = response.json()
                existing_content = base64.b64decode(existing_data['content']).decode('utf-8')
                return file_path, {
                    'sha': existing_data['sha'],
                    'content': existing_content,
                    'exists': True
                }
            else:
                return file_path, {'exists': False}
        except Exception as e:
            return file_path, {'exists': False, 'error': str(e)}
    
    # 并行检查文件
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_path = {executor.submit(check_single_file, path): path for path in file_paths}
        for future in as_completed(future_to_path):
            file_path, result = future.result()
            results[file_path] = result
    
    return results


def load_file_mapping():
    """加载文件位置映射表"""
    try:
        if os.path.exists(MAPPING_FILE):
            with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        safe_print(f"⚠️ 加载文件映射表时出错: {e}")
        return {}


def save_file_mapping(mapping):
    """保存文件位置映射表"""
    try:
        with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
    except Exception as e:
        safe_print(f"⚠️ 保存文件映射表时出错: {e}")


def delete_github_file(file_path):
    """删除GitHub上的文件"""
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }

    url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{file_path}'

    try:
        # 先获取文件信息以获取SHA
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            file_data = response.json()
            sha = file_data['sha']

            # 删除文件
            delete_data = {
                'message': f'🗑️ 清理旧位置文件: {file_path}',
                'sha': sha
            }

            delete_response = requests.delete(url, headers=headers, json=delete_data)
            if delete_response.status_code == 200:
                safe_print(f"🗑️ 已删除旧文件: {file_path}")
                return True
            else:
                safe_print(f"⚠️ 删除文件失败: {file_path} - {delete_response.status_code}")
        else:
            safe_print(f"📝 文件不存在，无需删除: {file_path}")
        
        return False
    except Exception as e:
        safe_print(f"⚠️ 删除文件时出错: {file_path} - {e}")
        return False


def clean_deleted_pages(file_mapping):
    """清理已删除页面对应的GitHub文件"""
    if not file_mapping:
        return

    safe_print(f"\n🧹 检查已删除的页面...")
    
    # 获取当前同步中处理过的页面ID
    current_session_pages = set()
    
    # 从pending_files中提取页面ID（这需要我们存储页面ID信息）
    # 由于当前结构限制，我们先跳过这个功能，在后续版本中改进
    
    # TODO: 在后续版本中添加更完善的清理机制
    # 目前只清理位置变更的文件，已删除页面的清理将在后续版本中实现
    
    safe_print(f"✅ 清理检查完成")


def get_database_ids():
    """获取要同步的数据库ID列表"""
    if NOTION_DATABASE_IDS:
        # 支持多个数据库ID，用逗号分隔
        database_ids = [db_id.strip() for db_id in NOTION_DATABASE_IDS.split(',') if db_id.strip()]
        return database_ids
    elif NOTION_DATABASE_ID:
        # 兼容单个数据库ID
        return [NOTION_DATABASE_ID.strip()]
    else:
        return []


def search_all_pages():
    """搜索所有页面（包括数据库中的页面和独立页面）"""
    headers = {
        'Authorization': f'Bearer {NOTION_API_KEY}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }

    url = 'https://api.notion.com/v1/search'

    all_pages = []
    has_more = True
    start_cursor = None

    while has_more:
        data = {
            'filter': {
                'property': 'object',
                'value': 'page'
            },
            'page_size': 100
        }

        if start_cursor:
            data['start_cursor'] = start_cursor

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()

            all_pages.extend(result.get('results', []))
            has_more = result.get('has_more', False)
            start_cursor = result.get('next_cursor')

        except requests.exceptions.RequestException as e:
            safe_print(f"搜索页面时出错: {e}")
            break

    return all_pages


def get_page_info(page_id):
    """获取页面信息"""
    url = f'https://api.notion.com/v1/pages/{page_id}'

    try:
        response = notion_session.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        safe_print(f"获取页面 {page_id} 信息时出错: {e}")
        return None


def get_database_info(database_id):
    """获取数据库信息（包括名称和父页面关系）"""
    url = f'https://api.notion.com/v1/databases/{database_id}'

    try:
        response = notion_session.get(url)
        response.raise_for_status()
        db_data = response.json()

        # 获取数据库标题
        db_title = "未命名数据库"
        if 'title' in db_data and db_data['title']:
            db_title = db_data['title'][0]['plain_text']

        # 获取父页面信息
        parent_info = db_data.get('parent', {})
        parent_title = None
        
        if parent_info.get('type') == 'page_id':
            parent_page_id = parent_info.get('page_id')
            if parent_page_id:
                parent_page_data = get_page_info(parent_page_id)
                if parent_page_data:
                    parent_title = get_page_title(parent_page_data)

        return {
            'id': database_id,
            'title': db_title,
            'parent_title': parent_title,
            'data': db_data
        }
    except requests.exceptions.RequestException as e:
        safe_print(f"获取数据库 {database_id} 信息时出错: {e}")
        return {
            'id': database_id,
            'title': f"数据库_{database_id[:8]}",
            'parent_title': None,
            'data': None
        }


def clean_folder_name(name):
    """清理文件夹名称，移除不合法字符"""
    # 移除或替换不合法的文件夹字符
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        name = name.replace(char, '_')

    # 移除首尾空格和点
    name = name.strip(' .')

    # 如果名称为空，使用默认名称
    if not name:
        name = "未命名"

    return name


def parse_date_string(date_str):
    """解析日期字符串，支持多种格式"""
    if not date_str:
        return None
    
    # 尝试解析ISO格式日期
    try:
        if 'T' in date_str:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
        else:
            return datetime.fromisoformat(date_str).date()
    except:
        pass
    
    # 尝试解析其他常见格式
    date_formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y年%m月%d日',
        '%m/%d/%Y',
        '%d/%m/%Y'
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue
    
    return None


def get_week_range(date_obj):
    """获取指定日期所在周的日期范围（周日到周六）"""
    if not date_obj:
        return None
    
    # 获取周日（weekday() 返回0-6，0是周一，6是周日）
    # 如果今天是周日(weekday=6)，则today就是周日起始
    # 否则需要回退到上一个周日
    days_since_sunday = (date_obj.weekday() + 1) % 7
    sunday = date_obj - timedelta(days=days_since_sunday)
    # 获取周六
    saturday = sunday + timedelta(days=6)
    
    return (sunday, saturday)


def format_week_range(start_date, end_date):
    """格式化周期范围为文件夹名称"""
    if not start_date or not end_date:
        return None
    
    # 如果在同一个月
    if start_date.month == end_date.month:
        return f"{start_date.year}年{start_date.month}月{start_date.day}日-{end_date.day}日"
    # 如果跨月
    elif start_date.year == end_date.year:
        return f"{start_date.year}年{start_date.month}月{start_date.day}日-{end_date.month}月{end_date.day}日"
    # 如果跨年
    else:
        return f"{start_date.year}年{start_date.month}月{start_date.day}日-{end_date.year}年{end_date.month}月{end_date.day}日"


def generate_date_category(date_value):
    """根据日期值生成分类文件夹名称"""
    if not date_value:
        return None
    
    # 如果是字符串，先解析为日期对象
    if isinstance(date_value, str):
        date_obj = parse_date_string(date_value)
    else:
        date_obj = date_value
    
    if not date_obj:
        return None
    
    # 获取周期范围
    week_range = get_week_range(date_obj)
    if week_range:
        start_date, end_date = week_range
        return format_week_range(start_date, end_date)
    
    return None


def fetch_notion_notes(database_id):
    """获取指定Notion数据库中的笔记"""
    url = f'https://api.notion.com/v1/databases/{database_id}/query'

    try:
        response = notion_session.post(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        safe_print(f"获取数据库 {database_id} 的笔记时出错: {e}")
        return None


def get_page_content(page_id):
    """获取页面的具体内容"""
    url = f'https://api.notion.com/v1/blocks/{page_id}/children'

    try:
        response = notion_session.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        safe_print(f"获取页面内容时出错: {e}")
        return None


def get_page_title(page_data):
    """从页面数据中提取标题"""
    if 'properties' in page_data:
        for prop_name, prop_data in page_data['properties'].items():
            if prop_data['type'] == 'title' and 'title' in prop_data:
                if prop_data['title']:
                    return prop_data['title'][0]['plain_text']
                break

    # 如果没有找到title属性，尝试从其他地方获取
    if 'title' in page_data and page_data['title']:
        return page_data['title'][0]['plain_text'] if isinstance(page_data['title'], list) else str(page_data['title'])

    return ""


def get_page_properties(page_data):
    """从页面数据中提取所有属性"""
    properties = {}
    if 'properties' in page_data:
        for prop_name, prop_data in page_data['properties'].items():
            prop_type = prop_data.get('type', '')
            
            if prop_type == 'select' and 'select' in prop_data and prop_data['select']:
                properties[prop_name] = prop_data['select']['name']
            elif prop_type == 'multi_select' and 'multi_select' in prop_data:
                properties[prop_name] = [item['name'] for item in prop_data['multi_select']]
            elif prop_type == 'status' and 'status' in prop_data and prop_data['status']:
                properties[prop_name] = prop_data['status']['name']
            elif prop_type == 'rich_text' and 'rich_text' in prop_data and prop_data['rich_text']:
                properties[prop_name] = prop_data['rich_text'][0]['plain_text']
            elif prop_type == 'number' and 'number' in prop_data and prop_data['number'] is not None:
                properties[prop_name] = str(prop_data['number'])
            elif prop_type == 'checkbox' and 'checkbox' in prop_data:
                properties[prop_name] = '已完成' if prop_data['checkbox'] else '未完成'
            elif prop_type == 'date' and 'date' in prop_data and prop_data['date']:
                properties[prop_name] = prop_data['date']['start']
            elif prop_type == 'url' and 'url' in prop_data and prop_data['url']:
                properties[prop_name] = prop_data['url']
            elif prop_type == 'title' and 'title' in prop_data and prop_data['title']:
                properties[prop_name] = prop_data['title'][0]['plain_text']
            elif prop_type == 'formula' and 'formula' in prop_data:
                # 获取公式计算结果
                formula_result = prop_data['formula']
                if formula_result.get('type') == 'string' and formula_result.get('string'):
                    properties[prop_name] = formula_result['string']
                elif formula_result.get('type') == 'number' and formula_result.get('number') is not None:
                    properties[prop_name] = str(formula_result['number'])
                elif formula_result.get('type') == 'date' and formula_result.get('date'):
                    properties[prop_name] = formula_result['date']['start']
            elif prop_type == 'rollup' and 'rollup' in prop_data:
                # 获取汇总结果
                rollup_result = prop_data['rollup']
                if rollup_result.get('type') == 'array' and rollup_result.get('array'):
                    # 处理数组类型的汇总结果
                    array_values = []
                    for item in rollup_result['array']:
                        if item.get('type') == 'rich_text' and item.get('rich_text'):
                            array_values.append(item['rich_text'][0]['plain_text'])
                    if array_values:
                        properties[prop_name] = array_values
                elif rollup_result.get('type') == 'number' and rollup_result.get('number') is not None:
                    properties[prop_name] = str(rollup_result['number'])
            elif prop_type == 'created_time':
                properties[prop_name] = prop_data['created_time']
            elif prop_type == 'last_edited_time':
                properties[prop_name] = prop_data['last_edited_time']
    
    return properties


def generate_folder_path(database_title, page_properties, parent_title=None):
    """根据数据库标题、父页面标题和页面属性生成文件夹路径"""
    # 如果有父页面，使用父页面/数据库的结构
    if parent_title:
        base_folder = f"{clean_folder_name(parent_title)}/{clean_folder_name(database_title)}"
    else:
        base_folder = clean_folder_name(database_title)
    
    # 如果禁用分类，直接返回基础文件夹
    if not ENABLE_CATEGORIZATION:
        return base_folder
    
    # 查找分类属性
    category_value = None
    category_prop_name = None
    for prop_name in CATEGORY_PROPERTIES:
        prop_name = prop_name.strip()  # 移除空格
        if prop_name in page_properties:
            category_value = page_properties[prop_name]
            category_prop_name = prop_name
            break
    
    if category_value:
        # 检查是否是日期属性，如果是则进行特殊处理
        date_keywords = ['date', 'time', '日期', '时间', 'full date']
        is_date_prop = category_prop_name and any(date_keyword in category_prop_name.lower() 
                                                 for date_keyword in date_keywords)
        
        if is_date_prop:
            # 尝试生成日期范围分类
            date_category = generate_date_category(category_value)
            if date_category:
                category_folder = clean_folder_name(date_category)
                return f"{base_folder}/{category_folder}"
        
        # 如果不是日期属性或日期解析失败，使用原始值
        category_folder = clean_folder_name(str(category_value))
        return f"{base_folder}/{category_folder}"
    else:
        # 如果没有找到分类属性，使用原来的文件夹
        return base_folder


def convert_notion_to_markdown(page_data, content_data, source_info=""):
    """将Notion页面转换为Markdown格式"""
    title = get_page_title(page_data)

    if not title:
        title = f"页面_{page_data.get('id', 'unknown')}"

    markdown_content = f"# {title}\n\n"

    # 添加来源信息
    if source_info:
        markdown_content += f"**来源**: {source_info}\n\n"

    # 添加创建时间
    created_time = page_data.get('created_time', '')
    if created_time:
        markdown_content += f"**创建时间**: {created_time}\n\n"

    # 添加最后编辑时间
    last_edited_time = page_data.get('last_edited_time', '')
    if last_edited_time:
        markdown_content += f"**最后编辑**: {last_edited_time}\n\n"

    # 添加分割线
    markdown_content += "---\n\n"

    # 转换内容块
    if content_data and 'results' in content_data:
        for block in content_data['results']:
            markdown_content += convert_block_to_markdown(block)

    return markdown_content


def convert_block_to_markdown(block):
    """将单个Notion块转换为Markdown"""
    block_type = block.get('type', '')

    if block_type == 'paragraph' and 'paragraph' in block:
        text = extract_text_from_rich_text(block['paragraph'].get('rich_text', []))
        return f"{text}\n\n"

    elif block_type == 'heading_1' and 'heading_1' in block:
        text = extract_text_from_rich_text(block['heading_1'].get('rich_text', []))
        return f"# {text}\n\n"

    elif block_type == 'heading_2' and 'heading_2' in block:
        text = extract_text_from_rich_text(block['heading_2'].get('rich_text', []))
        return f"## {text}\n\n"

    elif block_type == 'heading_3' and 'heading_3' in block:
        text = extract_text_from_rich_text(block['heading_3'].get('rich_text', []))
        return f"### {text}\n\n"

    elif block_type == 'bulleted_list_item' and 'bulleted_list_item' in block:
        text = extract_text_from_rich_text(block['bulleted_list_item'].get('rich_text', []))
        return f"- {text}\n"

    elif block_type == 'numbered_list_item' and 'numbered_list_item' in block:
        text = extract_text_from_rich_text(block['numbered_list_item'].get('rich_text', []))
        return f"1. {text}\n"

    elif block_type == 'code' and 'code' in block:
        text = extract_text_from_rich_text(block['code'].get('rich_text', []))
        language = block['code'].get('language', '')
        caption = extract_text_from_rich_text(block['code'].get('caption', []))
        
        # 构建代码块
        code_block = f"```{language}\n{text}\n```"
        
        # 如果有标题，添加到代码块下面作为说明
        if caption:
            code_block += f"\n*{caption}*"
        
        return code_block + "\n\n"

    elif block_type == 'quote' and 'quote' in block:
        text = extract_text_from_rich_text(block['quote'].get('rich_text', []))
        return f"> {text}\n\n"

    elif block_type == 'callout' and 'callout' in block:
        text = extract_text_from_rich_text(block['callout'].get('rich_text', []))
        icon = block['callout'].get('icon', {})
        icon_text = ""
        if icon.get('type') == 'emoji':
            icon_text = icon.get('emoji', '') + " "
        return f"**{icon_text}提示**: {text}\n\n"
    
    elif block_type == 'child_database' and 'child_database' in block:
        # 处理嵌入的数据库
        db_title = block['child_database'].get('title', '未命名数据库')
        db_id = block.get('id', '')
        
        # 获取数据库内容并转换为表格
        database_table = convert_database_to_table(db_id, db_title)
        
        return f"### 📋 {db_title}\n\n{database_table}\n\n> **说明**: 此数据库内容已同步到 `{db_title}/` 文件夹，每行数据对应一个独立的markdown文件\n\n"
    
    elif block_type == 'link_to_page' and 'link_to_page' in block:
        # 处理页面链接
        page_info = block['link_to_page']
        if page_info.get('type') == 'page_id':
            page_id = page_info.get('page_id', '')
            return f"🔗 **链接到页面**: `{page_id}`\n\n"

    return ""


def extract_text_from_rich_text(rich_text_array):
    """从富文本数组中提取纯文本"""
    text = ""
    for rich_text in rich_text_array:
        if 'plain_text' in rich_text:
            text += rich_text['plain_text']
    return text


def convert_database_to_table(database_id, database_title):
    """将数据库内容转换为markdown表格"""
    try:
        # 获取数据库数据
        notes_data = fetch_notion_notes(database_id)
        if not notes_data or 'results' not in notes_data:
            return f"*无法获取数据库 {database_title} 的内容*"
        
        pages = notes_data['results']
        if not pages:
            return f"*数据库 {database_title} 暂无数据*"
        
        # 获取数据库信息以了解属性结构
        db_info = get_database_info(database_id)
        if not db_info or not db_info.get('data'):
            return f"*无法获取数据库 {database_title} 的结构信息*"
        
        # 获取属性列表
        properties = db_info['data'].get('properties', {})
        
        # 构建表格头部
        headers = []
        prop_keys = []
        
        # 检查是否有用户自定义的属性配置
        if DATABASE_TABLE_PROPERTIES:
            # 使用用户自定义的属性
            custom_props = [prop.strip() for prop in DATABASE_TABLE_PROPERTIES.split(',') if prop.strip()]
            for prop_name in custom_props:
                if prop_name in properties:
                    # 直接使用用户配置的属性名作为表头
                    headers.append(prop_name)
                    prop_keys.append(prop_name)
        else:
            # 使用默认的智能选择
            important_props = ['开发', '标题', 'Status', 'Category', 'Type', '状态', '分类', '类型', 'Full Date', '环境']
            
            # 先添加标题类型的属性
            title_prop = None
            for prop_name, prop_data in properties.items():
                if prop_data.get('type') == 'title':
                    title_prop = prop_name
                    break
            
            if title_prop:
                headers.append('名称')
                prop_keys.append(title_prop)
            
            # 按重要性添加其他属性
            for prop_name in important_props:
                if prop_name in properties and prop_name != title_prop:
                    headers.append(prop_name)
                    prop_keys.append(prop_name)
            
            # 添加剩余属性（移除列数限制）
            for prop_name, prop_data in properties.items():
                if prop_name not in prop_keys:
                    headers.append(prop_name)
                    prop_keys.append(prop_name)
        
        if not headers:
            return f"*数据库 {database_title} 无可显示的属性*"
        
        # 构建markdown表格
        table_lines = []
        
        # 表格头
        table_lines.append('| ' + ' | '.join(headers) + ' |')
        table_lines.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
        
        # 表格数据行
        for page in reversed(pages):  # 显示所有行
            page_properties = get_page_properties(page)
            row_data = []
            
            for prop_key in prop_keys:
                if prop_key in page_properties:
                    value = page_properties[prop_key]
                    # 处理不同类型的值
                    if isinstance(value, list):
                        cell_value = ', '.join(str(v) for v in value)
                    elif isinstance(value, str):
                        cell_value = value
                    else:
                        cell_value = str(value)
                    
                    # 不限制单元格长度，显示完整内容
                    
                    # 转义markdown特殊字符
                    cell_value = cell_value.replace('|', '\\|').replace('\n', ' ')
                    row_data.append(cell_value)
                else:
                    row_data.append('-')
            
            table_lines.append('| ' + ' | '.join(row_data) + ' |')
        
        return '\n'.join(table_lines)
        
    except Exception as e:
        safe_print(f"⚠️ 转换数据库表格时出错: {e}")
        return f"*转换数据库 {database_title} 为表格时出错*"


def get_file_content_hash(content):
    """计算文件内容的哈希值"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def get_existing_file_info(file_path):
    """获取GitHub上现有文件的信息"""
    url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{file_path}'

    try:
        response = github_session.get(url)
        if response.status_code == 200:
            existing_data = response.json()
            # 解码现有文件内容
            existing_content = base64.b64decode(existing_data['content']).decode('utf-8')
            return {
                'sha': existing_data['sha'],
                'content': existing_content,
                'exists': True
            }
        else:
            return {'exists': False}
    except:
        return {'exists': False}


def should_update_file(new_content, existing_info):
    """判断是否需要更新文件"""
    if not existing_info['exists']:
        return True

    # 比较内容哈希
    new_hash = get_file_content_hash(new_content)
    existing_hash = get_file_content_hash(existing_info['content'])

    return new_hash != existing_hash


def add_file_to_batch(folder_name, filename, content):
    """将文件添加到批量提交列表"""
    file_path = f"{GITHUB_PATH}/{folder_name}/{filename}.md"

    # 检查文件是否需要更新
    existing_info = get_existing_file_info(file_path)

    if should_update_file(content, existing_info):
        file_info = {
            'path': file_path,
            'content': content,
            'folder_name': folder_name,
            'filename': filename,
            'sha': existing_info.get('sha') if existing_info['exists'] else None,
            'is_new': not existing_info['exists']
        }
        pending_files.append(file_info)
        safe_print(f"📝 待更新: {folder_name}/{filename}.md")
        return True
    else:
        return False


def commit_files_batch():
    """批量提交所有待更新的文件 - 单次提交"""
    if not pending_files:
        safe_print("📄 没有文件需要更新")
        return 0

    safe_print(f"\n🚀 开始单次批量提交 {len(pending_files)} 个文件...")

    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # 获取仓库信息和默认分支
    repo_url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}'
    try:
        repo_response = requests.get(repo_url, headers=headers)
        repo_response.raise_for_status()
        default_branch = repo_response.json()['default_branch']
        safe_print(f"🌿 检测到默认分支: {default_branch}")
    except Exception as e:
        safe_print(f"⚠️ 无法获取仓库信息: {e}")
        safe_print(f"🔄 回退到兼容模式...")
        return commit_files_individually()

    try:
        # 1. 获取当前分支的最新commit
        ref_url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/refs/heads/{default_branch}'
        ref_response = requests.get(ref_url, headers=headers)
        ref_response.raise_for_status()
        base_commit_sha = ref_response.json()['object']['sha']
        safe_print(f"📍 当前分支最新commit: {base_commit_sha[:8]}")

        # 2. 获取基础tree
        commit_url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/commits/{base_commit_sha}'
        commit_response = requests.get(commit_url, headers=headers)
        commit_response.raise_for_status()
        base_tree_sha = commit_response.json()['tree']['sha']
        safe_print(f"📁 基础tree: {base_tree_sha[:8]}")

        # 3. 准备tree entries
        tree_entries = []
        new_files = []
        updated_files = []

        for file_info in pending_files:
            # 创建blob
            blob_data = {
                'content': file_info['content'],
                'encoding': 'utf-8'
            }
            
            blob_url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/blobs'
            blob_response = requests.post(blob_url, headers=headers, json=blob_data)
            blob_response.raise_for_status()
            blob_sha = blob_response.json()['sha']

            # 添加到tree entries
            tree_entries.append({
                'path': file_info['path'],
                'mode': '100644',
                'type': 'blob',
                'sha': blob_sha
            })

            if file_info['is_new']:
                new_files.append(file_info)
            else:
                updated_files.append(file_info)

        safe_print(f"📦 创建了 {len(tree_entries)} 个blob对象")

        # 4. 创建新tree
        tree_data = {
            'base_tree': base_tree_sha,
            'tree': tree_entries
        }

        tree_url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/trees'
        tree_response = requests.post(tree_url, headers=headers, json=tree_data)
        tree_response.raise_for_status()
        new_tree_sha = tree_response.json()['sha']
        safe_print(f"�� 创建新tree: {new_tree_sha[:8]}")

        # 5. 生成commit message
        commit_message = f"🔄 Notion同步 - 批量更新 {len(pending_files)} 个文件"

        if new_files:
            commit_message += f"\n\n✨ 新增 {len(new_files)} 个文件:"
            for file_info in new_files:
                commit_message += f"\n  + {file_info['folder_name']}/{file_info['filename']}.md"
        
        if updated_files:
            commit_message += f"\n\n📝 更新 {len(updated_files)} 个文件:"
            for file_info in updated_files:
                commit_message += f"\n  📄 {file_info['folder_name']}/{file_info['filename']}.md"

        # 6. 创建commit
        commit_data = {
            'message': commit_message,
            'tree': new_tree_sha,
            'parents': [base_commit_sha]
        }

        commit_create_url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/commits'
        commit_create_response = requests.post(commit_create_url, headers=headers, json=commit_data)
        commit_create_response.raise_for_status()
        new_commit_sha = commit_create_response.json()['sha']
        safe_print(f"💾 创建新commit: {new_commit_sha[:8]}")

        # 7. 更新分支引用
        ref_update_data = {
            'sha': new_commit_sha
        }

        ref_update_response = requests.patch(ref_url, headers=headers, json=ref_update_data)
        ref_update_response.raise_for_status()
        safe_print(f"🎯 更新分支引用成功")

        safe_print(f"✅ 单次批量提交完成! 成功提交 {len(pending_files)} 个文件到一个commit中")
        return len(pending_files)

    except Exception as e:
        safe_print(f"❌ 单次批量提交失败: {e}")
        safe_print(f"🔄 回退到兼容模式...")
        return commit_files_individually()


def commit_files_individually():
    """单个文件提交（备用方案）"""
    safe_print("🔄 使用兼容模式（每个文件单独提交）...")

    success_count = 0
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }

    for file_info in pending_files:
        url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{file_info["path"]}'

        # 重新获取最新的SHA以避免冲突
        try:
            check_response = requests.get(url, headers=headers)
            if check_response.status_code == 200:
                current_file = check_response.json()
                current_sha = current_file['sha']

                # 检查内容是否真的不同
                current_content = base64.b64decode(current_file['content']).decode('utf-8')
                if get_file_content_hash(current_content) == get_file_content_hash(file_info['content']):
                    continue
            else:
                current_sha = None
        except:
            current_sha = file_info.get('sha')

        encoded_content = base64.b64encode(file_info['content'].encode('utf-8')).decode('utf-8')

        data = {
            'message': f'更新笔记: {file_info["folder_name"]}/{file_info["filename"]}',
            'content': encoded_content
        }

        if current_sha:
            data['sha'] = current_sha

        try:
            response = requests.put(url, headers=headers, json=data)
            response.raise_for_status()
            safe_print(f"✅ 单独提交: {file_info['folder_name']}/{file_info['filename']}.md")
            success_count += 1
        except requests.exceptions.RequestException as e:
            if "409" in str(e):
                safe_print(f"⚠️ 文件冲突，跳过: {file_info['folder_name']}/{file_info['filename']}.md")
            else:
                safe_print(f"❌ 提交失败: {file_info['folder_name']}/{file_info['filename']}.md - {e}")

    return success_count


def clean_filename(filename):
    """清理文件名"""
    # 移除或替换不合法的文件字符
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # 移除首尾空格和点
    filename = filename.strip(' .')

    # 替换空格为下划线
    filename = filename.replace(' ', '_')

    # 如果文件名为空，使用默认名称
    if not filename:
        filename = "未命名页面"

    return filename


def process_database(database_info, db_index, total_dbs, file_mapping, database_page_ids=None):
    """处理单个数据库 - 优化版本"""
    database_id = database_info['id']
    database_title = database_info['title']
    parent_title = database_info.get('parent_title')

    safe_print(f"\n📚 正在处理数据库 {db_index}/{total_dbs}: {database_title}")
    if parent_title:
        safe_print(f"   🔗 父页面: {parent_title}")

    # 获取数据库中的笔记
    notes_data = fetch_notion_notes(database_id)
    if not notes_data:
        safe_print(f"❌ 无法获取数据库 {database_id} 的笔记")
        return 0

    # 处理每个页面
    pages = notes_data.get('results', [])
    safe_print(f"📄 找到 {len(pages)} 个页面，开始并行处理...")

    # 收集页面ID用于独立页面去重
    if database_page_ids is not None:
        for page in pages:
            database_page_ids.add(page['id'])

    # 并行处理页面
    processed_count = 0
    folder_stats = {}
    successful_results = []
    
    # 限制并发数，避免API限流
    max_workers = min(8, len(pages))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_page = {
            executor.submit(process_page_parallel, page, database_title, parent_title, file_mapping): page 
            for page in pages
        }
        
        # 收集结果
        for future in as_completed(future_to_page):
            result = future.result()
            if result['success']:
                successful_results.append(result)
                
                # 统计文件夹
                folder_path = result['folder_path']
                if folder_path not in folder_stats:
                    folder_stats[folder_path] = 0
                folder_stats[folder_path] += 1
                
                safe_print(f"   📄 {result['title']} -> {folder_path}")
            else:
                safe_print(f"   ❌ 处理页面失败: {result.get('error', '未知错误')}")

    # 批量处理文件
    if successful_results:
        if BATCH_COMMIT:
            # 先批量检查文件状态
            file_paths = [r['new_file_path'] for r in successful_results]
            existing_files = batch_check_github_files(file_paths)
            
            for result in successful_results:
                file_path = result['new_file_path']
                existing_info = existing_files.get(file_path, {'exists': False})
                
                if should_update_file(result['content'], existing_info):
                    if add_file_to_batch(result['folder_path'], result['filename'], result['content']):
                        processed_count += 1
        else:
            # 串行保存（如果不使用批量提交）
            for result in successful_results:
                if save_to_github_immediate(result['folder_path'], result['filename'], result['content']):
                    processed_count += 1

    # 显示统计
    if folder_stats:
        safe_print(f"   📁 {len(folder_stats)} 个文件夹，{processed_count}/{len(pages)} 个页面需要同步")
    else:
        safe_print(f"   ✅ {processed_count}/{len(pages)} 个页面需要同步")
    return processed_count


def save_to_github_immediate(folder_name, filename, content):
    """立即保存到GitHub（旧方式，保持兼容）"""
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # 构建文件路径，包含文件夹结构
    file_path = f"{GITHUB_PATH}/{folder_name}/{filename}.md"
    url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{file_path}'

    # 检查文件是否已存在
    try:
        existing_response = requests.get(url, headers=headers)
        if existing_response.status_code == 200:
            existing_data = existing_response.json()
            sha = existing_data['sha']
        else:
            sha = None
    except:
        sha = None

    # 编码内容
    encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')

    # 准备数据
    data = {
        'message': f'更新笔记: {folder_name}/{filename}',
        'content': encoded_content
    }

    if sha:
        data['sha'] = sha

    try:
        response = requests.put(url, headers=headers, json=data)
        response.raise_for_status()
        safe_print(f"✅ 成功保存文件: {folder_name}/{filename}.md")
        return True
    except requests.exceptions.RequestException as e:
        safe_print(f"❌ 保存到GitHub时出错: {e}")
        return False


def process_standalone_pages(file_mapping, database_page_ids=None):
    """处理独立页面（不在数据库中的页面）"""
    safe_print(f"\n📄 正在搜索所有独立页面...")

    # 获取所有页面
    all_pages = search_all_pages()
    safe_print(f"🔍 找到 {len(all_pages)} 个页面")

    # 如果没有传入数据库页面ID，则获取
    if database_page_ids is None:
        database_ids = get_database_ids()
        database_page_ids = set()
        for database_id in database_ids:
            notes_data = fetch_notion_notes(database_id)
            if notes_data and 'results' in notes_data:
                for page in notes_data['results']:
                    database_page_ids.add(page['id'])

    safe_print(f"🗂️ 数据库中共有 {len(database_page_ids)} 个页面")

    # 过滤出真正的独立页面
    standalone_pages = []
    for page in all_pages:
        page_id = page['id']
        
        # 跳过已经在我们配置的数据库中的页面
        if page_id in database_page_ids:
            continue
            
        parent = page.get('parent', {})
        
        # 只处理工作区根页面或不在任何数据库中的页面
        if parent.get('type') in ['workspace'] or (
            parent.get('type') == 'page_id' and 
            parent.get('page_id') not in database_page_ids
        ):
            standalone_pages.append(page)

    safe_print(f"📑 找到 {len(standalone_pages)} 个真正的独立页面")

    if not standalone_pages:
        safe_print("✅ 没有找到独立页面")
        return 0

    # 处理独立页面
    processed_count = 0
    folder_stats = {}  # 统计各个文件夹的文件数量

    for i, page in enumerate(standalone_pages, 1):
        page_id = page['id']
        title = get_page_title(page)

        if not title:
            title = f"页面_{page_id[:8]}"

        # 获取页面属性（独立页面也可能有属性）
        page_properties = get_page_properties(page)
        
        # 使用页面标题作为基础文件夹，就像数据库标题一样
        page_folder = generate_folder_path(title, page_properties)
        
        # 统计文件夹
        if page_folder not in folder_stats:
            folder_stats[page_folder] = 0
        folder_stats[page_folder] += 1

        # 获取页面内容
        content_data = get_page_content(page_id)

        # 转换为Markdown
        source_info = f"独立页面: {title}"
        markdown_content = convert_notion_to_markdown(page, content_data, source_info)

        # 文件名使用固定名称，因为文件夹已经是页面名称了
        filename = "content"  # 或者可以使用页面标题，但可能会重复
        new_file_path = f"{GITHUB_PATH}/{page_folder}/{filename}.md"

        # 检查是否需要删除旧位置的文件
        if page_id in file_mapping:
            old_file_path = file_mapping[page_id]
            if old_file_path != new_file_path:
                safe_print(f"🔄 检测到独立页面位置变更: {page_id}")
                safe_print(f"   旧位置: {old_file_path}")
                safe_print(f"   新位置: {new_file_path}")
                # 删除旧位置的文件
                delete_github_file(old_file_path)

        # 更新映射表
        file_mapping[page_id] = new_file_path

        # 添加到批量提交列表或立即保存
        if BATCH_COMMIT:
            if add_file_to_batch(page_folder, filename, markdown_content):
                safe_print(f"   📄 {title} -> {page_folder}")
                processed_count += 1
        else:
            if save_to_github_immediate(page_folder, filename, markdown_content):
                safe_print(f"   📄 {title} -> {page_folder}")
                processed_count += 1
    
    # 显示统计
    if folder_stats:
        safe_print(f"   📁 {len(folder_stats)} 个文件夹，{processed_count}/{len(standalone_pages)} 个页面需要同步")
    else:
        safe_print(f"   ✅ {processed_count}/{len(standalone_pages)} 个页面需要同步")
    return processed_count


def check_github_repo_status():
    """检查GitHub仓库状态和分支信息"""
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # 检查仓库是否存在
    repo_url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}'
    try:
        repo_response = requests.get(repo_url, headers=headers)
        if repo_response.status_code == 404:
            safe_print(f"❌ 仓库不存在: {GITHUB_OWNER}/{GITHUB_REPO}")
            safe_print(f"💡 请确认：")
            safe_print(f"   - GITHUB_OWNER: {GITHUB_OWNER}")
            safe_print(f"   - GITHUB_REPO: {GITHUB_REPO}")
            safe_print(f"   - 仓库是否存在且有权限访问")
            return False
        repo_response.raise_for_status()

        repo_data = repo_response.json()
        default_branch = repo_data['default_branch']

        safe_print(f"✅ 仓库检查通过: {GITHUB_OWNER}/{GITHUB_REPO}")
        safe_print(f"🌿 默认分支: {default_branch}")
        safe_print(f"🔒 仓库类型: {'私有' if repo_data['private'] else '公开'}")

        return True

    except requests.exceptions.RequestException as e:
        if "401" in str(e):
            safe_print(f"❌ GitHub Token权限不足")
            safe_print(f"💡 请检查：")
            safe_print(f"   - GITHUB_TOKEN是否正确")
            safe_print(f"   - Token是否有仓库访问权限")
        else:
            safe_print(f"❌ 仓库检查失败: {e}")
        return False


def sync_notion_to_github():
    """主同步函数"""
    global pending_files
    pending_files = []  # 重置待提交文件列表
    
    # 开始计时
    start_time = time.time()

    safe_print("🚀 开始同步Notion内容到GitHub...")
    safe_print(f"🔧 同步模式: {SYNC_MODE}")
    safe_print(f"📦 批量提交: {'开启' if BATCH_COMMIT else '关闭'}")
    safe_print(f"🚫 跳过提交: {'是' if SKIP_COMMIT else '否'}")
    safe_print(f"📂 文件夹分类: {'开启' if ENABLE_CATEGORIZATION else '关闭'}")
    safe_print(f"⚡ 并行处理: 已启用 (最大8个并发)")
    if ENABLE_CATEGORIZATION:
        safe_print(f"🏷️ 分类属性: {', '.join(CATEGORY_PROPERTIES)}")
    else:
        safe_print("⚠️ 文件夹分类已禁用，所有文件将放在数据库同名文件夹下")

    # 检查必要的环境变量
    if not all([NOTION_API_KEY, GITHUB_TOKEN, GITHUB_REPO, GITHUB_OWNER]):
        safe_print("❌ 错误: 缺少必要的环境变量")
        return

    # 初始化会话
    safe_print("🔧 初始化网络会话...")
    setup_sessions()

    # 检查GitHub仓库状态
    safe_print(f"\n🔍 检查GitHub仓库状态...")
    if not check_github_repo_status():
        safe_print("❌ GitHub仓库检查失败，请检查配置后重试")
        return

    # 加载文件位置映射表
    safe_print(f"📋 加载文件位置映射表...")
    file_mapping = load_file_mapping()
    safe_print(f"📊 当前跟踪 {len(file_mapping)} 个文件位置")

    total_processed = 0
    database_page_ids = set()  # 收集数据库页面ID，用于独立页面去重

    # 同步数据库
    if SYNC_MODE in ['databases', 'all']:
        database_ids = get_database_ids()

        if database_ids:
            safe_print(f"\n📊 找到 {len(database_ids)} 个数据库要同步")

            # 获取所有数据库信息
            database_infos = []
            for i, database_id in enumerate(database_ids, 1):
                safe_print(f"🔍 获取数据库 {i}/{len(database_ids)} 信息...")
                db_info = get_database_info(database_id)
                database_infos.append(db_info)
                safe_print(f"  📋 {db_info['title']}")

            # 处理每个数据库
            for i, database_info in enumerate(database_infos, 1):
                processed_count = process_database(database_info, i, len(database_infos), file_mapping, database_page_ids)
                total_processed += processed_count
        else:
            safe_print("⚠️ 没有配置数据库ID，跳过数据库同步")

    # 同步独立页面
    if SYNC_MODE in ['pages', 'all']:
        standalone_processed = process_standalone_pages(file_mapping, database_page_ids)
        total_processed += standalone_processed

    # 清理已删除页面的文件
    clean_deleted_pages(file_mapping)

    # 保存更新后的文件位置映射表
    safe_print(f"\n💾 保存文件位置映射表...")
    save_file_mapping(file_mapping)
    safe_print(f"📊 当前跟踪 {len(file_mapping)} 个文件位置")

    # 执行批量提交
    if SKIP_COMMIT:
        safe_print(f"\n⏭️ 跳过提交步骤，共准备了 {len(pending_files)} 个文件")
        safe_print(f"💡 如需提交，请设置 SKIP_COMMIT=false 重新运行")
    elif BATCH_COMMIT and pending_files:
        committed_count = commit_files_batch()
        if committed_count > 0:
            safe_print(f"\n🎉 同步完成! 所有 {committed_count} 个文件已合并到一次提交中")
            safe_print(f"📊 批量提交：{len(pending_files)} 个文件 = 1 个commit")
        else:
            safe_print(f"\n❌ 批量提交失败，已使用兼容模式")
    elif not BATCH_COMMIT and not SKIP_COMMIT:
        committed_count = commit_files_individually()
        safe_print(f"\n🎉 同步完成! 使用兼容模式提交了 {committed_count} 个文件")
    else:
        safe_print(f"\n🎉 同步完成! 没有文件需要更新")

    safe_print(f"📁 文件已保存到GitHub的 {GITHUB_PATH} 文件夹下")
    safe_print(f"📂 文件夹结构: 数据库文件夹 + 独立页面文件夹")
    
    # 显示性能统计
    end_time = time.time()
    duration = end_time - start_time
    safe_print(f"\n⏱️ 同步完成，总耗时: {duration:.2f} 秒")
    safe_print(f"🚀 性能优化已启用：并行处理 + 会话复用 + 批量检查")


if __name__ == '__main__':
    sync_notion_to_github()