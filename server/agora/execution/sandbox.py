"""Mock Firecracker sandbox for safe code execution with import validation."""

import ast
import re
from typing import Any, Optional

# Modules considered safe for execution
SAFE_IMPORTS: set[str] = {
    "math",
    "json",
    "random",
    "time",
    "datetime",
    "collections",
    "itertools",
    "functools",
    "re",
    "statistics",
    "typing",
    "decimal",
    "fractions",
    "uuid",
    "dataclasses",
}

# Modules that are explicitly forbidden
DANGEROUS_IMPORTS: set[str] = {
    "os",
    "subprocess",
    "sys",
    "shutil",
    "socket",
    "requests",
    "http",
    "urllib",
    "pathlib",
    "ctypes",
    "multiprocessing",
    "threading",
    "signal",
    "pickle",
    "shelve",
    "importlib",
    "builtins",
}

# Patterns that indicate dangerous operations
DANGEROUS_PATTERNS: list[re.Pattern] = [
    re.compile(r"__import__\s*\("),
    re.compile(r"exec\s*\("),
    re.compile(r"eval\s*\("),
    re.compile(r"open\s*\("),
    re.compile(r"compile\s*\("),
]


class SandboxResult:
    """Result of a sandbox execution."""

    def __init__(self, success: bool, output: Any = None, error: Optional[str] = None):
        self.success = success
        self.output = output
        self.error = error

    def __repr__(self) -> str:
        if self.success:
            return f"SandboxResult(success=True, output={self.output!r})"
        return f"SandboxResult(success=False, error={self.error!r})"


class FirecrackerSandbox:
    """Mock Firecracker-based sandbox for agent code execution.

    Currently validates code statically (no dangerous imports/patterns)
    without actually running a microVM. Real execution will be added
    when Firecracker support is integrated.
    """

    def __init__(self, sandbox_id: Optional[str] = None, timeout: int = 30):
        self.sandbox_id = sandbox_id or "mock-sandbox"
        self.timeout = timeout

    def execute(self, code: str, context: Optional[dict] = None) -> SandboxResult:
        """Validate and "execute" code in the sandbox.

        Currently performs static analysis:
        - Parses the AST to find all import statements.
        - Rejects any import from the DANGEROUS_IMPORTS set.
        - Rejects any code matching DANGEROUS_PATTERNS (exec, eval, etc.).
        - Warns about imports outside the SAFE_IMPORTS set.

        Args:
            code: Python source code to validate.
            context: Optional context dict (ignored in mock mode).

        Returns:
            SandboxResult with success=True if code passes validation.
        """
        # Check dangerous patterns first
        for pattern in DANGEROUS_PATTERNS:
            if pattern.search(code):
                return SandboxResult(
                    success=False,
                    error=f"Dangerous operation detected: matches {pattern.pattern}",
                )

        # Parse AST for import validation
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return SandboxResult(success=False, error=f"Syntax error: {e}")

        # Collect all imports
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split(".")[0])

        # Check for dangerous imports
        for mod in imports:
            if mod in DANGEROUS_IMPORTS:
                return SandboxResult(
                    success=False,
                    error=f"Import of dangerous module '{mod}' is not allowed.",
                )

        # Warn about unsafe (not in safe list) imports — still pass
        unsafe_imports = [m for m in imports if m not in SAFE_IMPORTS]
        if unsafe_imports:
            # In mock mode we warn but allow
            return SandboxResult(
                success=True,
                output={
                    "status": "passed_with_warnings",
                    "warnings": [
                        f"Import '{m}' is not in the approved safe list."
                        for m in unsafe_imports
                    ],
                    "code_length": len(code),
                },
            )

        # Everything looks safe
        return SandboxResult(
            success=True,
            output={
                "status": "passed",
                "imports_checked": imports,
                "code_length": len(code),
            },
        )
