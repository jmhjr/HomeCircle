"""Read the already-installed parent-package environmental fence."""
from custom_components._ordinary_boundary import snapshot, StartupBoundaryRefused as StartupBoundaryRefused

def install(hass):
    # Never import HomeCircle or patch it here: discovery installed the fence.
    return snapshot()
