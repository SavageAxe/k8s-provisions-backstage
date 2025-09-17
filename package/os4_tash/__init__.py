"""Public interface for the :mod:`os4_tash` package."""

from .argocd import ArgoCD, build_app_name
from .git import Git
from .vault import Vault
from .errors import (
    ExternalServiceError,
    ArgoCDError,
    GitError,
    VaultError,
)

__all__ = [
    "ArgoCD",
    "Git",
    "Vault",
    "build_app_name",
    "ExternalServiceError",
    "ArgoCDError",
    "GitError",
    "VaultError",
]
