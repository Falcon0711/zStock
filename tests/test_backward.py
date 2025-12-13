
import sys
import os
sys.path.insert(0, os.getcwd())

from services.local_data_service import get_local_data_service
import logging

logging.basicConfig(level=logging.INFO)

def test_backward_sync():
    service = get_local_data_service()
    
    # 选择一只已有部分数据的股票
    code = "600519"  # 茅台（假设之前已有数据）
    
    print(f"--- Testing Backward Sync for {code} ---")
    
    # 查看当前状态
    first_date = service.get_first_data_date(code)
    last_date = service.get_last_data_date(code)
    print(f"1. Current data range: {first_date} ~ {last_date}")
    
    # 第一次调用
    print(f"\n2. First call to get_stock_data_smart...")
    df1 = service.get_stock_data_smart(code, days=90)
    
    first_date_after1 = service.get_first_data_date(code)
    print(f"   After 1st call: earliest date = {first_date_after1}")
    
    # 第二次调用（应该继续向前补全）
    print(f"\n3. Second call to get_stock_data_smart...")
    df2 = service.get_stock_data_smart(code, days=90)
    
    first_date_after2 = service.get_first_data_date(code)
    print(f"   After 2nd call: earliest date = {first_date_after2}")
    
    # 第三次调用
    print(f"\n4. Third call to get_stock_data_smart...")
    df3 = service.get_stock_data_smart(code, days=90)
    
    first_date_after3 = service.get_first_data_date(code)
    print(f"   After 3rd call: earliest date = {first_date_after3}")
    
    print("\n--- Summary ---")
    print(f"Initial earliest: {first_date}")
    print(f"After 3 calls:    {first_date_after3}")
    
    if first_date_after3 < first_date:
        print("✅ SUCCESS: Data is being progressively extended backward!")
    else:
        print("ℹ️ No change (may have reached earliest available data)")

if __name__ == "__main__":
    test_backward_sync()
