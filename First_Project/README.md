# 系统监控桌面组件

一个 Windows 桌面系统监控工具，用 PyQt5 显示 CPU、内存、GPU、磁盘和网络吞吐数据。

## 功能

- 圆盘仪表盘展示 CPU、内存、GPU、磁盘和网络状态
- 网络显示实时上行/下行吞吐
- 磁盘可在设置中筛选指定分区
- GPU 优先使用 GPUtil，失败时回退到 `nvidia-smi`
- 支持方形布局和横向布局
- 支持小型、中型、大型三种尺寸
- 支持配色、透明度、刷新间隔设置
- 支持从 `fonts` 目录加载本地字体
- 支持系统托盘菜单和开机自动启动
- 拖动窗口靠近屏幕边缘时自动吸附

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

也可以双击 `start_app.bat` 或 `start_monitor.bat`。

## 文件说明

- `main.py`：主程序、界面、托盘菜单和设置窗口
- `system_monitor.py`：系统监控数据采集
- `settings.json`：用户配置
- `requirements.txt`：Python 依赖
- `start_monitor.bat`：快速启动程序
- `start_app.bat`：检查 Python、安装依赖并启动程序
- `setup_autostart.bat`：手动设置或取消开机启动
- `enable_autostart_admin.bat`：管理员模式设置开机启动
- `install_python.bat`：安装 Python 到桌面目录
- `package.py` / `package_app.bat`：打包项目文件为 `SystemMonitor.zip`
- `fonts/`：本地字体目录，可放入 `.ttf/.otf/.ttc` 字体文件

## 注意事项

1. GPU 监控主要支持 NVIDIA 显卡。
2. 如果没有 NVIDIA 显卡、驱动或 `nvidia-smi`，GPU 会显示“未检测到 NVIDIA”。
3. 开机自动启动写入当前用户注册表项：`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`。
4. 网络仪表盘的百分比是活动强度，不是网卡真实带宽占用；默认以 10MB/s 作为 100% 参考值。
5. SF Pro 请从 Apple Developer Fonts 官方页面下载：https://developer.apple.com/fonts/。
