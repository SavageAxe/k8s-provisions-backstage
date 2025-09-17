"""Application hooks package.

Provides a simple registry (HOOK_REGISTRY) that maps function names to callables.
Any callable defined in modules under this package is automatically registered
under its attribute name. This enables mapping hook events to custom function names
via configuration (e.g., {"pre_create_hook": "create_org"}).
"""

from typing import Callable, Any, Dict
import inspect
import importlib
import pkgutil

# Auto-discover all callables defined in modules under app.hooks
HOOK_REGISTRY: Dict[str, Callable[..., Any]] = {}

def _discover() -> None:
    package_name = __name__
    package = importlib.import_module(package_name)
    for finder, name, ispkg in pkgutil.iter_modules(package.__path__, package_name + "."):
        try:
            mod = importlib.import_module(name)
        except Exception:
            continue
        for attr_name in dir(mod):
            if attr_name.startswith("_"):
                continue
            obj = getattr(mod, attr_name)
            if callable(obj):
                HOOK_REGISTRY[attr_name] = obj

_discover()
