"""
Pytest configuration for Loki Server tests.
"""
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "security: marks security-related tests"
    )
    config.addinivalue_line(
        "markers", "docker: marks Docker-related tests"
    )
    config.addinivalue_line(
        "markers", "api: marks API endpoint tests"
    )
