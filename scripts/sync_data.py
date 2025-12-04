#!/usr/bin/env python
"""
A股数据同步脚本
用于定时更新本地股票历史数据

使用方式:
    # 同步所有股票（首次运行，耗时较长）
    python scripts/sync_data.py --all
    
    # 只同步用户自选股
    python scripts/sync_data.py --watchlist
    
    # 测试模式（只同步5只热门股）
    python scripts/sync_data.py --test
    
    # 同步指定股票
    python scripts/sync_data.py --codes 600519,000001,000858
"""

import sys
import os
import time
import argparse
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import akshare as ak
import pandas as pd
from services.local_data_service import get_local_data_service


def get_all_a_share_codes():
    """
    获取所有A股股票代码列表
    优先级: 东方财富 API -> 腾讯 API -> 本地缓存
    """
    codes = []
    
    # 方法1: 东方财富 API (AkShare 默认)
    try:
        print("📋 正在获取A股股票列表 (东方财富)...")
        df = ak.stock_zh_a_spot_em()
        codes = df['代码'].tolist()
        print(f"✅ 共获取 {len(codes)} 只股票 (东方财富)")
        # 保存到本地缓存
        save_stock_list_cache(codes)
        return codes
    except Exception as e:
        print(f"⚠️ 东方财富API失败: {e}")
    
    # 方法2: 腾讯 API
    try:
        print("📋 正在获取A股股票列表 (腾讯)...")
        import requests
        
        # 腾讯股票列表 API
        codes = []
        for market in ['sh', 'sz']:
            url = f"http://qt.gtimg.cn/q={market}"
            # 获取沪市和深市的股票列表
            # 使用腾讯行情 API 获取
            list_url = f"http://stock.gtimg.cn/data/index.php?appn=rank&t=rank{market}/chr&p=1&o=0&l=5000&v=list_data"
            resp = requests.get(list_url, timeout=10)
            if resp.status_code == 200:
                # 解析返回的数据
                text = resp.text
                # 格式: var list_data={data:"code1,code2,...",total:xxx}
                import re
                match = re.search(r'data:"([^"]+)"', text)
                if match:
                    stock_list = match.group(1).split(',')
                    for item in stock_list:
                        if item and len(item) >= 6:
                            code = item[:6]
                            if code.isdigit():
                                codes.append(code)
        
        if codes:
            codes = list(set(codes))  # 去重
            print(f"✅ 共获取 {len(codes)} 只股票 (腾讯)")
            save_stock_list_cache(codes)
            return codes
    except Exception as e:
        print(f"⚠️ 腾讯API失败: {e}")
    
    # 方法3: 从本地缓存读取
    try:
        print("📋 尝试从本地缓存读取股票列表...")
        codes = load_stock_list_cache()
        if codes:
            print(f"✅ 从缓存获取 {len(codes)} 只股票")
            return codes
    except Exception as e:
        print(f"⚠️ 读取缓存失败: {e}")
    
    print("❌ 所有获取股票列表的方法都失败了")
    return []


def save_stock_list_cache(codes: list):
    """保存股票列表到本地缓存"""
    try:
        import json
        cache_path = os.path.join(project_root, "data", "stock_list_cache.json")
        with open(cache_path, 'w') as f:
            json.dump({
                'codes': codes,
                'updated_at': datetime.now().isoformat(),
                'count': len(codes)
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ 保存缓存失败: {e}")


def load_stock_list_cache():
    """从本地缓存读取股票列表"""
    import json
    cache_path = os.path.join(project_root, "data", "stock_list_cache.json")
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            data = json.load(f)
            # 如果缓存是新格式（包含 codes 字段）
            if 'codes' in data:
                return data['codes']
            # 兼容旧格式（直接是列表或字典列表）
            elif isinstance(data, list):
                if data and isinstance(data[0], dict):
                    return [item.get('code', item.get('symbol', '')) for item in data]
                return data
    return []


def get_watchlist_codes():
    """获取用户自选股列表"""
    try:
        import json
        watchlist_path = os.path.join(project_root, "data", "user_stocks.json")
        if os.path.exists(watchlist_path):
            with open(watchlist_path, 'r') as f:
                data = json.load(f)
                codes = [item['code'] for item in data.get('stocks', [])]
                print(f"📋 自选股: {len(codes)} 只")
                return codes
    except Exception as e:
        print(f"⚠️ 读取自选股失败: {e}")
    return []


def get_hot_stock_codes():
    """获取热门股票（用于测试）"""
    return ['600519', '000001', '000858', '601398', '002594']


def fetch_from_tencent(code: str, start_date: str = "", days: int = 3650):
    """
    从腾讯 API 获取股票历史数据
    
    Args:
        code: 股票代码
        start_date: 开始日期 YYYYMMDD (可选)
        days: 历史天数
    
    Returns:
        DataFrame or None
    """
    import requests
    import re
    
    try:
        # 腾讯股票代码格式: sh600519 或 sz000001
        if code.startswith('6'):
            tc_code = f"sh{code}"
        else:
            tc_code = f"sz{code}"
        
        # 腾讯日K线 API - 使用正确的格式
        # 参数: 股票代码,周期,开始日期,结束日期,数量,复权类型
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayqfq&param={tc_code},day,,,{min(days, 800)},qfq"
        resp = requests.get(url, timeout=15)
        
        if resp.status_code != 200:
            return None
        
        # 响应格式: kline_dayqfq={...}
        text = resp.text
        json_match = re.search(r'=(\{.*\})', text)
        if not json_match:
            return None
        
        import json
        data = json.loads(json_match.group(1))
        
        if data.get('code') != 0:
            return None
        
        # 提取K线数据
        stock_data = data.get('data', {}).get(tc_code, {})
        day_data = stock_data.get('qfqday') or stock_data.get('day')
        
        if not day_data:
            return None
        
        # 腾讯格式可能有 6 或 7 列，动态处理
        # 6列: [日期, 开盘, 收盘, 最高, 最低, 成交量]
        # 7列: [日期, 开盘, 收盘, 最高, 最低, 成交量, 其他]
        rows = []
        for item in day_data:
            if len(item) >= 6:
                rows.append({
                    'date': item[0],
                    'open': float(item[1]),
                    'close': float(item[2]),
                    'high': float(item[3]),
                    'low': float(item[4]),
                    'volume': float(item[5])
                })
        
        if not rows:
            return None
        
        df = pd.DataFrame(rows)
        
        # 如果指定了开始日期，过滤数据
        if start_date:
            start_dt = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
            df = df[df['date'] >= start_dt]
        
        return df
    except Exception as e:
        return None


def sync_stock_data(code: str, local_service, days: int = 3650, max_retries: int = 3):
    """
    同步单只股票的历史数据（增量更新）
    支持多数据源和重试机制
    
    Args:
        code: 股票代码
        local_service: 本地数据服务实例
        days: 历史数据天数（默认10年）
        max_retries: 最大重试次数
    
    Returns:
        (success: bool, new_records: int)
    """
    try:
        # 检查本地最后更新日期
        last_date = local_service.get_last_data_date(code)
        
        if last_date:
            # 增量更新：从最后日期的下一天开始
            start_date = (datetime.strptime(last_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y%m%d')
            today = datetime.now().strftime('%Y%m%d')
            
            if start_date >= today:
                return True, 0  # 静默跳过，不打印
        else:
            # 全量同步：获取指定天数的历史
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        df = None
        
        # 方法1: AkShare (东方财富) - 带重试
        for attempt in range(max_retries):
            try:
                time.sleep(0.2 + attempt * 0.3)  # 递增延迟
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    adjust="qfq"
                )
                if df is not None and not df.empty:
                    # 列名映射
                    column_mapping = {
                        '日期': 'date',
                        '开盘': 'open',
                        '最高': 'high',
                        '最低': 'low',
                        '收盘': 'close',
                        '成交量': 'volume'
                    }
                    df = df.rename(columns=column_mapping)
                    break
            except Exception:
                if attempt < max_retries - 1:
                    continue
        
        # 方法2: 腾讯 API (备选)
        if df is None or df.empty:
            df = fetch_from_tencent(code, start_date, days)
        
        if df is None or df.empty:
            return True, 0  # 无新数据
        
        # 保存到本地
        new_records = local_service.save_stock_data(code, df)
        return True, new_records
        
    except Exception as e:
        print(f"❌ {code}: 同步失败 - {e}")
        return False, 0


def sync_stocks(codes: list, local_service):
    """
    批量同步股票数据
    
    Args:
        codes: 股票代码列表
        local_service: 本地数据服务实例
    """
    total = len(codes)
    success_count = 0
    fail_count = 0
    total_new_records = 0
    
    print(f"\n🚀 开始同步 {total} 只股票...")
    print("=" * 50)
    
    start_time = time.time()
    
    for i, code in enumerate(codes, 1):
        success, new_records = sync_stock_data(code, local_service)
        
        if success:
            success_count += 1
            total_new_records += new_records
        else:
            fail_count += 1
        
        # 每 50 只显示进度
        if i % 50 == 0 or i == total:
            elapsed = time.time() - start_time
            eta = (elapsed / i) * (total - i)
            print(f"📊 进度: {i}/{total} ({i/total*100:.1f}%) | "
                  f"成功: {success_count} | 失败: {fail_count} | "
                  f"预计剩余: {eta/60:.1f}分钟")
    
    print("=" * 50)
    print(f"✅ 同步完成!")
    print(f"   - 成功: {success_count} 只")
    print(f"   - 失败: {fail_count} 只")
    print(f"   - 新增记录: {total_new_records} 条")
    print(f"   - 耗时: {(time.time() - start_time)/60:.1f} 分钟")
    
    # 显示数据库统计
    stats = local_service.get_stats()
    print(f"\n📁 数据库状态:")
    print(f"   - 股票数量: {stats['total_stocks']} 只")
    print(f"   - 总记录数: {stats['total_records']} 条")
    print(f"   - 数据库大小: {stats['db_size_mb']} MB")


def main():
    parser = argparse.ArgumentParser(description='A股数据同步工具')
    parser.add_argument('--all', action='store_true', help='同步所有A股')
    parser.add_argument('--watchlist', action='store_true', help='只同步自选股')
    parser.add_argument('--test', action='store_true', help='测试模式（5只热门股）')
    parser.add_argument('--codes', type=str, help='指定股票代码，逗号分隔')
    
    args = parser.parse_args()
    
    # 获取本地数据服务
    local_service = get_local_data_service()
    
    # 确定要同步的股票列表
    if args.codes:
        codes = [c.strip() for c in args.codes.split(',')]
        print(f"📋 同步指定股票: {codes}")
    elif args.test:
        codes = get_hot_stock_codes()
        print(f"🧪 测试模式: 同步 {len(codes)} 只热门股")
    elif args.watchlist:
        codes = get_watchlist_codes()
        if not codes:
            print("⚠️ 自选股为空，使用热门股代替")
            codes = get_hot_stock_codes()
    elif args.all:
        codes = get_all_a_share_codes()
    else:
        # 默认：同步自选股 + 热门股
        codes = list(set(get_watchlist_codes() + get_hot_stock_codes()))
        print(f"📋 默认模式: 同步自选股 + 热门股 ({len(codes)} 只)")
    
    if not codes:
        print("❌ 没有要同步的股票")
        return
    
    # 开始同步
    sync_stocks(codes, local_service)


if __name__ == "__main__":
    main()
