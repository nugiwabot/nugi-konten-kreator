"""
security.py
===========
Security, path confinement, and permission boundary engine for Nugi Konten Kreator MCP.
Guarantees:
1. Strictly confines all operations inside repository root.
2. Rejects path traversal and symlink escapes.
3. Classifies paths:
   - output/ is writable workspace (ALLOW write/create/mkdir).
   - everything outside output/ is PROTECTED (requires proposal approval).
4. Masks secrets (.env, tokens, credentials).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional, Set


SECRET_FILENAME_PATTERNS = {
    r"^\.env$",
    r"^\.env\.(local|production|prod|development|dev)$",
    r".*secret.*",
    r".*credential.*",
    r".*token.*\.json$",
    r".*id_rsa.*",
}

SECRET_VALUE_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|auth|bearer)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?"),
]


class SecurityError(PermissionError):
    """Raised when an operation attempts to bypass MCP security boundaries."""
    pass


def resolve_safe_path(repo_root: Path, user_path: str | Path) -> Path:
    """
    Resolve and canonicalize path within the repository root.
    Strictly forbids path traversal, symlink escape, or accessing external paths.
    """
    root_resolved = repo_root.resolve()
    target = Path(user_path)
    
    if not target.is_absolute():
        target = root_resolved / target
        
    resolved_target = target.resolve()
    
    # Check if resolved path is contained within repo_root
    try:
        resolved_target.relative_to(root_resolved)
    except ValueError:
        raise SecurityError(
            f"Path traversal blocked: '{user_path}' resolves outside repository root '{root_resolved}'"
        )
        
    return resolved_target


def is_output_path(repo_root: Path, target_path: Path) -> bool:
    """
    Returns True if target_path is within the 'output/' workspace.
    """
    out_root = (repo_root.resolve() / "output").resolve()
    try:
        target_path.resolve().relative_to(out_root)
        return True
    except ValueError:
        return False


def is_protected_path(repo_root: Path, target_path: Path) -> bool:
    """
    Returns True if target_path is a protected source file (outside output/).
    """
    return not is_output_path(repo_root, target_path)


def is_secret_file(target_path: Path) -> bool:
    """
    Checks if a file is a sensitive secret / environment file.
    .env.example is explicitly allowed; actual .env is blocked.
    """
    name = target_path.name
    if name == ".env.example":
        return False
    for pat in SECRET_FILENAME_PATTERNS:
        if re.match(pat, name, re.IGNORECASE):
            return True
    return False


def mask_secrets(content: str) -> str:
    """
    Masks credentials, API keys, and sensitive tokens in strings.
    """
    if not content:
        return ""
    masked = content
    for pat in SECRET_VALUE_PATTERNS:
        masked = pat.sub(r"\1: [REDACTED]", masked)
    return masked
