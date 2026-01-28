# Learnings - China Stock Proxy

## 2026-01-28

### Task 1: 项目初始化
- Created Python virtual environment structure
- Set up dependency management with requirements.txt
- Established project directory structure

### Task 2: 代理池实现
- Implemented proxy rotation mechanism
- Added User-Agent randomization
- Configured frequency control (2 seconds per request)

### Task 3: 数据库设计
- Designed PostgreSQL + TimescaleDB schema
- Created time-series tables for financial data

## Key Decisions
- Stock scope: All non-ST A-share stocks (~4500)
- Data range: 3 years, forward-adjusted prices
- Server: Aliyun 4CPU/8GB
- Auth: Bearer Token (JWT)

## Architecture Notes
- Backend: Python + FastAPI
- Database: PostgreSQL + TimescaleDB
- Task Queue: Celery + Redis
- Proxy: requests + rotation pool
