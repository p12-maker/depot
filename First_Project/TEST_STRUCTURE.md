# 测试文件结构

```
First_Project/
│
├── main.py                          # 主程序
├── system_monitor.py                # 系统监控模块
├── settings.json                    # 配置文件
├── requirements.txt                 # 依赖列表
│
├── 📁 tests/                        # 测试目录
│   ├── __init__.py                  # 测试包初始化
│   ├── test_system_monitor.py       # SystemMonitor 单元测试 (375行)
│   ├── test_gui.py                  # GUI 组件测试 (414行)
│   ├── test_integration.py          # 集成测试 (403行)
│   └── README_TESTS.md              # 测试详细文档 (409行)
│
├── run_tests.py                     # Python 测试运行器 (120行)
├── test_example.py                  # 测试示例脚本 (104行)
├── run_tests.bat                    # Windows 批处理运行器 (109行)
├── pytest.ini                       # pytest 配置
├── .coveragerc                      # 覆盖率配置
├── TEST_SUMMARY.md                  # 测试总结文档 (376行)
└── TEST_STRUCTURE.md                # 本文件
```

---

## 📊 测试代码统计

| 文件 | 行数 | 类型 | 说明 |
|------|------|------|------|
| test_system_monitor.py | 375 | 单元测试 | SystemMonitor 核心功能 |
| test_gui.py | 414 | 单元测试 | GUI 组件和业务逻辑 |
| test_integration.py | 403 | 集成测试 | 模块协同和性能 |
| README_TESTS.md | 409 | 文档 | 完整测试指南 |
| TEST_SUMMARY.md | 376 | 文档 | 测试总结 |
| run_tests.py | 120 | 工具 | Python 运行器 |
| test_example.py | 104 | 示例 | 快速入门 |
| run_tests.bat | 109 | 工具 | Windows 运行器 |
| **总计** | **~2,310** | - | **测试代码 + 文档** |

---

## 🎯 测试覆盖范围

### 1️⃣ SystemMonitor 模块 (17个测试)

```
test_system_monitor.py
│
├── TestSystemMonitor (12个测试)
│   ├── CPU 信息采集
│   │   ├── test_get_cpu_info_success ✅
│   │   └── test_get_cpu_info_exception ✅
│   │
│   ├── 内存信息采集
│   │   ├── test_get_memory_info_success ✅
│   │   └── test_get_memory_info_exception ✅
│   │
│   ├── GPU 信息采集
│   │   ├── test_get_gpu_info_gputil_success ✅
│   │   ├── test_get_gpu_info_fallback_to_nvidia_smi ✅
│   │   ├── test_get_gpu_info_complete_fallback ✅
│   │   └── test_get_gpu_info_cache ✅
│   │
│   ├── 磁盘信息采集
│   │   ├── test_get_disk_info_success ✅
│   │   └── test_get_disk_info_permission_error ✅
│   │
│   ├── 网络信息采集
│   │   ├── test_get_network_info_success ✅
│   │   └── test_get_network_info_exception ✅
│   │
│   └── 综合测试
│       ├── test_get_all_info ✅
│       ├── test_initialization ✅
│       └── test_gpu_cache_ttl ✅
│
└── TestGPUFallbackMethods (5个测试)
    ├── test_nvidia_smi_success ✅
    ├── test_nvidia_smi_not_found ✅
    ├── test_windows_gpu_names ✅
    ├── test_windows_gpu_load ✅
    └── test_windows_gpu_load_invalid ✅
```

---

### 2️⃣ GUI 组件 (29个测试)

```
test_gui.py
│
├── TestUtilityFunctions (8个测试)
│   ├── 字节格式化
│   │   ├── test_format_bytes_per_second_basic ✅
│   │   ├── test_format_bytes_per_second_precision ✅
│   │   ├── test_format_bytes_compact_basic ✅
│   │   └── test_format_bytes_compact_precision ✅
│   │
│   ├── 磁盘相关
│   │   ├── test_normalize_disk_mount ✅
│   │   ├── test_disk_matches_selection_all ✅
│   │   ├── test_disk_matches_selection_none ✅
│   │   └── test_disk_matches_selection_specific ✅
│   │
├── TestSettingsManagement (3个测试)
│   ├── test_load_settings_default ✅
│   ├── test_save_and_load_settings ✅
│   └── test_load_settings_with_existing_file ✅
│
├── TestGaugeWidget (11个测试) ⚠️ 需要 PyQt5
│   ├── test_widget_initialization ✅
│   ├── test_update_data_basic ✅
│   ├── test_update_data_clamping ✅
│   ├── test_update_network_data ✅
│   ├── test_get_color_low_usage ✅
│   ├── test_get_color_medium_usage ✅
│   ├── test_get_color_high_usage ✅
│   └── test_accent_override ✅
│
├── TestMonitorPanel (4个测试) ⚠️ 需要 PyQt5
│   ├── test_panel_initialization ✅
│   ├── test_set_widgets_square_layout ✅
│   ├── test_set_widgets_horizontal_layout ✅
│   └── test_grid_columns_calculation ✅
│
├── TestMainWindow (5个测试) ⚠️ 需要 PyQt5
│   ├── test_window_initialization ✅
│   ├── test_edit_mode_toggle ✅
│   ├── test_layout_metrics ✅
│   ├── test_build_gauges ✅
│   └── test_render_info ✅
│
└── TestSettingsDialog (4个测试) ⚠️ 需要 PyQt5
    ├── test_dialog_initialization ✅
    ├── test_get_selected_disks_all ✅
    ├── test_refresh_spinbox_range ✅
    └── test_opacity_slider_range ✅
```

---

### 3️⃣ 集成测试 (12个测试)

```
test_integration.py
│
├── TestSystemIntegration (4个测试) ⚠️ 需要 PyQt5
│   ├── test_full_workflow ✅
│   ├── test_settings_persistence ✅
│   ├── test_layout_switching ✅
│   └── test_disk_filtering ✅
│
├── TestDataFlow (2个测试)
│   ├── test_monitor_to_gauge_data_flow ✅
│   └── test_network_speed_calculation ✅
│
├── TestErrorHandling (3个测试)
│   ├── test_graceful_degradation_gpu ✅
│   ├── test_error_recovery_disk ✅
│   └── test_error_recovery_network ✅
│
└── TestPerformance (2个测试) ⚠️ 需要 PyQt5
    ├── test_monitor_performance ✅
    └── test_gui_update_performance ✅
```

---

## 🔑 图例说明

- ✅ = 已实现的测试
- ⚠️ = 需要特定环境（如 PyQt5）
- 📝 = 有详细文档

---

## 📈 测试分类统计

| 分类 | 数量 | 百分比 |
|------|------|--------|
| 单元测试 | 46 | 79% |
| 集成测试 | 12 | 21% |
| **总计** | **58** | **100%** |

| 环境要求 | 数量 | 说明 |
|---------|------|------|
| 无特殊要求 | 40 | 可在任何环境运行 |
| 需要 PyQt5 | 18 | GUI 相关测试 |

---

## 🚀 快速开始

### 方式 1：使用批处理脚本（最简单）
```bash
run_tests.bat
```

### 方式 2：使用 Python 运行器
```bash
python run_tests.py
```

### 方式 3：直接使用 pytest
```bash
pytest tests/ -v
```

### 方式 4：使用 unittest
```bash
python -m unittest discover tests -v
```

---

## 📖 文档导航

1. **新手入门** → 查看 `test_example.py`
2. **测试概览** → 查看 `TEST_SUMMARY.md`
3. **详细指南** → 查看 `tests/README_TESTS.md`
4. **文件结构** → 查看本文档

---

## 💡 提示

- 所有外部依赖都已 Mock，无需真实硬件
- GUI 测试在无显示服务器时会自动跳过
- 建议先运行 `test_example.py` 了解测试运行方式
- 使用 `pytest -v` 查看详细输出
- 使用 `--cov` 参数生成覆盖率报告

---

**最后更新**: 2026-07-15  
**维护者**: AI Assistant
