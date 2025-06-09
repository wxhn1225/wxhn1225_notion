import requests
import json
import os
from dotenv import load_dotenv
from collections import defaultdict

# 加载环境变量
load_dotenv()

NOTION_API_KEY = os.getenv('NOTION_API_KEY')
NOTION_DATABASE_IDS = os.getenv('NOTION_DATABASE_IDS')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')  # 兼容旧版本


def get_database_ids():
    """获取要分析的数据库ID列表"""
    if NOTION_DATABASE_IDS:
        database_ids = [db_id.strip() for db_id in NOTION_DATABASE_IDS.split(',') if db_id.strip()]
        return database_ids
    elif NOTION_DATABASE_ID:
        return [NOTION_DATABASE_ID.strip()]
    else:
        return []


def get_database_schema(database_id):
    """获取数据库的结构信息"""
    headers = {
        'Authorization': f'Bearer {NOTION_API_KEY}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }

    url = f'https://api.notion.com/v1/databases/{database_id}'

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ 获取数据库 {database_id} 结构时出错: {e}")
        return None


def get_database_sample_data(database_id, limit=10):
    """获取数据库的示例数据，用于分析属性值"""
    headers = {
        'Authorization': f'Bearer {NOTION_API_KEY}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }

    url = f'https://api.notion.com/v1/databases/{database_id}/query'
    data = {
        'page_size': limit
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ 获取数据库 {database_id} 示例数据时出错: {e}")
        return None


def analyze_property_values(sample_data, property_name, property_type):
    """分析属性在实际数据中的值分布"""
    values = []
    
    if not sample_data or 'results' not in sample_data:
        return values
    
    for page in sample_data['results']:
        if 'properties' not in page or property_name not in page['properties']:
            continue
            
        prop_data = page['properties'][property_name]
        
        if property_type == 'select' and 'select' in prop_data and prop_data['select']:
            values.append(prop_data['select']['name'])
        elif property_type == 'multi_select' and 'multi_select' in prop_data:
            values.extend([item['name'] for item in prop_data['multi_select']])
        elif property_type == 'status' and 'status' in prop_data and prop_data['status']:
            values.append(prop_data['status']['name'])
        elif property_type == 'checkbox' and 'checkbox' in prop_data:
            values.append('✅ 已选中' if prop_data['checkbox'] else '⬜ 未选中')
        elif property_type == 'rich_text' and 'rich_text' in prop_data and prop_data['rich_text']:
            values.append(prop_data['rich_text'][0]['plain_text'][:50])  # 限制长度
        elif property_type == 'number' and 'number' in prop_data and prop_data['number'] is not None:
            values.append(str(prop_data['number']))
    
    # 统计值的出现次数
    value_counts = defaultdict(int)
    for value in values:
        value_counts[value] += 1
    
    return dict(value_counts)


def format_property_info(prop_name, prop_config, sample_values):
    """格式化属性信息显示"""
    prop_type = prop_config.get('type', 'unknown')
    
    # 属性类型的中文说明
    type_names = {
        'title': '标题',
        'rich_text': '文本',
        'number': '数字',
        'select': '单选',
        'multi_select': '多选',
        'date': '日期',
        'checkbox': '复选框',
        'url': '链接',
        'email': '邮箱',
        'phone_number': '电话',
        'formula': '公式',
        'relation': '关联',
        'rollup': '汇总',
        'people': '人员',
        'files': '文件',
        'status': '状态',
        'created_time': '创建时间',
        'created_by': '创建者',
        'last_edited_time': '最后编辑时间',
        'last_edited_by': '最后编辑者'
    }
    
    type_display = type_names.get(prop_type, prop_type)
    result = f"  📋 属性名称: 「{prop_name}」 ({type_display})"
    
    # 显示预定义选项（对于select和multi_select）
    if prop_type == 'select' and 'select' in prop_config and 'options' in prop_config['select']:
        options = [opt['name'] for opt in prop_config['select']['options']]
        result += f"\n     🎯 可选值: {', '.join(options)}"
    elif prop_type == 'multi_select' and 'multi_select' in prop_config and 'options' in prop_config['multi_select']:
        options = [opt['name'] for opt in prop_config['multi_select']['options']]
        result += f"\n     🎯 可选值: {', '.join(options)}"
    elif prop_type == 'status' and 'status' in prop_config and 'options' in prop_config['status']:
        options = [opt['name'] for opt in prop_config['status']['options']]
        result += f"\n     🎯 状态值: {', '.join(options)}"
    
    # 显示实际数据中的值分布
    if sample_values:
        result += f"\n     📊 实际使用的值:"
        sorted_values = sorted(sample_values.items(), key=lambda x: x[1], reverse=True)
        for value, count in sorted_values[:5]:  # 只显示前5个最常见的值
            if len(value) > 30:
                value = value[:30] + "..."
            result += f"\n       • 「{value}」 ({count}次)"
        if len(sample_values) > 5:
            result += f"\n       • ... 还有{len(sample_values) - 5}个其他值"
    
    return result


def is_good_for_categorization(prop_name, prop_config, sample_values):
    """判断属性是否适合用于文件夹分类"""
    prop_type = prop_config.get('type', '')
    
    # 适合分类的属性类型
    good_types = ['select', 'multi_select', 'status', 'checkbox']
    
    if prop_type not in good_types:
        return False
    
    # 检查是否有合理的值分布
    if not sample_values:
        return False
    
    # 如果只有1个值或超过10个值，可能不太适合分类
    unique_values = len(sample_values)
    if unique_values < 2:
        return False
    if unique_values > 15:  # 放宽限制，允许更多选项
        return False
    
    # 检查数据分布是否合理（避免过于偏斜的分布）
    total_count = sum(sample_values.values())
    if total_count < 2:  # 总数据太少
        return False
    
    # 计算最大值占比，如果超过90%说明分布太偏斜
    max_count = max(sample_values.values())
    if max_count / total_count > 0.9:
        return False
    
    # 优先推荐常见的分类属性名
    priority_names = ['status', 'state', 'type', 'category', 'tag', 'priority', 'stage', 'phase']
    if prop_name.lower() in priority_names:
        return True
    
    return True


def get_categorization_rejection_reason(prop_name, prop_config, sample_values):
    """分析为什么属性不适合分类"""
    prop_type = prop_config.get('type', '')
    
    # 检查类型
    good_types = ['select', 'multi_select', 'status', 'checkbox']
    if prop_type not in good_types:
        return f"属性类型 '{prop_type}' 不适合分类"
    
    # 检查值的数量
    if not sample_values:
        return "没有找到实际数据"
    
    unique_values = len(sample_values)
    if unique_values < 2:
        return f"只有{unique_values}个不同的值，太少了"
    if unique_values > 15:
        return f"有{unique_values}个不同的值，太多了"
    
    # 检查数据分布
    total_count = sum(sample_values.values())
    if total_count < 2:
        return "总数据量太少"
    
    max_count = max(sample_values.values())
    if max_count / total_count > 0.9:
        return f"数据分布过于集中({max_count}/{total_count})"
    
    return None


def analyze_notion_databases():
    """分析Notion数据库结构"""
    print("🔍 Notion数据库属性分析工具")
    print("=" * 50)
    print("📖 本工具将帮助你:")
    print("   1. 分析Notion数据库的属性结构")
    print("   2. 找出适合文件夹分类的属性")
    print("   3. 生成正确的CATEGORY_PROPERTIES配置")
    print("   4. 避免混淆属性名称和属性值")
    print("=" * 50)
    
    # 检查API密钥
    if not NOTION_API_KEY:
        print("❌ 错误: 未找到NOTION_API_KEY环境变量")
        print("💡 请确保.env文件中配置了正确的Notion API密钥")
        return
    
    # 获取数据库ID列表
    database_ids = get_database_ids()
    if not database_ids:
        print("❌ 错误: 未找到数据库ID配置")
        print("💡 请在.env文件中配置NOTION_DATABASE_IDS或NOTION_DATABASE_ID")
        return
    
    print(f"📊 找到 {len(database_ids)} 个数据库要分析\n")
    
    all_good_properties = []  # 存储所有适合分类的属性
    
    for i, database_id in enumerate(database_ids, 1):
        print(f"🗃️ 分析数据库 {i}/{len(database_ids)}: {database_id}")
        
        # 获取数据库结构
        schema = get_database_schema(database_id)
        if not schema:
            continue
        
        # 获取数据库标题
        db_title = "未命名数据库"
        if 'title' in schema and schema['title']:
            db_title = schema['title'][0]['plain_text']
        
        print(f"📋 数据库名称: {db_title}")
        
        # 获取示例数据
        sample_data = get_database_sample_data(database_id)
        
        # 分析属性
        properties = schema.get('properties', {})
        print(f"🔧 找到 {len(properties)} 个属性:\n")
        
        db_good_properties = []
        
        for prop_name, prop_config in properties.items():
            # 分析属性在实际数据中的值
            prop_type = prop_config.get('type', '')
            sample_values = analyze_property_values(sample_data, prop_name, prop_type)
            
            # 显示属性信息
            print(format_property_info(prop_name, prop_config, sample_values))
            
            # 检查是否适合分类
            if is_good_for_categorization(prop_name, prop_config, sample_values):
                db_good_properties.append(prop_name)
                all_good_properties.append(prop_name)
                print(f"     ✅ 推荐用于分类")
                
                # 显示分类统计
                if sample_values:
                    total_pages = sum(sample_values.values())
                    print(f"     📈 分类统计: {len(sample_values)}个分类，共{total_pages}个页面")
            else:
                # 说明不推荐的原因
                reason = get_categorization_rejection_reason(prop_name, prop_config, sample_values)
                if reason:
                    print(f"     ❌ 不推荐分类: {reason}")
            
            print()
        
        if db_good_properties:
            print(f"🎯 该数据库推荐的分类属性: {', '.join(db_good_properties)}")
            # 显示具体的文件夹结构预览
            for prop in db_good_properties[:1]:  # 只显示第一个属性作为示例
                prop_sample_values = analyze_property_values(sample_data, prop, 
                    next(p['type'] for p_name, p in properties.items() if p_name == prop))
                if prop_sample_values:
                    print(f"   📂 使用「{prop}」属性的文件夹结构:")
                    for value in list(prop_sample_values.keys())[:3]:  # 只显示前3个值
                        print(f"      {db_title}/{value}/页面.md")
                    if len(prop_sample_values) > 3:
                        print(f"      ... 还有{len(prop_sample_values) - 3}个其他文件夹")
        else:
            print("⚠️ 该数据库没有找到适合分类的属性")
        
        print("=" * 50)
        print()
    
    # 生成配置建议
    print("💡 配置建议:")
    print("=" * 50)
    
    if all_good_properties:
        # 去重并保持顺序
        unique_properties = []
        seen = set()
        for prop in all_good_properties:
            if prop not in seen:
                unique_properties.append(prop)
                seen.add(prop)
        
        print("📝 推荐的环境变量配置:")
        print()
        print("# 启用文件夹分类")
        print("ENABLE_CATEGORIZATION=true")
        print()
        print("# 分类属性名称（注意：是属性名称，不是属性值）")
        suggested_config = ','.join(unique_properties)
        print(f"CATEGORY_PROPERTIES={suggested_config}")
        print()
        
        print("🏷️ 重要说明:")
        print("- CATEGORY_PROPERTIES 配置的是「属性名称」")
        print("- 例如：如果你的页面有 Status 属性，配置 Status（不是 Reading、Completed）")
        print("- 工具会自动根据属性的值创建子文件夹")
        print()
        
        print("📂 预期的文件夹结构:")
        for prop in unique_properties[:2]:  # 只显示前2个作为示例
            print(f"- 基于「{prop}」属性:")
            print(f"  数据库名/属性值1/页面.md")
            print(f"  数据库名/属性值2/页面.md")
        
    else:
        print("⚠️ 未找到适合分类的属性，建议禁用分类功能:")
        print()
        print("ENABLE_CATEGORIZATION=false")
        print()
        print("💡 原因：没有找到具有2-10个不同值的select/status/checkbox属性")
    
    print("\n" + "=" * 50)
    print("🎉 分析完成! 请根据上述建议更新你的 .env 文件")




if __name__ == '__main__':
    analyze_notion_databases() 