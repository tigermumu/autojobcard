import sqlite3

conn = sqlite3.connect('aircraft_workcard.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(import_batch_items)")
cols = cursor.fetchall()

print('import_batch_items 表的 workcard_number 字段信息:')
for col in cols:
    if col[1] == 'workcard_number':
        print(f'字段名: {col[1]}')
        print(f'类型: {col[2]}')
        print(f'NOT NULL: {col[3]} (False表示可空, True表示必填)')
        print(f'可空: {not col[3]}')

conn.close()



















