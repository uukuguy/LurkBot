"""Pytest configuration and fixtures."""

import pytest


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--docker",
        action="store_true",
        default=False,
        help="Run tests that require Docker daemon",
    )
    parser.addoption(
        "--browser",
        action="store_true",
        default=False,
        help="Run tests that require Playwright browser automation",
    )


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "docker: mark test as requiring Docker daemon")
    config.addinivalue_line("markers", "browser: mark test as requiring Playwright")
