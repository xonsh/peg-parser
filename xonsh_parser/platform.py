import platform
import sys

from .lazyasd import LazyBool

PYTHON_VERSION_INFO = sys.version_info[:3]
ON_WINDOWS = LazyBool(lambda: platform.system() == "Windows", globals(), "ON_WINDOWS")
