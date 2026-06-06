"""Tool forge CI/CD pipeline with 4-gate static/security/sandbox/high-risk checks."""

import ast
import re
from typing import Any, Optional

from .sandbox import FirecrackerSandbox, SandboxResult


class GateResult:
    """Result of a single CI/CD gate check."""

    def __init__(self, passed: bool, details: Optional[str] = None):
        self.passed = passed
        self.details = details or ""

    def __repr__(self) -> str:
        return f"GateResult(passed={self.passed}, details={self.details!r})"


class ToolForge:
    """CI/CD pipeline for tool development with four validation gates.

    Pipeline order:
      1. _gate_static   — AST-level linting and structure checks.
      2. _gate_security — Detect dangerous imports / patterns.
      3. _gate_sandbox  — Execute in FirecrackerSandbox mock.
      4. _is_high_risk  — Flag for manual review if risk score is high.
    """

    def __init__(self):
        self._sandbox = FirecrackerSandbox(sandbox_id="tool-forge")
        self._risk_patterns: list[re.Pattern] = [
            re.compile(r"(?i)subprocess|Popen|popen"),
            re.compile(r"(?i)exec\s*\(|eval\s*\(|compile\s*\("),
            re.compile(r"(?i)pickle|shelve|marshal"),
            re.compile(r"(?i)bytecode|\.pyc|__pycache__"),
            re.compile(r"(?i)socket\.|connect\(|bind\("),
            re.compile(r"(?i)ctypes|dlopen|ffi\."),
        ]

    def run_pipeline(self, tool_code: str, tool_name: str = "") -> dict:
        """Run the full 4-gate CI/CD pipeline on tool source code.

        Args:
            tool_code: Source code of the tool.
            tool_name: Optional name for reporting.

        Returns:
            Dict with keys: passed (bool), gates (list of gate results),
            is_high_risk (bool), summary (str).
        """
        gates = []
        all_passed = True

        # Gate 1: Static analysis
        gate1 = self._gate_static(tool_code)
        gates.append({"name": "static", "result": gate1})
        if not gate1.passed:
            all_passed = False

        # Gate 2: Security scan
        gate2 = self._gate_security(tool_code)
        gates.append({"name": "security", "result": gate2})
        if not gate2.passed:
            all_passed = False

        # Gate 3: Sandbox execution
        gate3 = self._gate_sandbox(tool_code)
        gates.append({"name": "sandbox", "result": gate3})
        if not gate3.passed:
            all_passed = False

        # Gate 4: High risk assessment
        is_high_risk = self._is_high_risk(tool_code)
        gates.append({"name": "high_risk", "result": GateResult(passed=True, details=str(is_high_risk))})

        return {
            "tool_name": tool_name,
            "passed": all_passed,
            "gates": gates,
            "is_high_risk": is_high_risk,
            "summary": self._build_summary(all_passed, is_high_risk, gates),
        }

    def _gate_static(self, tool_code: str) -> GateResult:
        """Gate 1: Static AST analysis — check for basic structural issues."""
        try:
            tree = ast.parse(tool_code)
        except SyntaxError as e:
            return GateResult(passed=False, details=f"Syntax error: {e}")

        # Check for a function or class definition (minimal structure)
        has_def = any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            for node in ast.walk(tree)
        )
        if not has_def:
            return GateResult(
                passed=False,
                details="No function or class definition found in tool code.",
            )

        return GateResult(passed=True, details="Static analysis passed.")

    def _gate_security(self, tool_code: str) -> GateResult:
        """Gate 2: Security scan — detect dangerous imports and patterns."""
        dangerous_imports = {
            "os", "subprocess", "sys", "shutil", "socket", "ctypes",
            "multiprocessing", "threading", "signal", "pickle", "shelve",
            "importlib", "marshal",
        }

        try:
            tree = ast.parse(tool_code)
        except SyntaxError as e:
            return GateResult(passed=False, details=f"Cannot parse: {e}")

        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split(".")[0])

        found_dangerous = [m for m in imports if m in dangerous_imports]
        if found_dangerous:
            return GateResult(
                passed=False,
                details=f"Dangerous imports detected: {', '.join(found_dangerous)}",
            )

        # Check for dangerous function calls in AST
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("exec", "eval", "compile", "__import__"):
                    return GateResult(
                        passed=False,
                        details=f"Dangerous call '{node.func.id}()' is not allowed.",
                    )

        return GateResult(passed=True, details="Security scan passed.")

    def _gate_sandbox(self, tool_code: str) -> GateResult:
        """Gate 3: Execute in the FirecrackerSandbox (mock)."""
        result: SandboxResult = self._sandbox.execute(tool_code)
        if not result.success:
            return GateResult(passed=False, details=f"Sandbox failed: {result.error}")
        return GateResult(passed=True, details=f"Sandbox passed: {result.output}")

    def _is_high_risk(self, tool_code: str) -> bool:
        """Gate 4: Determine if tool code should be flagged for manual review.

        Returns True if any high-risk pattern is detected.
        """
        for pattern in self._risk_patterns:
            if pattern.search(tool_code):
                return True
        return False

    @staticmethod
    def _build_summary(passed: bool, high_risk: bool, gates: list[dict]) -> str:
        """Build a human-readable pipeline summary."""
        gate_names = ", ".join(g["name"] for g in gates)
        verdict = "PASSED" if passed else "FAILED"
        risk_tag = " [HIGH RISK — manual review required]" if high_risk else ""
        failed_gates = [g["name"] for g in gates if not g["result"].passed]
        fail_msg = f" (failed: {', '.join(failed_gates)})" if failed_gates else ""
        return f"Pipeline {verdict}: gates=[{gate_names}]{fail_msg}{risk_tag}"
