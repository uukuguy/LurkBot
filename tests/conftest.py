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


def pytest_collection_modifyitems(config, items):
    """Skip tests based on markers and command line options."""
    # Skip docker tests unless --docker flag is provided
    if not config.getoption("--docker"):
        skip_docker = pytest.mark.skip(reason="need --docker option to run")
        for item in items:
            if "docker" in item.keywords:
                item.add_marker(skip_docker)

    # Skip browser tests unless --browser flag is provided
    if not config.getoption("--browser"):
        skip_browser = pytest.mark.skip(reason="need --browser option to run")
        for item in items:
            if "browser" in item.keywords:
                item.add_marker(skip_browser)
