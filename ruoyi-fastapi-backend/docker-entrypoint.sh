#!/bin/bash
# ============================================
# Docker 启动脚本
# 1. 初始化数据库（首次启动时）
# 2. 启动应用
# ============================================
set -e

echo "========================================="
echo " RuoYi-Bid-Eval 启动中..."
echo "========================================="

# 等待 MySQL 就绪
echo "⏳ 等待 MySQL..."
python -c "
import pymysql, time, os
host = os.environ.get('DB_HOST', 'mysql')
port = int(os.environ.get('DB_PORT', 3306))
user = os.environ.get('DB_USERNAME', 'root')
pwd = os.environ.get('DB_PASSWORD', 'mysqlroot')
db = os.environ.get('DB_DATABASE', 'bid_eval_v2')
for i in range(30):
    try:
        conn = pymysql.connect(host=host, port=port, user=user, password=pwd, database=db, charset='utf8mb4')
        conn.close()
        print('✅ MySQL 就绪')
        break
    except Exception as e:
        if i < 29:
            time.sleep(2)
        else:
            print(f'❌ MySQL 连接失败: {e}')
            exit(1)
"

# 初始化数据库（使用 uv run 确保依赖可用）
echo "🔄 初始化数据库..."
uv run python scripts/init_db.py

# 启动应用
echo "🚀 启动应用..."
exec uv run python app.py
