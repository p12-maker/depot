import csv
import json
import subprocess
import threading
import time
from datetime import datetime

import psutil

# 兼容 Python 3.12 下 GPUtil 依赖 distutils 的情况。
try:
    import GPUtil
except ModuleNotFoundError as e:
    if "distutils" in str(e):
        try:
            import setuptools  # noqa: F401
            import GPUtil
        except (ModuleNotFoundError, ImportError):
            GPUtil = None
            print("GPU 监控模块加载失败，将跳过 GPU 信息")
    else:
        GPUtil = None
        print(f"GPU 监控模块加载失败，将跳过 GPU 信息: {e}")


class SystemMonitor:
    """系统监控核心类。"""

    def __init__(self):
        self.last_io_counters = psutil.disk_io_counters()
        self.last_io_time = time.time()
        self.last_net_counters = psutil.net_io_counters()
        self.last_net_time = time.time()
        self.gpu_cache = None
        self.gpu_cache_time = 0
        self.gpu_cache_ttl = 10
        self.gpu_update_running = False
        self.gpu_lock = threading.Lock()
        self.nvidia_smi_available = True
        self.windows_gpu_names_cache = None

    def get_cpu_info(self):
        """获取 CPU 使用率。"""
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            return {
                "usage": cpu_percent,
                "cores": psutil.cpu_count(logical=False),
                "threads": psutil.cpu_count(logical=True),
            }
        except Exception as e:
            print(f"获取 CPU 信息失败: {e}")
            return {"usage": 0, "cores": 0, "threads": 0}

    def get_memory_info(self):
        """获取内存使用情况。"""
        try:
            mem = psutil.virtual_memory()
            return {
                "total": mem.total,
                "used": mem.used,
                "free": mem.free,
                "percent": mem.percent,
            }
        except Exception as e:
            print(f"获取内存信息失败: {e}")
            return {"total": 0, "used": 0, "free": 0, "percent": 0}

    def get_gpu_info(self):
        """获取 GPU 使用情况。"""
        now = time.time()
        if self.gpu_cache and now - self.gpu_cache_time < self.gpu_cache_ttl:
            return self.gpu_cache

        gpu = None
        if GPUtil is not None:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    gpu = {
                        "name": gpu.name,
                        "load": gpu.load * 100,
                        "memory_used": gpu.memoryUsed,
                        "memory_total": gpu.memoryTotal,
                        "temperature": gpu.temperature,
                        "source": "GPUtil",
                    }
                    self.gpu_cache = gpu
                    self.gpu_cache_time = now
                    return gpu
            except Exception as e:
                print(f"GPUtil 获取 GPU 信息失败，尝试 nvidia-smi: {e}")

        gpu = self._get_gpu_info_from_nvidia_smi() if self.nvidia_smi_available else None
        if gpu:
            self.gpu_cache = gpu
            self.gpu_cache_time = now
            return gpu
        gpu = self._get_gpu_info_from_windows()
        self.gpu_cache = gpu
        self.gpu_cache_time = now
        return gpu

    def _get_gpu_info_from_nvidia_smi(self):
        """使用 nvidia-smi 作为 GPU 读取兜底方案。"""
        try:
            cmd = [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None

            row = next(csv.reader([result.stdout.strip().splitlines()[0]], skipinitialspace=True))
            if len(row) < 5:
                return None

            return {
                "name": row[0],
                "load": float(row[1]),
                "memory_used": float(row[2]),
                "memory_total": float(row[3]),
                "temperature": float(row[4]),
                "source": "nvidia-smi",
            }
        except FileNotFoundError:
            self.nvidia_smi_available = False
        except Exception as e:
            print(f"nvidia-smi 获取 GPU 信息失败: {e}")
            return None

    def _run_powershell_json(self, command, timeout=4):
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    command,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None
            return json.loads(result.stdout)
        except Exception:
            return None

    def _get_windows_gpu_names(self):
        if self.windows_gpu_names_cache is not None:
            return self.windows_gpu_names_cache

        command = (
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name,AdapterRAM | ConvertTo-Json -Compress"
        )
        data = self._run_powershell_json(command)
        if not data:
            self.windows_gpu_names_cache = []
            return []
        if isinstance(data, dict):
            data = [data]
        self.windows_gpu_names_cache = [
            {
                "name": item.get("Name") or "GPU",
                "memory_total": (item.get("AdapterRAM") or 0) / (1024 * 1024),
            }
            for item in data
            if item.get("Name")
        ]
        return self.windows_gpu_names_cache

    def _get_windows_gpu_load(self):
        command = (
            "$samples = (Get-Counter '\\GPU Engine(*)\\Utilization Percentage' "
            "-ErrorAction SilentlyContinue).CounterSamples; "
            "$samples | Where-Object { $_.InstanceName -match 'engtype_3D|engtype_Compute|engtype_Copy|engtype_Video' } | "
            "Measure-Object CookedValue -Sum | Select-Object -ExpandProperty Sum | ConvertTo-Json -Compress"
        )
        data = self._run_powershell_json(command)
        try:
            return min(max(float(data or 0), 0), 100)
        except (TypeError, ValueError):
            return 0

    def _get_gpu_info_from_windows(self):
        """读取 Windows 通用 GPU 信息，兼容 Intel/AMD 核显。"""
        names = self._get_windows_gpu_names()
        if not names:
            return None

        primary = names[0]
        return {
            "name": primary["name"],
            "load": self._get_windows_gpu_load(),
            "memory_used": 0,
            "memory_total": primary.get("memory_total") or 0,
            "temperature": None,
            "source": "windows",
        }

    def get_gpu_info(self):
        """Return cached GPU data and refresh stale data in a background thread."""
        now = time.time()
        with self.gpu_lock:
            cached_gpu = self.gpu_cache
            cache_time = self.gpu_cache_time
            update_running = self.gpu_update_running

        if cached_gpu and now - cache_time < self.gpu_cache_ttl:
            return cached_gpu

        if not update_running:
            with self.gpu_lock:
                if not self.gpu_update_running:
                    self.gpu_update_running = True
                    threading.Thread(target=self._refresh_gpu_cache, daemon=True).start()

        return cached_gpu

    def _refresh_gpu_cache(self):
        try:
            gpu = self._read_gpu_info_sync()
            with self.gpu_lock:
                self.gpu_cache = gpu
                self.gpu_cache_time = time.time()
        finally:
            with self.gpu_lock:
                self.gpu_update_running = False

    def _read_gpu_info_sync(self):
        gpu = None
        if GPUtil is not None:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    return {
                        "name": gpu.name,
                        "load": gpu.load * 100,
                        "memory_used": gpu.memoryUsed,
                        "memory_total": gpu.memoryTotal,
                        "temperature": gpu.temperature,
                        "source": "GPUtil",
                    }
            except Exception as e:
                print(f"GPUtil 获取 GPU 信息失败，尝试 nvidia-smi: {e}")

        gpu = self._get_gpu_info_from_nvidia_smi() if self.nvidia_smi_available else None
        if gpu:
            return gpu
        return self._get_gpu_info_from_windows()

    def get_disk_info(self):
        """获取磁盘使用情况和读写吞吐。"""
        try:
            partitions = []
            for partition in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    partitions.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent,
                    })
                except PermissionError:
                    continue

            current_io = psutil.disk_io_counters()
            current_time = time.time()

            read_speed = 0
            write_speed = 0
            if self.last_io_counters and current_io:
                time_delta = current_time - self.last_io_time
                if time_delta > 0:
                    read_speed = max(
                        0,
                        (current_io.read_bytes - self.last_io_counters.read_bytes) / time_delta,
                    )
                    write_speed = max(
                        0,
                        (current_io.write_bytes - self.last_io_counters.write_bytes) / time_delta,
                    )

            self.last_io_counters = current_io
            self.last_io_time = current_time

            return {
                "partitions": partitions,
                "read_speed": read_speed,
                "write_speed": write_speed,
            }
        except Exception as e:
            print(f"获取磁盘信息失败: {e}")
            return {"partitions": [], "read_speed": 0, "write_speed": 0}

    def get_network_info(self):
        """获取网络上下行吞吐。"""
        try:
            current_net = psutil.net_io_counters()
            current_time = time.time()

            sent_speed = 0
            recv_speed = 0
            if self.last_net_counters and current_net:
                time_delta = current_time - self.last_net_time
                if time_delta > 0:
                    sent_speed = max(
                        0,
                        (current_net.bytes_sent - self.last_net_counters.bytes_sent) / time_delta,
                    )
                    recv_speed = max(
                        0,
                        (current_net.bytes_recv - self.last_net_counters.bytes_recv) / time_delta,
                    )

            self.last_net_counters = current_net
            self.last_net_time = current_time

            return {
                "sent_speed": sent_speed,
                "recv_speed": recv_speed,
                "bytes_sent": current_net.bytes_sent if current_net else 0,
                "bytes_recv": current_net.bytes_recv if current_net else 0,
            }
        except Exception as e:
            print(f"获取网络信息失败: {e}")
            return {
                "sent_speed": 0,
                "recv_speed": 0,
                "bytes_sent": 0,
                "bytes_recv": 0,
            }

    def get_all_info(self):
        """获取所有系统信息。"""
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cpu": self.get_cpu_info(),
            "memory": self.get_memory_info(),
            "gpu": self.get_gpu_info(),
            "disk": self.get_disk_info(),
            "network": self.get_network_info(),
        }
