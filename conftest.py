"""Pytest root conftest — sets up Python path before test collection"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
