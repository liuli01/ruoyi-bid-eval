"""修复 sys_user 表中用户昵称乱码"""
import subprocess

CP1252_BYTE_MAP = {
    '\u20AC': 0x80, '\u201A': 0x82, '\u0192': 0x83, '\u201E': 0x84,
    '\u2026': 0x85, '\u2020': 0x86, '\u2021': 0x87, '\u02C6': 0x88,
    '\u2030': 0x89, '\u0160': 0x8A, '\u2039': 0x8B, '\u0152': 0x8C,
    '\u017D': 0x8E, '\u2018': 0x91, '\u2019': 0x92, '\u201C': 0x93,
    '\u201D': 0x94, '\u2022': 0x95, '\u2013': 0x96, '\u2014': 0x97,
    '\u02DC': 0x98, '\u2122': 0x99, '\u0161': 0x9A, '\u203A': 0x9B,
    '\u0153': 0x9C, '\u017E': 0x9E, '\u0178': 0x9F,
}

def cp1252_fix_encode(text):
    result = bytearray()
    for ch in text:
        cp = ord(ch)
        if cp <= 0xFF:
            result.append(cp)
        elif ch in CP1252_BYTE_MAP:
            result.append(CP1252_BYTE_MAP[ch])
        else:
            raise ValueError(f"Cannot map U+{cp:04X}")
    return bytes(result)

def fix_text(val):
    if not val or not isinstance(val, str):
        return None
    if any('\u4e00' <= c <= '\u9fff' for c in val):
        return None
    try:
        raw_bytes = cp1252_fix_encode(val)
        fixed = raw_bytes.decode('utf-8')
        return fixed if fixed != val else None
    except:
        return None

# 读取 sys_user
result = subprocess.run(
    ['docker', 'exec', '-i', 'mysql-bid-eval',
     'mysql', '-uroot', '-pmysqlroot', 'bid_eval_v2',
     '--default-character-set=utf8',
     '-e', "SELECT user_id, user_name, nick_name FROM sys_user ORDER BY user_id"],
    capture_output=True, text=True
)

fixes = []
lines = result.stdout.strip().split('\n')[1:]
for line in lines:
    parts = line.strip().split('\t')
    if len(parts) >= 3:
        uid = parts[0]
        uname = parts[1]
        nname = parts[2] if len(parts) > 2 else ''
        
        fixed_uname = fix_text(uname)
        fixed_nname = fix_text(nname)
        
        if fixed_uname:
            fixes.append((uid, 'user_name', fixed_uname))
        if fixed_nname:
            fixes.append((uid, 'nick_name', fixed_nname))

# 读取 sys_dept
result2 = subprocess.run(
    ['docker', 'exec', '-i', 'mysql-bid-eval',
     'mysql', '-uroot', '-pmysqlroot', 'bid_eval_v2',
     '--default-character-set=utf8',
     '-e', "SELECT dept_id, dept_name, leader FROM sys_dept ORDER BY dept_id"],
    capture_output=True, text=True
)

lines2 = result2.stdout.strip().split('\n')[1:]
for line in lines2:
    parts = line.strip().split('\t')
    if len(parts) >= 3:
        did = parts[0]
        dname = parts[1]
        leader = parts[2] if len(parts) > 2 else ''
        
        fixed_dname = fix_text(dname)
        fixed_leader = fix_text(leader)
        
        if fixed_dname:
            fixes.append((did, 'dept_name', fixed_dname))
        if fixed_leader:
            fixes.append((did, 'leader', fixed_leader))

if fixes:
    print(f"发现 {len(fixes)} 条需要修复的数据：")
    sql_parts = []
    for pk, col, fixed in fixes:
        escaped = fixed.replace("'", "''")
        table = 'sys_user' if pk.isdigit() and int(pk) < 1000 else 'sys_dept'
        if table == 'sys_dept':
            table = 'sys_dept'
            pk_col = 'dept_id'
        else:
            pk_col = 'user_id'
        sql_parts.append(f"UPDATE {table} SET {col} = '{escaped}' WHERE {pk_col} = {pk};")
        print(f"  {table}.{col} (id={pk}): -> {fixed}")
    
    sql = '\n'.join(sql_parts)
    print(f"\n执行 SQL...")
    exec_result = subprocess.run(
        ['docker', 'exec', '-i', 'mysql-bid-eval',
         'mysql', '-uroot', '-pmysqlroot', 'bid_eval_v2',
         '--default-character-set=utf8'],
        input=sql, capture_output=True, text=True, encoding='utf-8'
    )
    if exec_result.stderr:
        err = exec_result.stderr.replace('mysql: [Warning]', '').strip()
        if err:
            print(f"错误: {err[:300]}")
    print("完成!")
else:
    print("没有需要修复的数据")
