# A股金融数据代理服务

## 项目概述

开发代理请求的A股市场金融数据服务，通过智能代理轮换和频率控制规避IP封禁，支持全部非ST A股股票的数据收集和下载。

## 核心功能

1. **代理增强的数据获取**：通过代理池轮换规避akshare IP封禁
2. **定时/手动数据更新**：支持15:05自动定时任务和手动触发
3. **Bearer Token认证的API**：提供安全的数据下载接口
4. **时间区间和股票代码过滤**：灵活的数据查询能力
5. **前复权日线数据**：最近3年历史数据

## 技术栈

- **后端**：Python 3.11+ + FastAPI
- **数据库**：PostgreSQL 15 + TimescaleDB 2.11+
- **定时任务**：Celery 5.3+ + Redis 7+
- **代理管理**：requests + 代理池轮换
- **部署**：Docker + 阿里云服务器（4CPU/8GB）

## 快速开始

### 环境要求
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (可选)

### 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 配置环境变量

```bash
cp .env.example .env
# 编辑.env文件，填写必要的配置
```

### 运行数据库迁移

```bash
# 使用Docker（推荐）
docker-compose up -d postgres redis

# 或使用本地PostgreSQL/Redis
# 确保配置正确的连接字符串
```

### 启动服务

```bash
# 启动FastAPI服务器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 启动Celery worker
celery -A src.tasks.celery_app worker --loglevel=info

# 启动Celery beat（定时任务调度器）
celery -A src.tasks.celery_app beat --loglevel=info
```

## 项目结构

```
.
├── src/
│   ├── api/              # FastAPI端点
│   │   ├── __init__.py
│   │   ├── auth.py      # 认证相关路由
│   │   └── stocks.py    # 股票数据路由
│   ├── models/           # SQLAlchemy模型
│   │   ├── __init__.py
│   │   ├── database.py  # 数据库连接
│   │   └── stock_data.py # 股票数据模型
│   ├── services/         # 业务逻辑
│   │   ├── __init__.py
│   │   └── data_fetcher.py # 数据获取服务
│   ├── tasks/           # Celery任务
│   │   ├── __init__.py
│   │   └── celery_app.py # Celery配置和任务
│   └── utils/           # 工具函数
│       ├── __init__.py
│       ├── proxy_pool.py    # 代理池管理
│       └── frequency_control.py # 频率控制
├── tests/               # 测试
├── docker/              # Docker配置
│   ├── Dockerfile
│   └── docker-compose.yml
├── migrations/          # 数据库迁移
├── requirements.txt      # Python依赖
├── .env.example       # 环境变量示例
└── README.md          # 本文件
```

## API文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 配置说明

### 关键配置项

| 环境变量 | 说明 | 默认值 |
|-----------|------|--------|
| `DATABASE_URL` | PostgreSQL连接字符串 | - |
| `REDIS_URL` | Redis连接字符串 | - |
| `SECRET_KEY` | JWT密钥 | - |
| `AUTH_USERNAME` | API登录用户名 | - |
| `AUTH_PASSWORD` | API登录密码 | - |
| `CORS_ALLOWED_ORIGINS` | CORS允许来源，逗号分隔 | `http://localhost:3000,http://127.0.0.1:3000` |
| `PROXY_POOL_SIZE` | 代理池大小 | 5 |
| `REQUEST_INTERVAL` | 请求间隔（秒） | 2 |
| `MAX_RETRIES` | 失败重试次数 | 3 |

### 代理配置

项目使用自建代理池来规避IP封禁。代理列表可以通过以下方式配置：

1. **环境变量**：`PROXY_LIST`
2. **配置文件**：`config/proxies.txt`
3. **动态获取**：集成免费代理API（可选）

## 数据范围

- **股票范围**：全部非ST的A股股票（约4500只）
- **时间范围**：最近3年交易日数据
- **复权类型**：前复权
- **数据字段**：开盘价、最高价、最低价、收盘价、成交量、成交额

## 定时任务

系统配置了以下定时任务：

- **每日数据更新**：15:05自动执行
- **任务类型**：获取全市场股票日线数据
- **手动触发**：通过API端点手动触发

## 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_proxy_pool.py
pytest tests/test_api.py
```

## 部署

### Docker部署

```bash
# 构建镜像
docker build -t china-stock-proxy .

# 运行容器
docker-compose up -d
```

### 阿里云部署

1. 安装Docker和Docker Compose
2. 配置.env文件中的阿里云数据库连接
3. 运行`docker-compose up -d`启动所有服务
4. 配置Nginx反向代理（可选）

## 监控和日志

- **日志级别**：INFO（可通过环境变量调整）
- **日志位置**：控制台输出 + 文件（可选）
- **监控指标**：任务执行状态、代理成功率、API请求延迟

### 运行检查（建议）

```bash
# 1) 健康检查
curl -sS http://localhost:8000/health

# 2) 获取 token
TOKEN=$(curl -sS -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${AUTH_USERNAME}&password=${AUTH_PASSWORD}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3) 验证受保护接口
curl -sS -H "Authorization: Bearer ${TOKEN}" "http://localhost:8000/api/v1/stocks/daily?stock_code=000001&limit=20"

# 4) 验证监控指标
curl -sS http://localhost:8000/metrics
```

## 贡献指南

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 许可证

MIT License

## 联系方式

- 项目负责人：[您的姓名]
- 邮箱：[您的邮箱]
