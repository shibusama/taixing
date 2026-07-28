#!/usr/bin/env python3
"""从 SQLite 导出数据并导入到 Supabase"""

import sqlite3
import json
import os
import sys

def get_supabase_client():
    """获取 Supabase 客户端"""
    try:
        from supabase import create_client, Client
        url = os.environ.get('COZE_SUPABASE_URL')
        key = os.environ.get('COZE_SUPABASE_ANON_KEY')
        if not url or not key:
            print("错误：未配置 COZE_SUPABASE_URL 或 COZE_SUPABASE_ANON_KEY")
            return None
        return create_client(url, key)
    except ImportError:
        print("错误：未安装 supabase 库，请运行 pip install supabase")
        return None

def export_sqlite(db_path='data/taixing_v2.db'):
    """导出 SQLite 数据"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'")
    tables = [t[0] for t in cursor.fetchall()]
    
    all_data = {}
    for table in tables:
        cursor.execute(f'SELECT * FROM {table}')
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        data = []
        for row in rows:
            data.append(dict(zip(columns, row)))
        
        all_data[table] = data
        print(f'{table}: {len(data)} 条')
    
    conn.close()
    return all_data

def import_to_supabase(supabase, data):
    """导入数据到 Supabase"""
    for table, rows in data.items():
        if not rows:
            continue
        
        try:
            # 批量插入
            response = supabase.table(table).insert(rows).execute()
            print(f'{table}: 导入成功 {len(rows)} 条')
        except Exception as e:
            print(f'{table}: 导入失败 - {e}')

def main():
    print("=== 导出 SQLite 数据 ===")
    data = export_sqlite()
    
    print("\n=== 导入到 Supabase ===")
    supabase = get_supabase_client()
    if not supabase:
        sys.exit(1)
    
    import_to_supabase(supabase, data)
    print("\n完成！")

if __name__ == '__main__':
    main()
