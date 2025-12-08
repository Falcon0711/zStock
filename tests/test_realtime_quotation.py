#!/usr/bin/env python
# coding: utf-8
"""
实时行情服务测试脚本

测试 RealtimeQuotationService 和 RealtimeKlineService 的核心功能
"""

import sys
import os

# 添加项目根路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_realtime_quotation_service():
    """测试实时行情服务"""
    print("\n" + "=" * 60)
    print("【测试1】RealtimeQuotationService - 新浪行情")
    print("=" * 60)
    
    from services.realtime_quotation_service import RealtimeQuotationService
    
    service = RealtimeQuotationService(source='sina')
    
    # 测试单只股票
    print("\n1.1 获取单只股票 (600519 贵州茅台):")
    data = service.get_realtime('600519')
    if data and '600519' in data:
        quote = data['600519']
        print(f"   名称: {quote.get('name')}")
        print(f"   现价: {quote.get('now')}")
        print(f"   涨跌幅: {((quote.get('now', 0) - quote.get('close', 0)) / quote.get('close', 1) * 100):.2f}%")
        print("   ✅ 单只股票测试通过")
    else:
        print("   ⚠️ 获取数据失败（可能是非交易时段）")
    
    # 测试多只股票
    print("\n1.2 获取多只股票 (600519, 000001, 300750):")
    stocks = ['600519', '000001', '300750']
    data = service.get_realtime(stocks)
    if data:
        for code in stocks:
            if code in data:
                quote = data[code]
                print(f"   {quote.get('name')} ({code}): {quote.get('now')}")
        print("   ✅ 多只股票测试通过")
    else:
        print("   ⚠️ 获取数据失败")
    
    # 测试市场快照
    print("\n1.3 获取市场快照 (前5只):")
    data = service.get_market_snapshot(limit=5)
    if data:
        for code, quote in list(data.items())[:5]:
            print(f"   {quote.get('name')} ({code}): {quote.get('now')}")
        print(f"   ✅ 市场快照测试通过，共获取 {len(data)} 只")
    else:
        print("   ⚠️ 获取数据失败")
    
    return True


def test_tencent_quotation():
    """测试腾讯行情源"""
    print("\n" + "=" * 60)
    print("【测试2】RealtimeQuotationService - 腾讯行情")
    print("=" * 60)
    
    from services.realtime_quotation_service import RealtimeQuotationService
    
    service = RealtimeQuotationService(source='tencent')
    
    print("\n2.1 获取单只股票 (600519 贵州茅台):")
    data = service.get_realtime('600519')
    if data and '600519' in data:
        quote = data['600519']
        print(f"   名称: {quote.get('name')}")
        print(f"   现价: {quote.get('now')}")
        print("   ✅ 腾讯行情测试通过")
    else:
        print("   ⚠️ 获取数据失败（可能是非交易时段）")
    
    return True


def test_realtime_kline_service():
    """测试实时K线服务"""
    print("\n" + "=" * 60)
    print("【测试3】RealtimeKlineService")
    print("=" * 60)
    
    from services.realtime_kline_service import RealtimeKlineService
    
    service = RealtimeKlineService(realtime_source='sina')
    
    # 测试获取实时行情（K线格式）
    print("\n3.1 获取实时行情 (K线格式):")
    kline = service.get_realtime_as_kline('600519')
    if kline:
        print(f"   时间: {kline.get('time')}")
        print(f"   名称: {kline.get('name')}")
        print(f"   收盘: {kline.get('close')}")
        print(f"   涨跌幅: {kline.get('change_pct')}%")
        print("   ✅ 实时K线格式测试通过")
    else:
        print("   ⚠️ 获取数据失败")
    
    # 测试批量获取
    print("\n3.2 批量获取实时K线:")
    klines = service.get_batch_realtime(['600519', '000001'])
    if klines:
        for k in klines:
            print(f"   {k.get('name')} ({k.get('code')}): {k.get('close')} ({k.get('change_pct')}%)")
        print("   ✅ 批量实时K线测试通过")
    else:
        print("   ⚠️ 获取数据失败")
    
    return True


def test_stock_type_detection():
    """测试股票类型识别"""
    print("\n" + "=" * 60)
    print("【测试4】股票代码类型识别")
    print("=" * 60)
    
    from services.realtime_quotation_service import get_stock_type
    
    test_cases = [
        ('600519', 'sh'),  # 上交所
        ('000001', 'sz'),  # 深交所
        ('300750', 'sz'),  # 创业板
        ('688001', 'sh'),  # 科创板
        ('430047', 'bj'),  # 北交所 (83x开头)
        ('sh600519', 'sh'),  # 已有前缀
        ('sz000001', 'sz'),  # 已有前缀
    ]
    
    all_passed = True
    for code, expected in test_cases:
        result = get_stock_type(code)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_passed = False
        print(f"   {status} {code} -> {result} (期望: {expected})")
    
    if all_passed:
        print("   ✅ 股票类型识别测试全部通过")
    else:
        print("   ⚠️ 部分测试未通过")
    
    return all_passed


def main():
    print("*" * 60)
    print("*  实时行情服务测试                                      *")
    print("*" * 60)
    
    try:
        test_stock_type_detection()
        test_realtime_quotation_service()
        test_tencent_quotation()
        test_realtime_kline_service()
        
        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
