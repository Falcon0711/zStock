"""
修复所有今日盘中获取的陈旧数据
"""
import sqlite3
from datetime import datetime

def fix_all_stale_data():
    db_path = "data/stock_data.db"
    today = datetime.now().strftime('%Y-%m-%d')
    market_close_time = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
    
    print(f"=== 修复陈旧数据 (日期: {today}) ===")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. 找出所有今天的数据
    cursor.execute("""
        SELECT s.code, s.close, l.updated_at
        FROM stock_history s
        JOIN sync_log l ON s.code = l.code
        WHERE s.date = ?
    """, (today,))
    
    rows = cursor.fetchall()
    print(f"找到 {len(rows)} 条今日数据")
    
    stale_count = 0
    for code, close_price, updated_at_str in rows:
        try:
            updated_at = datetime.strptime(updated_at_str, '%Y-%m-%d %H:%M:%S')
            # 如果更新时间早于15:00，认为是陈旧数据
            if updated_at < market_close_time:
                stale_count += 1
                print(f"  ❌ {code}: 收盘价={close_price}, 更新于 {updated_at_str} (盘中)")
                
                # 删除这条记录
                cursor.execute("DELETE FROM stock_history WHERE code = ? AND date = ?", (code, today))
        except:
            pass
    
    if stale_count > 0:
        conn.commit()
        print(f"\n✅ 已删除 {stale_count} 条陈旧记录。下次分析时会自动获取正确的收盘数据。")
    else:
        print("\n✅ 没有发现陈旧数据。")
    
    conn.close()

if __name__ == "__main__":
    fix_all_stale_data()
