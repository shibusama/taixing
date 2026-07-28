"""
读取 SQL 文件，按批次生成独立的 SQL 文件
"""
import sys
import os

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
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '/tmp/sql_batches'
    batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    
    os.makedirs(output_dir, exist_ok=True)
    
    statements = split_sql_file(filepath)
    print(f"总共 {len(statements)} 条语句，每批 {batch_size} 条")
    
    for i in range(0, len(statements), batch_size):
        batch = statements[i:i+batch_size]
        batch_num = i // batch_size + 1
        output_file = os.path.join(output_dir, f"batch_{batch_num:02d}.sql")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("BEGIN;\n")
            for stmt in batch:
                f.write(stmt + "\n")
            f.write("COMMIT;\n")
        
        print(f"  Batch {batch_num:02d}: {output_file} ({len(batch)} statements)")

if __name__ == "__main__":
    main()
