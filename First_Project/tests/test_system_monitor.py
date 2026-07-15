"""
SystemMonitor 模块单元测试
测试系统监控数据采集功能
"""
import sys
import os
import time
import unittest
from unittest.mock import Mock, patch, MagicMock

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from system_monitor import SystemMonitor


class TestSystemMonitor(unittest.TestCase):
    """SystemMonitor 类测试"""

    def setUp(self):
        """每个测试前的初始化"""
        self.monitor = SystemMonitor()

    def tearDown(self):
        """每个测试后的清理"""
        pass

    # ==================== CPU 信息测试 ====================

    @patch('system_monitor.psutil')
    def test_get_cpu_info_success(self, mock_psutil):
        """测试成功获取 CPU 信息"""
        mock_psutil.cpu_percent.return_value = 45.5
        mock_psutil.cpu_count.side_effect = [4, 8]  # logical=False, logical=True

        result = self.monitor.get_cpu_info()

        self.assertEqual(result['usage'], 45.5)
        self.assertEqual(result['cores'], 4)
        self.assertEqual(result['threads'], 8)
        mock_psutil.cpu_percent.assert_called_once_with(interval=None)

    @patch('system_monitor.psutil')
    def test_get_cpu_info_exception(self, mock_psutil):
        """测试 CPU 信息采集异常处理"""
        mock_psutil.cpu_percent.side_effect = Exception("Test error")

        result = self.monitor.get_cpu_info()

        self.assertEqual(result['usage'], 0)
        self.assertEqual(result['cores'], 0)
        self.assertEqual(result['threads'], 0)

    # ==================== 内存信息测试 ====================

    @patch('system_monitor.psutil')
    def test_get_memory_info_success(self, mock_psutil):
        """测试成功获取内存信息"""
        mock_mem = Mock()
        mock_mem.total = 16 * 1024 ** 3  # 16GB
        mock_mem.used = 8 * 1024 ** 3    # 8GB
        mock_mem.free = 8 * 1024 ** 3    # 8GB
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem

        result = self.monitor.get_memory_info()

        self.assertEqual(result['total'], 16 * 1024 ** 3)
        self.assertEqual(result['used'], 8 * 1024 ** 3)
        self.assertEqual(result['free'], 8 * 1024 ** 3)
        self.assertEqual(result['percent'], 50.0)

    @patch('system_monitor.psutil')
    def test_get_memory_info_exception(self, mock_psutil):
        """测试内存信息采集异常处理"""
        mock_psutil.virtual_memory.side_effect = Exception("Test error")

        result = self.monitor.get_memory_info()

        self.assertEqual(result['total'], 0)
        self.assertEqual(result['used'], 0)
        self.assertEqual(result['free'], 0)
        self.assertEqual(result['percent'], 0)

    # ==================== GPU 信息测试 ====================

    @patch('system_monitor.GPUtil')
    def test_get_gpu_info_gputil_success(self, mock_gputil):
        """测试使用 GPUtil 成功获取 GPU 信息"""
        mock_gpu = Mock()
        mock_gpu.name = "NVIDIA GeForce RTX 3060"
        mock_gpu.load = 0.65
        mock_gpu.memoryUsed = 4096
        mock_gpu.memoryTotal = 12288
        mock_gpu.temperature = 72
        mock_gputil.getGPUs.return_value = [mock_gpu]

        result = self.monitor.get_gpu_info()

        self.assertIsNotNone(result)
        self.assertEqual(result['name'], "NVIDIA GeForce RTX 3060")
        self.assertEqual(result['load'], 65.0)
        self.assertEqual(result['memory_used'], 4096)
        self.assertEqual(result['memory_total'], 12288)
        self.assertEqual(result['temperature'], 72)
        self.assertEqual(result['source'], 'GPUtil')

    @patch('system_monitor.GPUtil')
    @patch.object(SystemMonitor, '_get_gpu_info_from_nvidia_smi')
    def test_get_gpu_info_fallback_to_nvidia_smi(self, mock_nvidia_smi, mock_gputil):
        """测试 GPUtil 失败时回退到 nvidia-smi"""
        mock_gputil.getGPUs.side_effect = Exception("GPUtil error")
        mock_nvidia_smi.return_value = {
            'name': 'NVIDIA GTX 1660',
            'load': 50.0,
            'memory_used': 2048,
            'memory_total': 6144,
            'temperature': 65,
            'source': 'nvidia-smi'
        }

        result = self.monitor.get_gpu_info()

        self.assertIsNotNone(result)
        self.assertEqual(result['source'], 'nvidia-smi')

    @patch('system_monitor.GPUtil', None)
    @patch.object(SystemMonitor, '_get_gpu_info_from_nvidia_smi')
    @patch.object(SystemMonitor, '_get_gpu_info_from_windows')
    def test_get_gpu_info_complete_fallback(self, mock_windows, mock_nvidia_smi):
        """测试完整降级链：无 GPUtil → nvidia-smi → Windows API"""
        mock_nvidia_smi.return_value = None
        mock_windows.return_value = {
            'name': 'Intel UHD Graphics',
            'load': 20.0,
            'memory_used': 0,
            'memory_total': 2048,
            'temperature': None,
            'source': 'windows'
        }

        result = self.monitor.get_gpu_info()

        self.assertIsNotNone(result)
        self.assertEqual(result['source'], 'windows')

    def test_get_gpu_info_cache(self):
        """测试 GPU 信息缓存机制"""
        with patch.object(SystemMonitor, '_read_gpu_info_sync') as mock_read:
            mock_read.return_value = {'name': 'Test GPU', 'load': 50}

            # 第一次调用应该读取
            result1 = self.monitor.get_gpu_info()
            self.assertEqual(mock_read.call_count, 1)

            # 第二次调用（在缓存有效期内）应该使用缓存
            result2 = self.monitor.get_gpu_info()
            self.assertEqual(mock_read.call_count, 1)  # 不应该再次调用

            # 验证返回相同数据
            self.assertEqual(result1, result2)

    # ==================== 磁盘信息测试 ====================

    @patch('system_monitor.psutil')
    def test_get_disk_info_success(self, mock_psutil):
        """测试成功获取磁盘信息"""
        # Mock 分区
        mock_partition = Mock()
        mock_partition.device = '/dev/sda1'
        mock_partition.mountpoint = 'C:\\'
        mock_partition.fstype = 'NTFS'
        mock_psutil.disk_partitions.return_value = [mock_partition]

        # Mock 磁盘使用情况
        mock_usage = Mock()
        mock_usage.total = 500 * 1024 ** 3
        mock_usage.used = 250 * 1024 ** 3
        mock_usage.free = 250 * 1024 ** 3
        mock_usage.percent = 50.0
        mock_psutil.disk_usage.return_value = mock_usage

        # Mock IO 计数器
        mock_io = Mock()
        mock_io.read_bytes = 1000000
        mock_io.write_bytes = 500000
        mock_psutil.disk_io_counters.return_value = mock_io

        result = self.monitor.get_disk_info()

        self.assertEqual(len(result['partitions']), 1)
        partition = result['partitions'][0]
        self.assertEqual(partition['mountpoint'], 'C:\\')
        self.assertEqual(partition['fstype'], 'NTFS')
        self.assertGreater(result['read_speed'], 0)
        self.assertGreater(result['write_speed'], 0)

    @patch('system_monitor.psutil')
    def test_get_disk_info_permission_error(self, mock_psutil):
        """测试磁盘权限错误处理"""
        mock_partition = Mock()
        mock_partition.mountpoint = 'D:\\'
        mock_psutil.disk_partitions.return_value = [mock_partition]
        mock_psutil.disk_usage.side_effect = PermissionError("Access denied")

        result = self.monitor.get_disk_info()

        self.assertEqual(len(result['partitions']), 0)
        self.assertEqual(result['read_speed'], 0)
        self.assertEqual(result['write_speed'], 0)

    # ==================== 网络信息测试 ====================

    @patch('system_monitor.psutil')
    def test_get_network_info_success(self, mock_psutil):
        """测试成功获取网络信息"""
        # 第一次调用 - 初始化
        mock_net1 = Mock()
        mock_net1.bytes_sent = 1000000
        mock_net1.bytes_recv = 2000000
        mock_psutil.net_io_counters.return_value = mock_net1

        result1 = self.monitor.get_network_info()

        # 等待一小段时间
        time.sleep(0.1)

        # 第二次调用 - 计算速度
        mock_net2 = Mock()
        mock_net2.bytes_sent = 1100000  # 增加了 100000
        mock_net2.bytes_recv = 2200000  # 增加了 200000
        mock_psutil.net_io_counters.return_value = mock_net2

        result2 = self.monitor.get_network_info()

        self.assertGreater(result2['sent_speed'], 0)
        self.assertGreater(result2['recv_speed'], 0)
        self.assertEqual(result2['bytes_sent'], 1100000)
        self.assertEqual(result2['bytes_recv'], 2200000)

    @patch('system_monitor.psutil')
    def test_get_network_info_exception(self, mock_psutil):
        """测试网络信息采集异常处理"""
        mock_psutil.net_io_counters.side_effect = Exception("Network error")

        result = self.monitor.get_network_info()

        self.assertEqual(result['sent_speed'], 0)
        self.assertEqual(result['recv_speed'], 0)
        self.assertEqual(result['bytes_sent'], 0)
        self.assertEqual(result['bytes_recv'], 0)

    # ==================== 综合信息测试 ====================

    @patch('system_monitor.psutil')
    def test_get_all_info(self, mock_psutil):
        """测试获取所有系统信息"""
        # Mock 所有必要的数据
        mock_psutil.cpu_percent.return_value = 30.0
        mock_psutil.cpu_count.side_effect = [4, 8]

        mock_mem = Mock()
        mock_mem.total = 16 * 1024 ** 3
        mock_mem.used = 8 * 1024 ** 3
        mock_mem.free = 8 * 1024 ** 3
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem

        mock_psutil.disk_partitions.return_value = []
        mock_io = Mock()
        mock_io.read_bytes = 1000000
        mock_io.write_bytes = 500000
        mock_psutil.disk_io_counters.return_value = mock_io

        mock_net = Mock()
        mock_net.bytes_sent = 1000000
        mock_net.bytes_recv = 2000000
        mock_psutil.net_io_counters.return_value = mock_net

        result = self.monitor.get_all_info()

        self.assertIn('timestamp', result)
        self.assertIn('cpu', result)
        self.assertIn('memory', result)
        self.assertIn('gpu', result)
        self.assertIn('disk', result)
        self.assertIn('network', result)

        # 验证时间戳格式
        from datetime import datetime
        datetime.strptime(result['timestamp'], "%Y-%m-%d %H:%M:%S")

    # ==================== 边界情况测试 ====================

    def test_initialization(self):
        """测试 SystemMonitor 初始化"""
        monitor = SystemMonitor()
        self.assertIsNotNone(monitor.last_io_counters)
        self.assertIsNotNone(monitor.last_io_time)
        self.assertIsNotNone(monitor.last_net_counters)
        self.assertIsNotNone(monitor.last_net_time)
        self.assertIsNone(monitor.gpu_cache)
        self.assertFalse(monitor.gpu_update_running)

    def test_gpu_cache_ttl(self):
        """测试 GPU 缓存过期时间"""
        self.assertEqual(self.monitor.gpu_cache_ttl, 10)  # 10秒


class TestGPUFallbackMethods(unittest.TestCase):
    """GPU 降级方法测试"""

    def setUp(self):
        self.monitor = SystemMonitor()

    @patch('subprocess.run')
    def test_nvidia_smi_success(self, mock_run):
        """测试 nvidia-smi 成功执行"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "NVIDIA GeForce RTX 3060, 65, 4096, 12288, 72\n"
        mock_run.return_value = mock_result

        result = self.monitor._get_gpu_info_from_nvidia_smi()

        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'NVIDIA GeForce RTX 3060')
        self.assertEqual(result['load'], 65.0)
        self.assertEqual(result['source'], 'nvidia-smi')

    @patch('subprocess.run')
    def test_nvidia_smi_not_found(self, mock_run):
        """测试 nvidia-smi 不存在"""
        mock_run.side_effect = FileNotFoundError()

        result = self.monitor._get_gpu_info_from_nvidia_smi()

        self.assertIsNone(result)
        self.assertFalse(self.monitor.nvidia_smi_available)

    @patch.object(SystemMonitor, '_run_powershell_json')
    def test_windows_gpu_names(self, mock_powershell):
        """测试 Windows GPU 名称获取"""
        mock_powershell.return_value = [
            {'Name': 'Intel UHD Graphics', 'AdapterRAM': 2147483648}
        ]

        result = self.monitor._get_windows_gpu_names()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'Intel UHD Graphics')
        self.assertAlmostEqual(result[0]['memory_total'], 2048)  # MB

    @patch.object(SystemMonitor, '_run_powershell_json')
    def test_windows_gpu_load(self, mock_powershell):
        """测试 Windows GPU 负载获取"""
        mock_powershell.return_value = 45.5

        result = self.monitor._get_windows_gpu_load()

        self.assertEqual(result, 45.5)

    @patch.object(SystemMonitor, '_run_powershell_json')
    def test_windows_gpu_load_invalid(self, mock_powershell):
        """测试 Windows GPU 负载无效值处理"""
        mock_powershell.return_value = "invalid"

        result = self.monitor._get_windows_gpu_load()

        self.assertEqual(result, 0)


if __name__ == '__main__':
    unittest.main()
