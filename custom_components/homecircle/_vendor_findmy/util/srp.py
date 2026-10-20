"""Private modes of the installed pure-Python SRP implementation.

The dependency keeps its mode flags in module globals, including at challenge
time. Separate namespaces let simultaneous exchanges use their required modes
without changing the module used by other integrations or copying SRP equations.
"""

from importlib.util import module_from_spec, spec_from_file_location
from types import ModuleType

import srp._pysrp as _installed


def _backend(name: str, *, omit_username: bool) -> ModuleType:
    """Execute the installed implementation under a private, fixed-mode name."""
    origin = getattr(_installed, "__file__", None)
    if not isinstance(origin, str):
        raise ImportError("The installed pure-Python SRP implementation has no file")
    spec = spec_from_file_location(f"{__name__}.{name}", origin)
    if spec is None or spec.loader is None:
        raise ImportError("The installed pure-Python SRP implementation cannot be loaded")
    backend = module_from_spec(spec)
    spec.loader.exec_module(backend)
    backend.rfc5054_enable(True)
    backend.no_username_in_x(omit_username)
    return backend


gsa = _backend("gsa", omit_username=True)
recovery = _backend("recovery", omit_username=False)
