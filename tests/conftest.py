"""
Pytest 配置 — 将项目根目录加入 Python 路径
"""
import sys
import os

# 将项目根目录加入 sys.path，使测试文件可以导入项目模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
