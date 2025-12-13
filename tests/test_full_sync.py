
import sys
import os
sys.path.insert(0, os.getcwd())

from services.local_data_service import get_local_data_service
import logging

logging.basicConfig(level=logging.INFO)

def test_full_sync():
    service = get_local_data_service()
    
    # 选择一只可能未同步过的股票
    code = "601398"  # 工商银行
    
    print(f"--- Testing Full Sync for {code} ---")
    
    # 检查是否已完成全量同步
    completed = service.is_full_sync_completed(code)
    print(f"1. Full sync completed: {completed}")
    
    # 调用 get_stock_data_smart (会触发全量同步)
    print(f"\n2. Calling get_stock_data_smart({code})...")
    df = service.get_stock_data_smart(code, days=90)
    
    if df is not None:
        print(f"✅ Got {len(df)} rows")
        print(f"   Date range: {df['date'].min()} ~ {df['date'].max()}")
    else:
        print("❌ No data returned")
    
    # 再次检查是否已标记为完成
    completed_after = service.is_full_sync_completed(code)
    print(f"\n3. Full sync completed (after): {completed_after}")
    
    # 再次调用，应该不再触发全量同步
    print(f"\n4. Calling get_stock_data_smart again (should only do incremental)...")
    df2 = service.get_stock_data_smart(code, days=90)
    if df2 is not None:
        print(f"✅ Got {len(df2)} rows (from cache)")
    else:
        print("❌ No data")

if __name__ == "__main__":
    test_full_sync()
