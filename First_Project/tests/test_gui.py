"""
GUI 组件和功能测试
测试 PyQt5 界面组件和业务逻辑
"""
import sys
import os
import json
import unittest
from unittest.mock import Mock, patch, MagicMock

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 需要在有显示服务器的环境下运行，或使用虚拟显示
try:
    from PyQt5.QtCore import Qt, QPointF, QRectF
    from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath
    from PyQt5.QtWidgets import QApplication, QWidget
    
    # 创建 QApplication 实例（如果还没有）
    if not QApplication.instance():
        app = QApplication(sys.argv)
    
    HAS_QT = True
except ImportError:
    HAS_QT = False

if HAS_QT:
    from main import (
        GaugeWidget, MonitorPanel, SettingsDialog, MainWindow,
        format_bytes_per_second, format_bytes_compact,
        normalize_disk_mount, disk_matches_selection,
        load_settings, save_settings, GAUGE_WIDTH, GAUGE_HEIGHT
    )


class TestUtilityFunctions(unittest.TestCase):
    """工具函数测试"""

    def test_format_bytes_per_second_basic(self):
        """测试基本字节/秒格式化"""
        self.assertEqual(format_bytes_per_second(0), "0B/s")
        self.assertEqual(format_bytes_per_second(100), "100B/s")
        self.assertEqual(format_bytes_per_second(1024), "1K/s")
        self.assertEqual(format_bytes_per_second(1048576), "1M/s")
        self.assertEqual(format_bytes_per_second(1073741824), "1G/s")

    def test_format_bytes_per_second_precision(self):
        """测试格式化精度"""
        result = format_bytes_per_second(1536)  # 1.5K
        self.assertIn("1.5", result)
        self.assertIn("K/s", result)

    def test_format_bytes_compact_basic(self):
        """测试紧凑字节格式化"""
        self.assertEqual(format_bytes_compact(0), "0B")
        self.assertEqual(format_bytes_compact(1024), "1K")
        self.assertEqual(format_bytes_compact(1048576), "1M")
        self.assertEqual(format_bytes_compact(1073741824), "1G")

    def test_normalize_disk_mount(self):
        """测试磁盘挂载点标准化"""
        self.assertEqual(normalize_disk_mount("C:\\"), "C:")
        self.assertEqual(normalize_disk_mount("D:/"), "D:")
        self.assertEqual(normalize_disk_mount("E:\\\\"), "E:")
        self.assertEqual(normalize_disk_mount(""), "")
        self.assertEqual(normalize_disk_mount(None), "")

    def test_disk_matches_selection_all(self):
        """测试磁盘匹配 - 全部显示"""
        selected = []
        self.assertTrue(disk_matches_selection("C:\\", selected))
        self.assertTrue(disk_matches_selection("D:\\", selected))

    def test_disk_matches_selection_none(self):
        """测试磁盘匹配 - 全部隐藏"""
        selected = ["__none__"]
        self.assertFalse(disk_matches_selection("C:\\", selected))
        self.assertFalse(disk_matches_selection("D:\\", selected))

    def test_disk_matches_selection_specific(self):
        """测试磁盘匹配 - 指定磁盘"""
        selected = ["C:"]
        self.assertTrue(disk_matches_selection("C:\\", selected))
        self.assertFalse(disk_matches_selection("D:\\", selected))


class TestSettingsManagement(unittest.TestCase):
    """设置管理测试"""

    def setUp(self):
        """创建临时设置文件"""
        self.test_settings_file = os.path.join(
            os.path.dirname(__file__), 'test_settings.json'
        )
        # 备份原始设置文件路径
        import main
        self.original_settings_file = main.SETTINGS_FILE
        main.SETTINGS_FILE = self.test_settings_file

    def tearDown(self):
        """清理临时文件"""
        if os.path.exists(self.test_settings_file):
            os.remove(self.test_settings_file)
        # 恢复原始设置文件路径
        import main
        main.SETTINGS_FILE = self.original_settings_file

    def test_load_settings_default(self):
        """测试加载默认设置"""
        settings = load_settings()
        
        self.assertIn('refresh_interval', settings)
        self.assertIn('opacity', settings)
        self.assertIn('auto_start', settings)
        self.assertIn('theme', settings)
        self.assertIn('size', settings)
        self.assertIn('layout', settings)
        self.assertEqual(settings['refresh_interval'], 1)
        self.assertEqual(settings['opacity'], 96)
        self.assertEqual(settings['theme'], '深色')
        self.assertEqual(settings['size'], '中型')
        self.assertEqual(settings['layout'], 'square')

    def test_save_and_load_settings(self):
        """测试保存和加载设置"""
        test_settings = {
            'refresh_interval': 5,
            'opacity': 80,
            'auto_start': True,
            'theme': '浅色',
            'size': '大型',
            'layout': 'horizontal'
        }
        
        save_settings(test_settings)
        loaded = load_settings()
        
        self.assertEqual(loaded['refresh_interval'], 5)
        self.assertEqual(loaded['opacity'], 80)
        self.assertEqual(loaded['auto_start'], True)
        self.assertEqual(loaded['theme'], '浅色')
        self.assertEqual(loaded['size'], '大型')
        self.assertEqual(loaded['layout'], 'horizontal')

    def test_load_settings_with_existing_file(self):
        """测试从现有文件加载设置"""
        # 创建测试设置文件
        test_data = {
            'refresh_interval': 10,
            'custom_key': 'custom_value'
        }
        with open(self.test_settings_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        loaded = load_settings()
        
        self.assertEqual(loaded['refresh_interval'], 10)
        self.assertEqual(loaded['custom_key'], 'custom_value')
        # 应该保留默认值
        self.assertIn('opacity', loaded)


@unittest.skipUnless(HAS_QT, "PyQt5 not available")
class TestGaugeWidget(unittest.TestCase):
    """仪表盘组件测试"""

    def setUp(self):
        self.widget = GaugeWidget("Test")

    def test_widget_initialization(self):
        """测试组件初始化"""
        self.assertEqual(self.widget.title, "Test")
        self.assertEqual(self.widget.value, 0)
        self.assertEqual(self.widget.value_text, "0%")
        self.assertEqual(self.widget.detail_text, "")
        self.assertEqual(self.widget.width(), GAUGE_WIDTH)
        self.assertEqual(self.widget.height(), GAUGE_HEIGHT)

    def test_update_data_basic(self):
        """测试基本数据更新"""
        self.widget.update_data(50, "Detail text", "50%")
        
        self.assertEqual(self.widget.value, 50)
        self.assertEqual(self.widget.detail_text, "Detail text")
        self.assertEqual(self.widget.value_text, "50%")

    def test_update_data_clamping(self):
        """测试数据范围限制"""
        self.widget.update_data(150)  # 超过100
        self.assertEqual(self.widget.value, 100)
        
        self.widget.update_data(-10)  # 低于0
        self.assertEqual(self.widget.value, 0)

    def test_update_network_data(self):
        """测试网络数据更新"""
        self.widget.update_network_data(1024 * 1024, 2 * 1024 * 1024)  # 1MB/s, 2MB/s
        
        self.assertGreater(self.widget.value, 0)
        self.assertIn("↑", self.widget.detail_text)
        self.assertIn("↓", self.widget.detail_text)
        self.assertEqual(len(self.widget.upload_history), 1)
        self.assertEqual(len(self.widget.download_history), 1)

    def test_get_color_low_usage(self):
        """测试低使用率颜色"""
        self.widget.value = 30
        color = self.widget.get_color()
        # 应该是绿色
        self.assertEqual(color.red(), 48)
        self.assertEqual(color.green(), 210)

    def test_get_color_medium_usage(self):
        """测试中等使用率颜色"""
        self.widget.value = 65
        color = self.widget.get_color()
        # 应该是橙色
        self.assertEqual(color.red(), 255)
        self.assertEqual(color.green(), 156)

    def test_get_color_high_usage(self):
        """测试高使用率颜色"""
        self.widget.value = 90
        color = self.widget.get_color()
        # 应该是红色
        self.assertEqual(color.red(), 244)
        self.assertEqual(color.green(), 82)

    def test_accent_override(self):
        """测试自定义颜色覆盖"""
        self.widget.accent_override = "#FF0000"
        color = self.widget.get_color()
        self.assertEqual(color.name(), "#ff0000")


@unittest.skipUnless(HAS_QT, "PyQt5 not available")
class TestMonitorPanel(unittest.TestCase):
    """监控面板测试"""

    def setUp(self):
        self.panel = MonitorPanel()

    def test_panel_initialization(self):
        """测试面板初始化"""
        self.assertEqual(self.panel.layout_mode, "square")
        self.assertEqual(len(self.panel.widgets), 0)
        self.assertIsNone(self.panel.columns)

    def test_set_widgets_square_layout(self):
        """测试方形布局设置"""
        widgets = [GaugeWidget(f"Widget {i}") for i in range(4)]
        self.panel.set_widgets(widgets, "square")
        
        self.assertEqual(len(self.panel.widgets), 4)
        self.assertEqual(self.panel.layout_mode, "square")

    def test_set_widgets_horizontal_layout(self):
        """测试横向布局设置"""
        widgets = [GaugeWidget(f"Widget {i}") for i in range(3)]
        self.panel.set_widgets(widgets, "horizontal", columns=3)
        
        self.assertEqual(len(self.panel.widgets), 3)
        self.assertEqual(self.panel.layout_mode, "horizontal")
        self.assertEqual(self.panel.columns, 3)

    def test_grid_columns_calculation(self):
        """测试网格列数计算"""
        self.assertEqual(MonitorPanel.grid_columns(1), 1)
        self.assertEqual(MonitorPanel.grid_columns(2), 2)
        self.assertEqual(MonitorPanel.grid_columns(4), 2)
        self.assertEqual(MonitorPanel.grid_columns(9), 3)
        self.assertEqual(MonitorPanel.grid_columns(0), 1)


@unittest.skipUnless(HAS_QT, "PyQt5 not available")
class TestMainWindow(unittest.TestCase):
    """主窗口测试"""

    def setUp(self):
        # Mock SystemMonitor
        with patch('main.SystemMonitor') as mock_monitor:
            mock_instance = Mock()
            mock_instance.get_all_info.return_value = {
                'cpu': {'usage': 30, 'cores': 4, 'threads': 8},
                'memory': {'total': 16*1024**3, 'used': 8*1024**3, 'percent': 50},
                'gpu': None,
                'disk': {'partitions': []},
                'network': {'sent_speed': 0, 'recv_speed': 0}
            }
            mock_monitor.return_value = mock_instance
            
            # Mock shared memory to avoid conflicts
            with patch('main.QSharedMemory') as mock_shared:
                mock_shared_instance = Mock()
                mock_shared_instance.create.return_value = True
                mock_shared.return_value = mock_shared_instance
                
                self.window = MainWindow()

    def tearDown(self):
        if hasattr(self, 'window'):
            self.window.close()

    def test_window_initialization(self):
        """测试窗口初始化"""
        self.assertIsNotNone(self.window.monitor)
        self.assertIsNotNone(self.window.settings)
        self.assertIsNotNone(self.window.panel)

    def test_edit_mode_toggle(self):
        """测试编辑模式切换"""
        initial_mode = self.window.edit_mode
        self.window.toggle_edit_mode()
        self.assertNotEqual(self.window.edit_mode, initial_mode)

    def test_layout_metrics(self):
        """测试布局度量计算"""
        columns, rows, width, height = self.window.layout_metrics(4, "square")
        self.assertGreater(columns, 0)
        self.assertGreater(rows, 0)
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)

    def test_build_gauges(self):
        """测试仪表盘构建"""
        info = {
            'cpu': {'usage': 30, 'cores': 4, 'threads': 8},
            'memory': {'total': 16*1024**3, 'used': 8*1024**3, 'percent': 50},
            'gpu': None,
            'disk': {'partitions': []},
            'network': {'sent_speed': 0, 'recv_speed': 0}
        }
        
        self.window.build_gauges(info)
        
        self.assertIn('cpu', self.window.gauges)
        self.assertIn('memory', self.window.gauges)
        self.assertIn('network', self.window.gauges)

    def test_render_info(self):
        """测试信息渲染"""
        info = {
            'cpu': {'usage': 30, 'cores': 4, 'threads': 8},
            'memory': {'total': 16*1024**3, 'used': 8*1024**3, 'percent': 50},
            'gpu': None,
            'disk': {'partitions': []},
            'network': {'sent_speed': 1000, 'recv_speed': 2000}
        }
        
        self.window.render_info(info)
        
        # 验证仪表盘数据已更新
        cpu_gauge = self.window.gauges['cpu']
        self.assertEqual(cpu_gauge.value, 30)


@unittest.skipUnless(HAS_QT, "PyQt5 not available")
class TestSettingsDialog(unittest.TestCase):
    """设置对话框测试"""

    def setUp(self):
        # Mock SystemMonitor
        with patch('main.SystemMonitor') as mock_monitor:
            mock_instance = Mock()
            mock_instance.get_all_info.return_value = {
                'cpu': {'usage': 30, 'cores': 4, 'threads': 8},
                'memory': {'total': 16*1024**3, 'used': 8*1024**3, 'percent': 50},
                'gpu': None,
                'disk': {'partitions': []},
                'network': {'sent_speed': 0, 'recv_speed': 0}
            }
            mock_monitor.return_value = mock_instance
            
            with patch('main.QSharedMemory') as mock_shared:
                mock_shared_instance = Mock()
                mock_shared_instance.create.return_value = True
                mock_shared.return_value = mock_shared_instance
                
                parent = MainWindow()
                self.dialog = SettingsDialog(parent)

    def tearDown(self):
        if hasattr(self, 'dialog'):
            self.dialog.close()
        if hasattr(self, '_parent'):
            self._parent.close()

    def test_dialog_initialization(self):
        """测试对话框初始化"""
        self.assertEqual(self.dialog.windowTitle(), "设置")
        self.assertFalse(self.dialog.saved)

    def test_get_selected_disks_all(self):
        """测试获取选中的磁盘 - 全选"""
        # 模拟所有复选框都被选中
        self.dialog.disk_checks = []
        result = self.dialog.get_selected_disks()
        self.assertEqual(result, [])

    def test_refresh_spinbox_range(self):
        """测试刷新间隔范围"""
        self.assertEqual(self.dialog.refresh_spinbox.minimum(), 1)
        self.assertEqual(self.dialog.refresh_spinbox.maximum(), 60)

    def test_opacity_slider_range(self):
        """测试透明度滑块范围"""
        self.assertEqual(self.dialog.opacity_slider.minimum(), 35)
        self.assertEqual(self.dialog.opacity_slider.maximum(), 100)


if __name__ == '__main__':
    unittest.main()
