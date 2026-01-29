"""
Browser Routes - HTTP 路由端点

对标 MoltBot src/browser/routes/
"""

from .act import router as act_router
from .navigate import router as navigate_router
from .screenshot import router as screenshot_router
from .tabs import router as tabs_router

__all__ = [
    "act_router",
    "navigate_router",
    "screenshot_router",
    "tabs_router",
]
