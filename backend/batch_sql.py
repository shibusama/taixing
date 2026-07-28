"""
读取 SQL 文件，按批次输出可执行的 SQL 块
每批包含 BEGIN/COMMIT，约 20 条语句
"""
import sys

def split_sql_file(filepath):
    """读取 SQL 文件，分割成独立语句"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    statements = []
    current = []
    
    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('--'):
            continue
        current.append(line)
        if line.endswith(';'):
            statements.append(' '.join(current))
            current = []
    
    if current:
        statements.append(' '.join(current))
    
    return statements

def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else '/tmp/import_data.sql'
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    
    statements = split_sql_file(filepath)
    print(f"总共 {len(statements)} 条语句，每批 {batch_size} 条")
    
    for i in range(0, len(statements), batch_size):
        batch = statements[i:i+batch_size]
        batch_num = i // batch_size + 1
        print(f"\n-- Batch {batch_num} ({len(batch)} statements)")
        print("BEGIN;")
        for stmt in batch:
            print(stmt)
        print("COMMIT;")

if __name__ == "__main__":
    main()
