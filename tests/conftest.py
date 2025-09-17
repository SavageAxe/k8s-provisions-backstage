import pytest


def pytest_configure(config):
    # Register markers used across the suite
    config.addinivalue_line("markers", "asyncio: mark test as async")

