# 系统监控程序 - 测试文档

## 📋 目录结构

```
tests/
├── __init__.py                    # 测试包初始化
├── test_system_monitor.py         # SystemMonitor 单元测试
├── test_gui.py                    # GUI 组件单元测试
└── test_integration.py            # 集成测试

run_tests.py                       # 测试运行器
pytest.ini                         # pytest 配置
.coveragerc                        # 覆盖率配置
```

## 🧪 测试分类

### 1. **SystemMonitor 单元测试** (`test_system_monitor.py`)

测试系统监控数据采集模块的核心功能。

#### 测试内容：
- ✅ CPU 信息采集（成功/失败场景）
- ✅ 内存信息采集（成功/失败场景）
- ✅ GPU 信息采集（多级降级策略）
  - GPUtil → nvidia-smi → Windows API
- ✅ 磁盘信息采集（权限错误处理）
- ✅ 网络速度计算
- ✅ 数据缓存机制
- ✅ 异常处理和边界情况

#### 关键测试用例：
```python
test_get_cpu_info_success()              # CPU 信息正常获取
test_get_cpu_info_exception()            # CPU 采集异常处理
test_get_gpu_info_gputil_success()       # GPUtil 成功
test_get_gpu_info_fallback_to_nvidia_smi()  # 降级到 nvidia-smi
test_get_gpu_info_complete_fallback()    # 完整降级链
test_get_gpu_info_cache()                # GPU 缓存机制
test_get_disk_info_permission_error()    # 磁盘权限错误
test_get_network_info_success()          # 网络速度计算
```

---

### 2. **GUI 组件单元测试** (`test_gui.py`)

测试 PyQt5 界面组件和业务逻辑。

#### 测试内容：
- ✅ 工具函数（格式化、磁盘匹配等）
- ✅ 设置管理（加载/保存）
- ✅ GaugeWidget 仪表盘组件
  - 数据更新
  - 颜色编码
  - 网络图表
- ✅ MonitorPanel 面板布局
- ✅ MainWindow 主窗口
- ✅ SettingsDialog 设置对话框

#### 关键测试用例：
```python
test_format_bytes_per_second_basic()     # 字节格式化
test_disk_matches_selection_all()        # 磁盘匹配-全选
test_load_settings_default()             # 默认设置加载
test_save_and_load_settings()            # 设置持久化
test_widget_initialization()             # 仪表盘初始化
test_update_data_clamping()              # 数据范围限制
test_get_color_low_usage()               # 低使用率颜色
test_panel_initialization()              # 面板初始化
test_window_initialization()             # 窗口初始化
test_edit_mode_toggle()                  # 编辑模式切换
```

---

### 3. **集成测试** (`test_integration.py`)

测试多个模块协同工作的场景。

#### 测试内容：
- ✅ 完整工作流程
- ✅ 设置持久化
- ✅ 布局切换
- ✅ 磁盘筛选
- ✅ 数据流验证
- ✅ 错误恢复
- ✅ 性能测试

#### 关键测试用例：
```python
test_full_workflow()                     # 完整工作流程
test_settings_persistence()              # 设置持久化
test_layout_switching()                  # 布局切换
test_disk_filtering()                    # 磁盘筛选
test_monitor_to_gauge_data_flow()        # 数据流验证
test_graceful_degradation_gpu()          # GPU 优雅降级
test_error_recovery_disk()               # 磁盘错误恢复
test_monitor_performance()               # 监控器性能
test_gui_update_performance()            # GUI 更新性能
```

---

## 🚀 运行测试

### 方法 1：使用测试运行器（推荐）

```bash
# 运行所有测试
python run_tests.py

# 运行指定测试模块
python run_tests.py tests.test_system_monitor

# 运行指定测试类
python run_tests.py tests.test_system_monitor.TestSystemMonitor

# 运行指定测试方法
python run_tests.py tests.test_system_monitor.TestSystemMonitor.test_get_cpu_info_success
```

### 方法 2：使用 unittest

```bash
# 运行所有测试
python -m unittest discover tests

# 运行指定模块
python -m unittest tests.test_system_monitor

# 详细输出
python -m unittest -v tests.test_system_monitor
```

### 方法 3：使用 pytest

```bash
# 安装 pytest
pip install pytest pytest-cov

# 运行所有测试
pytest

# 运行指定模块
pytest tests/test_system_monitor.py

# 运行带标记的测试
pytest -m gui
pytest -m integration
pytest -m system

# 生成覆盖率报告
pytest --cov=. --cov-report=html

# 查看 HTML 覆盖率报告
# 打开 htmlcov/index.html
```

---

## 📊 测试覆盖率

### 查看覆盖率

```bash
# 命令行覆盖率报告
pytest --cov=. --cov-report=term-missing

# HTML 覆盖率报告
pytest --cov=. --cov-report=html
# 然后在浏览器中打开 htmlcov/index.html
```

### 覆盖率目标
- **SystemMonitor**: ≥ 90%
- **工具函数**: ≥ 95%
- **GUI 组件**: ≥ 80%
- **整体项目**: ≥ 85%

---

## 🔍 测试说明

### Mock 策略

测试中广泛使用 `unittest.mock` 来模拟外部依赖：

```python
@patch('system_monitor.psutil')
def test_example(self, mock_psutil):
    mock_psutil.cpu_percent.return_value = 45.5
    # ... 测试代码
```

### 跳过条件

某些测试需要特定环境：

```python
@unittest.skipUnless(HAS_QT, "PyQt5 not available")
class TestGaugeWidget(unittest.TestCase):
    # 只有在 PyQt5 可用时才运行
```

### 性能测试

性能测试会打印执行时间：

```
Performance: 10 iterations in 0.15s (15ms per call)
GUI Performance: 20 updates in 0.32s (16ms per update)
```

---

## ⚠️ 注意事项

### 1. GUI 测试要求
- GUI 测试需要显示服务器（Windows 上通常没问题）
- 在无头环境（如 CI/CD）中，GUI 测试会被自动跳过

### 2. 系统权限
- 某些磁盘测试可能需要管理员权限
- 开机自启测试会修改注册表（已 Mock，不影响实际系统）

### 3. GPU 测试
- GPU 测试不依赖实际硬件
- 所有 GPU 调用都被 Mock，可以在无 GPU 机器上运行

### 4. 网络测试
- 网络测试使用 Mock 数据
- 不会发送或接收真实网络流量

---

## 🐛 调试测试

### 查看详细输出

```bash
# unittest 详细模式
python -m unittest -v tests.test_system_monitor

# pytest 详细模式
pytest -vv tests/test_system_monitor.py

# 打印日志
pytest -s tests/test_system_monitor.py
```

### 运行单个测试

```bash
# 只运行一个测试方法
python -m unittest tests.test_system_monitor.TestSystemMonitor.test_get_cpu_info_success

# 或使用 pytest
pytest tests/test_system_monitor.py::TestSystemMonitor::test_get_cpu_info_success -v
```

### 快速失败模式

```bash
# 遇到第一个失败就停止
pytest -x tests/

# 或在 run_tests.py 中设置 failfast=True
```

---

## 📝 添加新测试

### 1. 创建测试文件

在 `tests/` 目录下创建 `test_<module>.py`

### 2. 编写测试类

```python
import unittest
from unittest.mock import Mock, patch

class TestNewFeature(unittest.TestCase):
    def setUp(self):
        # 每个测试前的初始化
        pass
    
    def tearDown(self):
        # 每个测试后的清理
        pass
    
    def test_feature_success(self):
        """测试功能成功场景"""
        # Arrange
        # Act
        # Assert
        self.assertTrue(True)
    
    def test_feature_failure(self):
        """测试功能失败场景"""
        with self.assertRaises(Exception):
            raise Exception("Expected error")
```

### 3. 添加到运行器

在 `run_tests.py` 的 `test_modules` 列表中添加新模块：

```python
test_modules = [
    'tests.test_system_monitor',
    'tests.test_gui',
    'tests.test_integration',
    'tests.test_new_module',  # 新增
]
```

---

## 🎯 测试最佳实践

### 1. AAA 模式
- **Arrange**: 准备测试数据
- **Act**: 执行被测操作
- **Assert**: 验证结果

### 2. 测试命名
- 使用描述性名称：`test_<function>_<scenario>`
- 例如：`test_get_cpu_info_success`

### 3. 独立性
- 每个测试应该独立运行
- 不依赖其他测试的执行顺序
- 使用 `setUp` 和 `tearDown` 清理状态

### 4. Mock 外部依赖
- 文件系统
- 网络请求
- 硬件访问
- 第三方 API

### 5. 边界值测试
- 最小值、最大值
- 空值、None
- 异常输入

---

## 📈 持续集成

### GitHub Actions 示例

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          pytest --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## 🔗 相关资源

- [unittest 官方文档](https://docs.python.org/3/library/unittest.html)
- [pytest 官方文档](https://docs.pytest.org/)
- [Mock 库文档](https://docs.python.org/3/library/unittest.mock.html)
- [覆盖率工具](https://coverage.readthedocs.io/)

---

## ❓ 常见问题

### Q: GUI 测试失败怎么办？
A: 确保在有显示服务器的环境中运行，或接受跳过这些测试。

### Q: 如何测试实际的 GPU？
A: 当前测试使用 Mock，如需测试真实 GPU，移除相应的 `@patch` 装饰器。

### Q: 测试运行很慢？
A: 检查是否有不必要的 sleep 或大量迭代，考虑使用 `@pytest.mark.slow` 标记。

### Q: 如何提高覆盖率？
A: 关注未覆盖的代码行，添加对应的测试用例，特别是异常处理分支。

---

**最后更新**: 2026-07-15  
**维护者**: AI Assistant
