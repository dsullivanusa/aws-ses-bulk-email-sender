"""lib package for shared utilities.

Keep this package lightweight so it can be imported in local test helpers without creating AWS clients at import time.
"""

__all__ = [
    "email_utils",
]
