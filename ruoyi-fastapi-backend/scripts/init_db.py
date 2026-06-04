"""
启动时自动初始化数据库
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(str(ROOT))

from config.env import DataBaseConfig


def split_sql(sql_text):
    """智能分割 SQL 语句，处理引号内的分号"""
    statements = []
    current = ""
    in_string = False
    string_char = None
    i = 0
    while i < len(sql_text):
        ch = sql_text[i]
        if in_string:
            current += ch
            if ch == "\\" and i + 1 < len(sql_text):
                i += 1
                current += sql_text[i]
            elif ch == string_char:
                in_string = False
        elif ch in ("'", '"'):
            in_string = True
            string_char = ch
            current += ch
        elif ch == ";" and not in_string:
            stmt = current.strip()
            if stmt and not stmt.startswith("--"):
                statements.append(stmt)
            current = ""
        elif ch == "-" and sql_text[i:i+2] == "--":
            # 跳过行注释
            end = sql_text.find("\n", i)
            if end == -1:
                end = len(sql_text)
            i = end + 1
            continue
        else:
            current += ch
        i += 1
    stmt = current.strip()
    if stmt and not stmt.startswith("--"):
        statements.append(stmt)
    return statements


def init_database():
    """初始化数据库：建表 + 基础数据"""
    try:
        import pymysql
    except ImportError:
        print("⚠️  pymysql 未安装，跳过数据库初始化")
        return

    conn = pymysql.connect(
        host=DataBaseConfig.db_host,
        port=DataBaseConfig.db_port,
        user=DataBaseConfig.db_username,
        password=DataBaseConfig.db_password,
        database=DataBaseConfig.db_database,
        charset="utf8mb4",
    )
    cur = conn.cursor()

    # 检查是否已初始化（表不存在也视为未初始化）
    try:
        cur.execute("SELECT COUNT(*) FROM sys_menu")
        if cur.fetchone()[0] > 0:
            print("✅ 数据库已初始化，跳过")
            cur.close()
            conn.close()
            return
    except Exception:
        pass  # 表不存在，继续初始化

    print("🔄 数据库未初始化，开始执行 SQL 文件...")
    sql_dir = ROOT / "sql"
    sql_files = [
        "ruoyi-fastapi.sql",
        "eval_init.sql",
        "portal_init.sql",
        "seed_projects.sql",
    ]

    for fname in sql_files:
        fpath = sql_dir / fname
        if not fpath.exists():
            print(f"  ⚠️ 跳过（文件不存在）: {fname}")
            continue
        print(f"  📄 执行: {fname}")
        sql_text = fpath.read_text(encoding="utf-8")
        statements = split_sql(sql_text)
        success = 0
        failed = 0
        for stmt in statements:
            try:
                cur.execute(stmt)
                conn.commit()
                success += 1
            except Exception as e:
                err = str(e)
                if "already exists" in err or "Duplicate" in err or "Unknown table" in err:
                    conn.rollback()
                    success += 1  # 可重入，算成功
                else:
                    failed += 1
                    if failed <= 3:
                        print(f"    ⚠️ [{fname}] {err[:150]}")
                    conn.rollback()
        print(f"    ✅ {success} 条执行成功" + (f", ⚠️ {failed} 条跳过" if failed else ""))

    cur.close()
    conn.close()
    print("✅ 数据库初始化完成")

    cur.close()
    try:
        conn.close()
    except Exception:
        pass
    print("✅ 数据库初始化完成")


if __name__ == "__main__":
    init_database()
