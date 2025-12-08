#!/usr/bin/env python
# coding: utf-8
"""
港股和外汇功能测试脚本

测试 HKQuotationService 和 ExchangeRateService 的核心功能
"""

import sys
import os

# 添加项目根路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_hk_quotation_service():
    """测试港股行情服务"""
    print("\n" + "=" * 60)
    print("【测试1】HKQuotationService - 港股实时行情")
    print("=" * 60)
    
    from services.hk_quotation_service import HKQuotationService
    
    service = HKQuotationService()
    
    # 测试单只港股
    print("\n1.1 获取单只港股 (00700 腾讯控股):")
    data = service.get_stock_detail('00700')
    if data:
        print(f"   名称: {data.get('name')}")
        print(f"   价格: {data.get('price')}")
        print(f"   涨跌幅: {data.get('change_pct')}%")
        print(f"   成交量: {data.get('volume')}")
        print(f"   总市值: {data.get('market_cap')}")
        print("   ✅ 单只港股测试通过")
    else:
        print("   ⚠️ 获取数据失败（可能是非交易时段）")
    
    # 测试多只港股
    print("\n1.2 获取多只港股 (00700, 00941, 09988):")
    stocks = ['00700', '00941', '09988']
    data = service.get_realtime(stocks)
    if data:
        for code, quote in data.items():
            name = quote.get('name', '未知')
            price = quote.get('price', 0)
            print(f"   {name} ({code}): HK${price}")
        print(f"   ✅ 多只港股测试通过，共获取 {len(data)} 只")
    else:
        print(" ⚠️ 获取数据失败")
    
    # 测试不同格式的代码
    print("\n1.3 测试不同格式的港股代码:")
    test_codes = ['700', '00700', 'hk00700', 'HK00700']
    for code in test_codes:
        data = service.get_stock_detail(code)
        if data:
            print(f"   {code} -> {data.get('code')}: ✅")
        else:
            print(f"   {code} -> 失败: ⚠️")
    
    return True


def test_hk_kline_service():
    """测试港股K线服务"""
    print("\n" + "=" * 60)
    print("【测试3】HKDayKlineService - 港股历史K线")
    print("=" * 60)
    
    from services.hk_kline_service import HKDayKlineService
    
    service = HKDayKlineService()
    
    print("\n3.1 获取港股日K线 (00700 腾讯控股, 最近30天):")
    klines = service.get_day_kline('00700', days=30)
    if klines:
        print(f"   获取到 {len(klines)} 根K线")
        if len(klines) > 0:
            latest = klines[-1]
            print(f"   最新日期: {latest['date']}")
            print(f"   收盘价: {latest['close']}")
            print(f"   成交量: {latest['volume']}")
        print("   ✅ 港股K线测试通过")
    else:
        print("   ⚠️ 获取数据失败")
    
    print("\n3.2 测试不同天数参数:")
    for days in [7, 30, 90]:
        klines = service.get_day_kline('00700', days=days)
        if klines:
            print(f"   {days}天: 获取 {len(klines)} 根K线 ✅")
        else:
            print(f"   {days}天: 失败 ⚠️")
    
    return True


def test_exchange_rate_service():
    """测试外汇服务"""
    print("\n" + "=" * 60)
    print("【测试2】ExchangeRateService - 中行外汇牌价")
    print("=" * 60)
    
    from services.exchange_rate_service import ExchangeRateService
    
    service = ExchangeRateService()
    
    print("\n2.1 获取美元汇率:")
    rate = service.get_exchange_rate("USD")
    if rate:
        print(f"   货币: {rate.get('currency')}")
        print(f"   买入价: {rate.get('buy_price')}")
        print(f"   卖出价: {rate.get('sell_price')}")
        print(f"   中间价: {rate.get('middle_price')}")
        print(f"   更新时间: {rate.get('update_time')}")
        print("   ✅ 美元汇率测试通过")
    else:
        print("   ⚠️ 获取数据失败")
    
    print("\n2.2 获取所有汇率:")
    rates = service.get_all_rates()
    if rates:
        for currency, data in rates.items():
            print(f"   {currency}: {data.get('middle_price')}")
        print(f"   ✅ 获取所有汇率测试通过，共 {len(rates)} 种货币")
    else:
        print("   ⚠️ 获取数据失败")
    
    # 测试缓存
    print("\n2.3 测试缓存机制:")
    import time
    start = time.time()
    rate1 = service.get_exchange_rate("USD")
    time1 = time.time() - start
    
    start = time.time()
    rate2 = service.get_exchange_rate("USD")
    time2 = time.time() - start
    
    print(f"   第一次请求耗时: {time1:.3f}秒")
    print(f"   第二次请求耗时: {time2:.3f}秒 (应该更快，使用缓存)")
    if time2 < time1:
        print("   ✅ 缓存机制工作正常")
    else:
        print("   ⚠️ 缓存可能未生效")
    
    return True


def main():
    print("*" * 60)
    print("*  港股和外汇功能测试                                    *")
    print("*" * 60)
    
    try:
        test_hk_quotation_service()
        test_hk_kline_service()
        test_exchange_rate_service()
        
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
