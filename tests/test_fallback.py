"""
fallback 模块单元测试
测试容灾执行器和重试装饰器
"""

import pytest
import time
from typing import Optional
from services.fallback import FallbackExecutor, with_retry, rate_limited


class TestFallbackExecutor:
    """测试 FallbackExecutor 类"""
    
    def test_first_source_success(self):
        """第一个数据源成功"""
        def source1():
            return "data_from_source1"
        
        def source2():
            return "data_from_source2"
        
        executor = FallbackExecutor(
            providers=[source1, source2],
            names=["source1", "source2"]
        )
        
        result = executor.execute()
        assert result == "data_from_source1"
    
    def test_fallback_to_second(self):
        """第一个失败，降级到第二个"""
        def source1():
            raise Exception("source1 failed")
        
        def source2():
            return "data_from_source2"
        
        executor = FallbackExecutor(
            providers=[source1, source2],
            names=["source1", "source2"]
        )
        
        result = executor.execute()
        assert result == "data_from_source2"
    
    def test_all_sources_fail(self):
        """所有数据源都失败"""
        def source1():
            raise Exception("source1 failed")
        
        def source2():
            raise Exception("source2 failed")
        
        executor = FallbackExecutor(
            providers=[source1, source2],
            names=["source1", "source2"]
        )
        
        result = executor.execute()
        assert result is None
    
    def test_empty_result_skipped(self):
        """空结果被跳过"""
        def source1():
            return None  # 返回 None，视为失败
        
        def source2():
            return "valid_data"
        
        executor = FallbackExecutor(
            providers=[source1, source2],
            names=["source1", "source2"]
        )
        
        result = executor.execute()
        assert result == "valid_data"


class TestWithRetry:
    """测试 with_retry 装饰器"""
    
    def test_success_no_retry(self):
        """成功时不重试"""
        call_count = 0
        
        @with_retry(max_retries=3, delay=0.01)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = success_func()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_failure(self):
        """失败时重试"""
        call_count = 0
        
        @with_retry(max_retries=3, delay=0.01)
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("fail")
            return "success_after_retry"
        
        result = fail_twice()
        assert result == "success_after_retry"
        assert call_count == 3
    
    def test_max_retries_exceeded(self):
        """超过最大重试次数"""
        call_count = 0
        
        @with_retry(max_retries=2, delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise Exception("always fail")
        
        result = always_fail()
        assert result is None
        assert call_count == 3  # 1 + 2 retries


class TestRateLimited:
    """测试 rate_limited 装饰器"""
    
    def test_rate_limit_delay(self):
        """限流延迟"""
        @rate_limited(delay=0.1)
        def quick_func():
            return time.time()
        
        start = time.time()
        quick_func()
        quick_func()
        end = time.time()
        
        # 两次调用应该至少间隔 0.1 秒
        assert end - start >= 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
