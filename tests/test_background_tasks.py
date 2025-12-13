"""
后台任务队列单元测试
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch


class TestBackgroundTaskQueue:
    """后台任务队列测试"""
    
    def test_queue_creation(self):
        """测试队列创建"""
        from services.background_tasks import BackgroundTaskQueue, TaskPriority
        
        queue = BackgroundTaskQueue(num_workers=1)
        
        assert queue._num_workers == 1
        assert queue.queue_size == 0
        assert len(queue._workers) == 1
        
        queue.shutdown()
    
    def test_task_submission(self):
        """测试任务提交"""
        from services.background_tasks import BackgroundTaskQueue, TaskPriority
        
        queue = BackgroundTaskQueue(num_workers=1)
        result = []
        
        def task():
            result.append(1)
        
        queue.submit(task, task_name="test-task")
        queue.wait_completion()
        
        assert len(result) == 1
        queue.shutdown()
    
    def test_task_deduplication(self):
        """测试任务去重"""
        from services.background_tasks import BackgroundTaskQueue, TaskPriority
        
        queue = BackgroundTaskQueue(num_workers=1)
        counter = [0]
        
        def slow_task():
            time.sleep(0.2)
            counter[0] += 1
        
        # 提交相同任务 3 次
        queue.submit(slow_task, task_name="same-task")
        queue.submit(slow_task, task_name="same-task")  # 应该被跳过
        queue.submit(slow_task, task_name="same-task")  # 应该被跳过
        
        queue.wait_completion()
        
        # 应该只执行 1 次
        assert counter[0] == 1
        queue.shutdown()
    
    def test_priority_ordering(self):
        """测试优先级排序"""
        from services.background_tasks import BackgroundTaskQueue, TaskPriority
        
        queue = BackgroundTaskQueue(num_workers=1)
        execution_order = []
        
        def task(name):
            execution_order.append(name)
        
        # 先提交低优先级，再提交高优先级
        queue.submit(lambda: task("low"), task_name="low", priority=TaskPriority.LOW)
        queue.submit(lambda: task("high"), task_name="high", priority=TaskPriority.HIGH)
        queue.submit(lambda: task("normal"), task_name="normal", priority=TaskPriority.NORMAL)
        
        queue.wait_completion()
        
        # 高优先级应该先执行
        assert execution_order[0] == "high"
        assert execution_order[1] == "normal"
        assert execution_order[2] == "low"
        
        queue.shutdown()
    
    def test_stats(self):
        """测试统计信息"""
        from services.background_tasks import BackgroundTaskQueue
        
        queue = BackgroundTaskQueue(num_workers=1)
        
        queue.submit(lambda: None, task_name="task1")
        queue.submit(lambda: 1/0, task_name="task2-will-fail")  # 会失败
        
        queue.wait_completion()
        
        stats = queue.stats
        assert stats["completed"] >= 1
        assert stats["failed"] >= 1
        
        queue.shutdown()


class TestDataFetcher:
    """数据获取模块测试"""
    
    def test_get_stock_data_function_exists(self):
        """测试函数存在"""
        from analyzers.data_fetcher import get_stock_data
        
        assert callable(get_stock_data)
    
    def test_get_stock_data_with_mock(self):
        """测试 get_stock_data（使用 mock）"""
        import pandas as pd
        from analyzers.data_fetcher import get_stock_data
        
        mock_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=90),
            'open': [100] * 90,
            'high': [105] * 90,
            'low': [95] * 90,
            'close': [102] * 90,
            'volume': [1000000] * 90
        })
        
        with patch('services.local_data_service.get_local_data_service') as mock_service:
            mock_instance = Mock()
            mock_instance.get_stock_data_smart.return_value = mock_data
            mock_service.return_value = mock_instance
            
            result = get_stock_data('600519', days=90)
            
            assert result is not None
            assert len(result) == 90


class TestTaskPriority:
    """任务优先级测试"""
    
    def test_priority_values(self):
        """测试优先级值"""
        from services.background_tasks import TaskPriority
        
        assert TaskPriority.HIGH < TaskPriority.NORMAL
        assert TaskPriority.NORMAL < TaskPriority.LOW
        assert TaskPriority.HIGH == 1
        assert TaskPriority.NORMAL == 5
        assert TaskPriority.LOW == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
