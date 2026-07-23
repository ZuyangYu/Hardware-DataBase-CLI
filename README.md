# Hardware DataBase CLI & MCP

Hardware DataBase API 的独立 CLI 客户端和 MCP server。

## 安装

```bash
pip install git+https://github.com/ZuyangYu/Hardware-DataBase-CLI.git@INTERN-DEVELOP
# 或本地开发
pip install -e .
```

## CLI — `hardware-database`

HTTP 客户端，连接 Hardware DataBase API server。

```bash
# 登录
hardware-database login --user admin

# 列出知识库
hardware-database list-kb

# 检索（流式）
hardware-database query --kb my_kb "问题"

# JSON 输出（供 agent 消费）
hardware-database --json query --kb my_kb "问题"

# 上传文件
hardware-database upload --kb my_kb file1.xlsx file2.pdf

# 列出文件
hardware-database list-files --kb my_kb

# 删除文件
hardware-database delete --kb my_kb --file 某文件
```

全局选项: `--api-url`, `--token`, `--json`。Token 也可通过 `HDB_TOKEN` 环境变量或 `login` 保存的会话文件提供。

### 环境变量

| 变量 | 说明 |
|------|------|
| `HDB_API_URL` | API 地址（默认 `http://127.0.0.1:8000`） |
| `HDB_TOKEN` | Bearer token（优先级高于会话文件） |

## MCP — `hardware-database-mcp`

stdio MCP server，把 API 暴露给 Claude Code 等本地 agent。

```bash
hardware-database-mcp
```

### MCP 工具

| 工具 | 说明 |
|------|------|
| `health` | 探测 API 可达性 + 认证状态 |
| `whoami` | 当前用户信息 |
| `list_kbs` | 可访问知识库 |
| `list_files` | 知识库文件列表 |
| `query` | 执行硬件设计查询 |
| `upload` | 上传文件 |
| `delete` | 删除文件 |

## 依赖

- Python >= 3.12
- httpx (HTTP 客户端)
- mcp (MCP server)

## 架构

CLI 和 MCP 都是 Hardware DataBase API server 的 HTTP 客户端，不持有业务逻辑。
API server (`hardware-database-server`) 需单独运行。
