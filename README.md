# 🚀 Notion到GitHub同步工具

一个强大的Python工具，可以将你的Notion笔记和数据库内容自动同步到GitHub仓库，支持智能文件夹分类、日期分组和批量提交。

## ✨ 主要特性

### 📊 多种同步模式
- **数据库同步**：同步指定Notion数据库中的所有页面
- **独立页面同步**：同步工作区中的独立页面
- **全量同步**：同步数据库页面 + 独立页面

### 📁 智能文件夹分类
- 根据Notion页面属性自动创建子文件夹
- 支持状态、分类、类型等多种属性类型
- **🗓️ 日期分组**：自动识别日期属性，按时间段分组（如：2024年3月17日-23日）
- 可自定义分类属性优先级

### 🔄 智能提交机制
- 内容变更检测，只提交真正有变化的文件
- **单次批量提交**：所有变更合并到一个commit中
- 自动回退机制，确保提交成功
- **文件位置跟踪**：自动清理位置变更后的旧文件
- **预览模式**：支持跳过提交，仅准备文件

### 🛠️ 数据库分析工具
- 自动分析数据库结构和属性
- 推荐最佳分类配置
- 实际数据分布统计

## 📦 安装

### 环境要求
- Python 3.7+
- 有效的Notion API密钥
- GitHub个人访问令牌

### 依赖安装
```bash
pip install requests python-dotenv
```

## 🔧 配置

### 1. 创建配置文件
复制 `env.example` 为 `.env` 并填入你的配置：

```bash
cp env.example .env
```

### 2. 必需配置
```bash
# Notion API配置
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 数据库ID（支持多个，用逗号分隔）
NOTION_DATABASE_IDS=database_id_1,database_id_2,database_id_3

# GitHub配置
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_OWNER=your_username
GITHUB_REPO=your_repo_name
GITHUB_PATH=notes
```

### 3. 可选配置
```bash
# 同步模式
SYNC_MODE=all  # all/databases/pages

# 批量提交
BATCH_COMMIT=true

# 跳过提交（预览模式）
SKIP_COMMIT=false

# 文件夹分类
ENABLE_CATEGORIZATION=true
CATEGORY_PROPERTIES=Status,Category,Type,状态,分类,类型,Full Date
```

## 🚀 使用方法

### 基本同步
```bash
python sync.py
```

### 预览模式（不提交到GitHub）
设置环境变量后运行：
```bash
# Windows
set SKIP_COMMIT=true && python sync.py

# macOS/Linux
SKIP_COMMIT=true python sync.py
```

### 分析数据库结构
在配置分类属性前，建议先分析你的数据库结构：
```bash
python analyze_databases.py
```

这会输出类似这样的分析结果：
```
🔍 Notion数据库属性分析工具
==================================================
📊 找到 3 个数据库要分析

🗃️ 分析数据库 1/3: abc123...
📋 数据库名称: Habit Tracker
🔧 找到 5 个属性:

  🗓️ Full Date (日期)
     🎯 日期属性，支持按时间段分组
     📊 实际数据:
       • 2024-03-17 (1次)
       • 2024-03-18 (1次)
       • 2024-03-22 (1次)
     ✅ 推荐用于日期分组
     
  📋 Status (状态)
     🎯 状态选项: Not started, Reading, Completed
     📊 实际数据:
       • Reading (3次)
       • Completed (2次)
       • Not started (1次)
     ✅ 推荐用于分类

💡 配置建议:
------------------------------
📝 建议的 CATEGORY_PROPERTIES 配置:
CATEGORY_PROPERTIES=Status,Full Date

📂 启用分类:
ENABLE_CATEGORIZATION=true
```

## 📂 文件夹结构示例

> **📝 说明**：`notes/` 目录下的内容为示例，实际使用时会是你自己的Notion内容。

### 启用分类前
```
notes/
├── Reading List/
│   ├── Go.md
│   ├── Python.md
│   └── New_book.md
├── Habit Tracker/
│   ├── 2024-03-17.md
│   ├── 2024-03-18.md
│   └── 2024-03-22.md
└── Journal/
    └── content.md
```

### 启用分类后（含日期分组）
```
notes/
├── Reading List/
│   ├── Not started/
│   │   └── The_Girl_with_the_Dragon_Tattoo.md
│   ├── Reading/
│   │   ├── Go.md
│   │   ├── Python.md
│   │   └── New_book.md
│   └── Completed/
│       ├── To_Kill_a_Mockingbird.md
│       └── Brave_New_World.md
├── Habit Tracker/
│   ├── 2024年3月17日-23日/
│   │   ├── 2024-03-17.md
│   │   ├── 2024-03-18.md
│   │   └── 2024-03-22.md
│   └── 2024年3月24日-30日/
│       ├── 2024-03-24.md
│       └── 2024-03-26.md
└── Journal/
    ├── Personal/
    │   └── content.md
    └── Work/
        └── content.md
```

## ⚙️ 配置选项详解

### 同步模式 (SYNC_MODE)
| 值 | 说明 |
|---|---|
| `all` | 同步数据库页面 + 独立页面（推荐） |
| `databases` | 只同步指定的数据库 |
| `pages` | 只同步独立页面 |

### 批量提交 (BATCH_COMMIT)
| 值 | 说明 |
|---|---|
| `true` | 启用单次批量提交（推荐） |
| `false` | 每个文件单独提交 |

**单次批量提交说明**：
- `true`：使用GitHub Tree API，所有文件变更合并到一个commit中
- `false`：每个文件单独创建commit
- 失败时自动回退到兼容模式（单个文件提交）

### 跳过提交 (SKIP_COMMIT)
| 值 | 说明 |
|---|---|
| `false` | 正常提交到GitHub（默认） |
| `true` | 跳过提交，仅准备文件（预览模式） |

### 文件夹分类 (ENABLE_CATEGORIZATION)
| 值 | 说明 |
|---|---|
| `true` | 根据页面属性创建子文件夹 |
| `false` | 所有文件放在数据库同名文件夹下 |

### 分类属性 (CATEGORY_PROPERTIES)
支持的属性类型：
- `select` (单选)
- `multi_select` (多选)
- `status` (状态)
- `checkbox` (复选框)
- `rich_text` (文本)
- `number` (数字)
- `date` (日期) - **支持自动时间段分组**

### 🗓️ 日期分组特性

当分类属性中包含日期类型属性时，工具会自动识别并进行智能分组：

#### 支持的日期属性关键词
- `date`, `time`, `日期`, `时间`, `full date`

#### 分组规则
- **按周分组**：周日到周六为一个时间段
- **智能命名**：如 "2024年3月17日-23日"
- **跨月处理**：如 "2024年3月29日-4月4日"
- **跨年处理**：如 "2023年12月31日-2024年1月6日"

#### 示例配置
```bash
# 对于Habit Tracker数据库，使用Full Date属性进行日期分组
CATEGORY_PROPERTIES=Status,Full Date

# 对于不同数据库使用不同策略
# Reading List使用Status分类，Habit Tracker使用Full Date分组
```

## 🔑 获取API密钥

### Notion API密钥
1. 访问 [Notion开发者页面](https://www.notion.so/my-integrations)
2. 创建新的集成(Integration)
3. 复制Internal Integration Token
4. 在Notion中分享数据库给你的集成

### GitHub Token
1. 访问 [GitHub Token设置](https://github.com/settings/tokens)
2. 点击"Generate new token (classic)"
3. 选择权限：`repo` (仓库完全访问权限)
4. 复制生成的token

### 获取数据库ID
1. 在浏览器中打开你的Notion数据库
2. 复制URL中的数据库ID（32位十六进制字符串）
3. URL格式：`https://notion.so/database_id?v=view_id`

## 🎯 使用技巧

### 1. 多数据库同步
```bash
NOTION_DATABASE_IDS=database1_id,database2_id,database3_id
```

### 2. 自定义分类属性
根据你的数据库结构，调整分类属性的优先级：
```bash
CATEGORY_PROPERTIES=Priority,Status,Category,Type
```

### 3. 处理中文属性
工具支持中英文混合的属性名：
```bash
CATEGORY_PROPERTIES=Status,Category,状态,分类,类型
```

### 4. 独立页面智能分类
独立页面（非数据库页面）的处理方式：
- **自动去重**：智能识别并跳过已在配置数据库中的页面，避免重复同步
- **独立文件夹**：每个独立页面创建自己的文件夹，以页面标题命名
- **分类支持**：独立页面也支持按属性分类创建子文件夹
- 例如：独立页面"Journal"有属性"Category=Personal" → `Journal/Personal/content.md`

### 5. 文件位置自动清理
工具会自动跟踪每个页面的文件位置：
- 当页面的分类属性发生变化时，自动删除旧位置的文件
- 维护一个 `file_mapping.json` 文件来跟踪页面ID和文件路径的对应关系
- 避免同一页面在多个位置存在副本

## 🐛 故障排除

### 常见错误

#### 1. API权限错误
```
❌ GitHub Token权限不足
```
**解决方案**：检查GitHub Token是否有`repo`权限

#### 2. 数据库访问错误
```
❌ 获取数据库 xxx 信息时出错: 404
```
**解决方案**：确保数据库已分享给你的Notion集成

#### 3. 仓库不存在
```
❌ 仓库不存在: username/repo
```
**解决方案**：检查`GITHUB_OWNER`和`GITHUB_REPO`配置

### 兼容性处理

工具内置多种兼容性处理机制：
- 自动检测GitHub API限制
- 批量提交失败时自动回退到单文件提交
- 智能冲突检测和重试

## 📈 高级功能

### 自动化运行
可以配合GitHub Actions或系统定时任务实现自动同步：

```yaml
# .github/workflows/notion-sync.yml
name: Notion Sync
on:
  schedule:
    - cron: '0 */6 * * *'  # 每6小时运行一次
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - run: pip install requests python-dotenv
    - run: python sync.py
      env:
        NOTION_API_KEY: ${{ secrets.NOTION_API_KEY }}
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        # ... 其他环境变量
```

### 自定义Markdown转换
可以修改`convert_notion_to_markdown`函数来自定义转换规则。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

感谢Notion和GitHub提供的优秀API服务。

---

**💡 提示**：首次使用建议先运行`analyze_databases.py`来了解你的数据库结构，然后根据分析结果调整配置。 