"""
集成测试
测试多个模块协同工作的场景
"""
import sys
import os
import time
import json
import unittest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from PyQt5.QtWidgets import QApplication
    if not QApplication.instance():
        app = QApplication(sys.argv)
    HAS_QT = True
except ImportError:
    HAS_QT = False

if HAS_QT:
    from main import MainWindow, SettingsDialog, save_settings, load_settings
    from system_monitor import SystemMonitor


class TestSystemIntegration(unittest.TestCase):
    """系统集成测试"""

    def setUp(self):
        """设置测试环境"""
        self.test_settings_file = os.path.join(
            os.path.dirname(__file__), 'test_integration_settings.json'
        )
        
        # 临时替换设置文件路径
        import main
        self.original_settings_file = main.SETTINGS_FILE
        main.SETTINGS_FILE = self.test_settings_file

    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.test_settings_file):
            os.remove(self.test_settings_file)
        
        import main
        main.SETTINGS_FILE = self.original_settings_file

    @patch('main.SystemMonitor')
    @patch('main.QSharedMemory')
    def test_full_workflow(self, mock_shared, mock_monitor_class):
        """测试完整工作流程"""
        # Mock 系统监控器
        mock_monitor = Mock()
        mock_monitor.get_all_info.return_value = {
            'cpu': {'usage': 45.5, 'cores': 8, 'threads': 16},
            'memory': {
                'total': 32 * 1024 ** 3,
                'used': 16 * 1024 ** 3,
                'percent': 50.0
            },
            'gpu': {
                'name': 'NVIDIA RTX 3080',
                'load': 75.0,
                'memory_used': 8192,
                'memory_total': 10240,
                'temperature': 70
            },
            'disk': {
                'partitions': [
                    {
                        'mountpoint': 'C:\\',
                        'total': 500 * 1024 ** 3,
                        'used': 250 * 1024 ** 3,
                        'percent': 50.0
                    }
                ],
                'read_speed': 1024 * 1024,
                'write_speed': 512 * 1024
            },
            'network': {
                'sent_speed': 1024 * 100,
                'recv_speed': 1024 * 1000
            }
        }
        mock_monitor_class.return_value = mock_monitor

        # Mock 共享内存
        mock_shared_instance = Mock()
        mock_shared_instance.create.return_value = True
        mock_shared.return_value = mock_shared_instance

        # 创建主窗口
        window = MainWindow()

        try:
            # 验证初始化
            self.assertIsNotNone(window.monitor)
            self.assertIsNotNone(window.settings)
            
            # 验证默认设置
            self.assertIn('refresh_interval', window.settings)
            self.assertIn('opacity', window.settings)
            
            # 模拟数据更新
            window.update_data()
            
            # 验证仪表盘已创建
            self.assertGreater(len(window.gauges), 0)
            self.assertIn('cpu', window.gauges)
            self.assertIn('memory', window.gauges)
            self.assertIn('network', window.gauges)
            
            # 验证数据已渲染
            cpu_gauge = window.gauges['cpu']
            self.assertEqual(cpu_gauge.value, 45.5)
            
            memory_gauge = window.gauges['memory']
            self.assertEqual(memory_gauge.value, 50.0)
            
        finally:
            window.close()

    @patch('main.SystemMonitor')
    @patch('main.QSharedMemory')
    def test_settings_persistence(self, mock_shared, mock_monitor_class):
        """测试设置持久化"""
        mock_monitor = Mock()
        mock_monitor.get_all_info.return_value = {
            'cpu': {'usage': 30, 'cores': 4, 'threads': 8},
            'memory': {'total': 16*1024**3, 'used': 8*1024**3, 'percent': 50},
            'gpu': None,
            'disk': {'partitions': []},
            'network': {'sent_speed': 0, 'recv_speed': 0}
        }
        mock_monitor_class.return_value = mock_monitor
        
        mock_shared_instance = Mock()
        mock_shared_instance.create.return_value = True
        mock_shared.return_value = mock_shared_instance

        # 创建窗口并修改设置
        window = MainWindow()
        try:
            original_interval = window.settings['refresh_interval']
            
            # 修改设置
            window.settings['refresh_interval'] = 5
            window.settings['opacity'] = 80
            save_settings(window.settings)
            
            # 重新加载设置
            loaded_settings = load_settings()
            
            # 验证设置已保存
            self.assertEqual(loaded_settings['refresh_interval'], 5)
            self.assertEqual(loaded_settings['opacity'], 80)
            
        finally:
            window.close()

    @patch('main.SystemMonitor')
    @patch('main.QSharedMemory')
    def test_layout_switching(self, mock_shared, mock_monitor_class):
        """测试布局切换"""
        mock_monitor = Mock()
        mock_monitor.get_all_info.return_value = {
            'cpu': {'usage': 30, 'cores': 4, 'threads': 8},
            'memory': {'total': 16*1024**3, 'used': 8*1024**3, 'percent': 50},
            'gpu': None,
            'disk': {'partitions': []},
            'network': {'sent_speed': 0, 'recv_speed': 0}
        }
        mock_monitor_class.return_value = mock_monitor
        
        mock_shared_instance = Mock()
        mock_shared_instance.create.return_value = True
        mock_shared.return_value = mock_shared_instance

        window = MainWindow()
        try:
            initial_layout = window.settings.get('layout', 'square')
            
            # 切换布局
            window.toggle_layout()
            
            new_layout = window.settings.get('layout')
            self.assertNotEqual(initial_layout, new_layout)
            
            # 再次切换应该回到原布局
            window.toggle_layout()
            final_layout = window.settings.get('layout')
            self.assertEqual(initial_layout, final_layout)
            
        finally:
            window.close()

    @patch('main.SystemMonitor')
    @patch('main.QSharedMemory')
    def test_disk_filtering(self, mock_shared, mock_monitor_class):
        """测试磁盘筛选功能"""
        mock_monitor = Mock()
        mock_monitor.get_all_info.return_value = {
            'cpu': {'usage': 30, 'cores': 4, 'threads': 8},
            'memory': {'total': 16*1024**3, 'used': 8*1024**3, 'percent': 50},
            'gpu': None,
            'disk': {
                'partitions': [
                    {'mountpoint': 'C:\\', 'total': 500*1024**3, 'used': 250*1024**3, 'percent': 50},
                    {'mountpoint': 'D:\\', 'total': 1000*1024**3, 'used': 500*1024**3, 'percent': 50},
                ]
            },
            'network': {'sent_speed': 0, 'recv_speed': 0}
        }
        mock_monitor_class.return_value = mock_monitor
        
        mock_shared_instance = Mock()
        mock_shared_instance.create.return_value = True
        mock_shared.return_value = mock_shared_instance

        window = MainWindow()
        try:
            # 初始状态 - 显示所有磁盘
            window.update_data()
            initial_disk_count = len([k for k in window.gauges.keys() if k.startswith('disk:')])
            
            # 筛选只显示 C 盘
            window.settings['selected_disks'] = ['C:']
            window.last_visible_disks = None  # 强制重建
            window.update_data()
            
            filtered_disk_count = len([k for k in window.gauges.keys() if k.startswith('disk:')])
            self.assertEqual(filtered_disk_count, 1)
            
            # 验证是 C 盘
            self.assertIn('disk:C:\\', window.gauges)
            
        finally:
            window.close()


class TestDataFlow(unittest.TestCase):
    """数据流测试"""

    def test_monitor_to_gauge_data_flow(self):
        """测试从监控器到仪表盘的数据流"""
        monitor = SystemMonitor()
        
        with patch('system_monitor.psutil') as mock_psutil:
            # Mock CPU 数据
            mock_psutil.cpu_percent.return_value = 75.5
            mock_psutil.cpu_count.side_effect = [8, 16]
            
            # 获取数据
            cpu_info = monitor.get_cpu_info()
            
            # 验证数据格式
            self.assertIsInstance(cpu_info['usage'], float)
            self.assertIsInstance(cpu_info['cores'], int)
            self.assertIsInstance(cpu_info['threads'], int)
            
            # 验证数据范围
            self.assertGreaterEqual(cpu_info['usage'], 0)
            self.assertLessEqual(cpu_info['usage'], 100)
            self.assertGreater(cpu_info['cores'], 0)
            self.assertGreater(cpu_info['threads'], 0)

    def test_network_speed_calculation(self):
        """测试网络速度计算"""
        monitor = SystemMonitor()
        
        with patch('system_monitor.psutil') as mock_psutil:
            # 第一次调用 - 初始化
            mock_net1 = Mock()
            mock_net1.bytes_sent = 1000000
            mock_net1.bytes_recv = 2000000
            mock_psutil.net_io_counters.return_value = mock_net1
            
            result1 = monitor.get_network_info()
            
            time.sleep(0.1)
            
            # 第二次调用 - 计算速度
            mock_net2 = Mock()
            mock_net2.bytes_sent = 1100000  # +100000
            mock_net2.bytes_recv = 2300000  # +300000
            mock_psutil.net_io_counters.return_value = mock_net2
            
            result2 = monitor.get_network_info()
            
            # 验证速度计算
            self.assertGreater(result2['sent_speed'], 0)
            self.assertGreater(result2['recv_speed'], 0)


class TestErrorHandling(unittest.TestCase):
    """错误处理测试"""

    def test_graceful_degradation_gpu(self):
        """测试 GPU 监控的优雅降级"""
        monitor = SystemMonitor()
        
        # 禁用所有 GPU 检测方法
        with patch('system_monitor.GPUtil', None):
            with patch.object(monitor, '_get_gpu_info_from_nvidia_smi', return_value=None):
                with patch.object(monitor, '_get_windows_gpu_names', return_value=[]):
                    
                    result = monitor.get_gpu_info()
                    
                    # 应该返回 None 而不是抛出异常
                    self.assertIsNone(result)

    def test_error_recovery_disk(self):
        """测试磁盘错误的恢复"""
        monitor = SystemMonitor()
        
        with patch('system_monitor.psutil') as mock_psutil:
            mock_psutil.disk_partitions.side_effect = Exception("Disk error")
            
            result = monitor.get_disk_info()
            
            # 应该返回空数据而不是崩溃
            self.assertEqual(result['partitions'], [])
            self.assertEqual(result['read_speed'], 0)
            self.assertEqual(result['write_speed'], 0)

    def test_error_recovery_network(self):
        """测试网络错误的恢复"""
        monitor = SystemMonitor()
        
        with patch('system_monitor.psutil') as mock_psutil:
            mock_psutil.net_io_counters.side_effect = Exception("Network error")
            
            result = monitor.get_network_info()
            
            # 应该返回零值而不是崩溃
            self.assertEqual(result['sent_speed'], 0)
            self.assertEqual(result['recv_speed'], 0)


class TestPerformance(unittest.TestCase):
    """性能测试"""

    def test_monitor_performance(self):
        """测试监控器性能"""
        monitor = SystemMonitor()
        
        start_time = time.time()
        
        # 连续获取 10 次数据
        for _ in range(10):
            info = monitor.get_all_info()
            self.assertIn('cpu', info)
            self.assertIn('memory', info)
        
        elapsed = time.time() - start_time
        
        # 应该在合理时间内完成（5秒内）
        self.assertLess(elapsed, 5.0)
        print(f"\nPerformance: 10 iterations in {elapsed:.2f}s ({elapsed/10*1000:.0f}ms per call)")

    def test_gui_update_performance(self):
        """测试 GUI 更新性能"""
        if not HAS_QT:
            self.skipTest("PyQt5 not available")
        
        with patch('main.SystemMonitor') as mock_monitor_class:
            with patch('main.QSharedMemory') as mock_shared:
                mock_monitor = Mock()
                mock_monitor.get_all_info.return_value = {
                    'cpu': {'usage': 30, 'cores': 4, 'threads': 8},
                    'memory': {'total': 16*1024**3, 'used': 8*1024**3, 'percent': 50},
                    'gpu': None,
                    'disk': {'partitions': []},
                    'network': {'sent_speed': 0, 'recv_speed': 0}
                }
                mock_monitor_class.return_value = mock_monitor
                
                mock_shared_instance = Mock()
                mock_shared_instance.create.return_value = True
                mock_shared.return_value = mock_shared_instance
                
                window = MainWindow()
                try:
                    start_time = time.time()
                    
                    # 连续更新 20 次
                    for _ in range(20):
                        window.update_data()
                    
                    elapsed = time.time() - start_time
                    
                    # 应该在合理时间内完成
                    self.assertLess(elapsed, 10.0)
                    print(f"\nGUI Performance: 20 updates in {elapsed:.2f}s ({elapsed/20*1000:.0f}ms per update)")
                    
                finally:
                    window.close()


if __name__ == '__main__':
    unittest.main()
