# 🚀 Notion 到 GitHub 同步工具

> 一个强大的 Python 工具，将你的 Notion 笔记和数据库内容自动同步到 GitHub 仓库

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 项目简介

这是一个专为 Notion 用户设计的同步工具，能够将你的 Notion 工作区内容智能地同步到 GitHub 仓库。无论是个人笔记、项目管理还是知识库，都能轻松实现版本控制和备份。

**核心优势：**
- 🔄 **智能同步**：自动检测内容变更，只同步真正有变化的文件
- 📁 **智能分类**：根据 Notion 属性自动创建文件夹结构
- 🗓️ **日期分组**：支持按时间段自动分组（如：2024年3月17日-23日）
- 🚀 **批量提交**：所有变更合并到一个 commit，提高效率
- 🏗️ **父子数据库**：智能识别并正确处理嵌套数据库结构
- 📊 **嵌入表格**：页面中的数据库自动转换为 markdown 表格显示
- 🛠️ **易于配置**：简单的环境变量配置，开箱即用

## ✨ 主要特性

### 📊 多种同步模式
- **数据库同步**：同步指定Notion数据库中的所有页面
- **独立页面同步**：同步工作区中的独立页面
- **全量同步**：同步数据库页面 + 独立页面

### 🏗️ 父子数据库支持
- **智能识别**：自动检测数据库的父页面关系
- **结构保持**：保持 "父页面/子数据库" 的文件夹结构
- **嵌入表格**：页面中嵌入的数据库自动转换为 markdown 表格
- **完整展示**：表格显示完整数据，无长度限制

#### 父子数据库示例
```
页面结构：New PC 页面 → 包含 "环境安装" 数据库

同步后文件结构：
notes/
└── New PC/
    ├── content.md              # New PC 页面内容（包含环境安装表格）
    └── 环境安装/                # 环境安装数据库内容
        ├── 通用IDE.md
        ├── Python.md
        ├── C++.md
        └── ...
```

### 📊 嵌入数据库表格
当页面中包含嵌入的数据库时，会自动：
- 在页面内容中生成完整的 markdown 表格
- 保持数据库的独立文件夹同步
- 支持自定义表格列显示顺序
- 显示完整数据内容，无字符限制

#### 表格显示示例
```markdown
### 📋 环境安装

| 开发 | 环境 |
| --- | --- |
| 通用IDE | VSCode、Cursor |
| Python | PyCharm、Anaconda |
| C++ | CLion、VS、MinGW-win64、CMake |
| Go | GoLand |
| Linux | WSL2（Ubuntu） |
| Docker | Docker Desktop |
| Git | Git、Github Desktop |
| Java | IDEA |
| Remote | Termius、Xshell、Xftp |

> **说明**: 此数据库内容已同步到 `环境安装/` 文件夹，每行数据对应一个独立的markdown文件
```

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

# 数据库表格显示（新增）
DATABASE_TABLE_PROPERTIES=开发,环境  # 自定义表格列顺序
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
📋 数据库名称: 环境安装
🔗 父页面: New PC
🔧 找到 2 个属性:

  📝 开发 (标题)
     🎯 标题属性，用于页面名称
     📊 实际数据:
       • 通用IDE (1次)
       • Python (1次)
       • C++ (1次)
     ✅ 推荐作为主要标识
     
  🔗 环境 (URL)
     🎯 URL属性，存储相关链接
     📊 实际数据:
       • VSCode、Cursor (1次)
       • PyCharm、Anaconda (1次)
     ✅ 推荐显示在表格中

💡 配置建议:
------------------------------
📝 建议的 DATABASE_TABLE_PROPERTIES 配置:
DATABASE_TABLE_PROPERTIES=开发,环境

📂 父子关系:
此数据库将同步到: New PC/环境安装/
```

## 📂 文件夹结构示例

> **📝 说明**：`notes/` 目录下的内容为示例，实际使用时会是你自己的Notion内容。

### 父子数据库结构示例
```
notes/
├── New PC/                     # 父页面
│   ├── content.md              # 页面内容（包含嵌入的环境安装表格）
│   └── 环境安装/               # 子数据库
│       ├── 通用IDE.md
│       ├── Python.md
│       ├── C++.md
│       ├── Go.md
│       ├── Linux.md
│       ├── Docker.md
│       ├── Git.md
│       ├── Java.md
│       └── Remote.md
├── Reading List/               # 独立数据库
│   ├── Not started/
│   │   └── The_Girl_with_the_Dragon_Tattoo.md
│   ├── Reading/
│   │   ├── Go.md
│   │   ├── Python.md
│   │   └── New_book.md
│   └── Completed/
│       ├── To_Kill_a_Mockingbird.md
│       └── Brave_New_World.md
└── Habit Tracker/              # 日期分组数据库
    ├── 2024年3月17日-23日/
    │   ├── 2024-03-17.md
    │   ├── 2024-03-18.md
    │   └── 2024-03-22.md
    └── 2024年3月24日-30日/
        ├── 2024-03-24.md
        └── 2024-03-26.md
```

## ⚙️ 配置选项详解

### 数据库表格配置 (DATABASE_TABLE_PROPERTIES) 🆕
控制嵌入数据库在页面中的表格显示：

```bash
# 自定义表格列顺序（用逗号分隔，注意等号后不要有空格）
DATABASE_TABLE_PROPERTIES=开发,环境

# 空值表示使用默认智能选择
DATABASE_TABLE_PROPERTIES=
```

**功能说明：**
- 🎯 **自定义列顺序**：按指定顺序显示表格列
- 📊 **完整数据**：显示完整内容，无字符长度限制
- 🔄 **智能回退**：如果指定属性不存在，自动使用可用属性
- 📋 **支持中英文**：属性名支持中英文混合

**示例效果：**
```markdown
# New PC

## 开发环境

### 📋 环境安装

| 开发 | 环境 |
| --- | --- |
| 通用IDE | VSCode、Cursor |
| Python | PyCharm、Anaconda |
| C++ | CLion、VS、MinGW-win64、CMake |
```

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
- `title` (标题) - **支持作为主要分类**
- `url` (链接) - **支持作为辅助信息**

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
5. **重要**：确保对嵌套数据库也分享权限

### GitHub Token
1. 访问 [GitHub Token设置](https://github.com/settings/tokens)
2. 点击"Generate new token (classic)"
3. 选择权限：`repo` (仓库完全访问权限)
4. 复制生成的token

### 获取数据库ID
1. 在浏览器中打开你的Notion数据库
2. 复制URL中的数据库ID（32位十六进制字符串）
3. URL格式：`https://notion.so/database_id?v=view_id`

**📝 注意**：对于嵌入在页面中的数据库，你也需要获取其独立的数据库ID。

## 🎯 使用技巧

### 1. 多数据库同步
```bash
NOTION_DATABASE_IDS=database1_id,database2_id,database3_id
```

### 2. 嵌入数据库表格优化 🆕
```bash
# 自定义表格列显示顺序
DATABASE_TABLE_PROPERTIES=名称,状态,类型,环境

# 支持中英文混合
DATABASE_TABLE_PROPERTIES=Title,状态,Category,环境

# 留空使用智能默认选择
DATABASE_TABLE_PROPERTIES=
```

### 3. 处理父子数据库关系 🆕
- **自动识别**：工具会自动检测数据库的父页面关系
- **结构保持**：文件夹结构会反映 Notion 中的层级关系
- **双重同步**：页面内容 + 数据库独立文件都会同步

### 4. 自定义分类属性
根据你的数据库结构，调整分类属性的优先级：
```bash
CATEGORY_PROPERTIES=Priority,Status,Category,Type
```

### 5. 处理中文属性
工具支持中英文混合的属性名：
```bash
CATEGORY_PROPERTIES=Status,Category,状态,分类,类型
```

### 6. 独立页面智能分类
独立页面（非数据库页面）的处理方式：
- **自动去重**：智能识别并跳过已在配置数据库中的页面，避免重复同步
- **独立文件夹**：每个独立页面创建自己的文件夹，以页面标题命名
- **分类支持**：独立页面也支持按属性分类创建子文件夹
- 例如：独立页面"Journal"有属性"Category=Personal" → `Journal/Personal/content.md`

### 7. 文件位置自动清理
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
**解决方案**：确保数据库已分享给你的Notion集成，特别是嵌入的子数据库

#### 3. 仓库不存在
```
❌ 仓库不存在: username/repo
```
**解决方案**：检查`GITHUB_OWNER`和`GITHUB_REPO`配置

#### 4. 表格显示不完整 🆕
```
⚠️ 表格某些列显示为空或被截断
```
**解决方案**：
- 检查 `DATABASE_TABLE_PROPERTIES` 配置是否正确
- 确认属性名称与 Notion 中完全一致
- 使用空值让工具自动选择可用属性

### 兼容性处理

工具内置多种兼容性处理机制：
- 自动检测GitHub API限制
- 批量提交失败时自动回退到单文件提交
- 智能冲突检测和重试
- 父子数据库关系容错处理

## 📈 高级功能

### 嵌入数据库表格自定义 🆕
可以通过环境变量精确控制表格显示：

```bash
# 示例1：开发环境配置表格
DATABASE_TABLE_PROPERTIES=开发,环境

# 示例2：任务管理表格
DATABASE_TABLE_PROPERTIES=任务,状态,优先级,截止日期

# 示例3：书单管理表格  
DATABASE_TABLE_PROPERTIES=书名,作者,状态,评分
```

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
        DATABASE_TABLE_PROPERTIES: ${{ vars.DATABASE_TABLE_PROPERTIES }}
        # ... 其他环境变量
```

### 自定义Markdown转换
可以修改`convert_notion_to_markdown`函数来自定义转换规则。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## ❓ 常见问题

### Q: file_mapping.json 文件是什么？
A: 这是工具自动生成的映射文件，用于跟踪 Notion 页面 ID 和本地文件路径的对应关系。当页面属性变化导致文件位置改变时，工具会自动清理旧位置的文件。

### Q: 支持哪些 Notion 属性类型？
A: 支持所有常见属性类型，包括：select、multi_select、status、checkbox、rich_text、number、date、title、url、formula、rollup 等。

### Q: 如何处理嵌入的数据库？🆕
A: 工具会自动识别页面中嵌入的数据库（child_database），并：
- 在页面内容中生成对应的 markdown 表格
- 同时保持数据库内容的独立文件夹同步
- 支持通过 DATABASE_TABLE_PROPERTIES 自定义表格显示

### Q: 父子数据库关系如何处理？🆕
A: 工具会自动检测数据库的父页面关系，并在文件夹结构中保持这种层级关系。例如："New PC/环境安装/" 这样的结构。

### Q: 如何处理大量数据？
A: 工具内置智能缓存机制，只同步有变更的内容。首次同步可能较慢，后续增量同步会很快。

### Q: 表格数据显示不完整怎么办？🆕  
A: 最新版本已移除字符长度限制，会显示完整数据。如果仍有问题，请检查：
- DATABASE_TABLE_PROPERTIES 配置是否正确
- 属性名称是否与 Notion 中一致
- 数据库是否正确分享给了集成

## 🙏 致谢

感谢 Notion 和 GitHub 提供的优秀 API 服务。

## 📞 联系

如有问题或建议，欢迎：
- 提交 [Issue](../../issues)
- 发起 [Pull Request](../../pulls)
- 在 [Discussions](../../discussions) 中讨论

---

**💡 提示**：首次使用建议先运行 `analyze_databases.py` 来了解你的数据库结构，然后根据分析结果调整配置。对于包含嵌入数据库的页面，特别推荐使用 `DATABASE_TABLE_PROPERTIES` 来优化表格显示效果。

**⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！** 