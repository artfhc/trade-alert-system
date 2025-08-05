"""
Application version management
"""

__version__ = "0.0.1"

def get_version() -> str:
    """Get the current application version"""
    return __version__

def get_version_info() -> dict:
    """Get detailed version information"""
    major, minor, patch = __version__.split('.')
    return {
        "version": __version__,
        "major": int(major),
        "minor": int(minor), 
        "patch": int(patch)
    }