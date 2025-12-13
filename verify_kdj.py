from analyzers.stock_analyzer import StockAnalyzer
import pandas as pd

try:
    analyzer = StockAnalyzer()
    # Mock data or fetch real data
    # Let's try to fetch real data for 600030 (CITIC Securities) as seen in user screenshot
    code = "600030" 
    print(f"Analyzing {code}...")
    result = analyzer.analyze_stock(code, use_cache=False)
    
    print(f"KDJ K: {result.get('kdj_k')}")
    print(f"KDJ D: {result.get('kdj_d')}")
    print(f"KDJ J: {result.get('kdj_j')}")
    
    if result.get('kdj_j') == 0 and result.get('kdj_k') != 0:
        print("ERROR: KDJ J is 0 but K is not!")
    else:
        print("SUCCESS: KDJ J value is present.")

except Exception as e:
    print(f"Error: {e}")
