"""
MemoryPoisonDetector — lightweight static analysis for dangerous patterns in tool code.

Part of the Observability (O) layer in the Agora 5-layer architecture.
Scans agent tool code / memory blobs for suspicious patterns that could
indicate memory poisoning, prompt injection, or sandbox escape attempts.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Regex patterns that indicate potentially dangerous operations
DEFAULT_DANGEROUS_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bexec\s*\(", re.IGNORECASE),
    re.compile(r"\beval\s*\(", re.IGNORECASE),
    re.compile(r"\bcompile\s*\(", re.IGNORECASE),
    re.compile(r"\b__import__\s*\(", re.IGNORECASE),
    re.compile(r"\bos\.system\s*\(", re.IGNORECASE),
    re.compile(r"\bsubprocess\b", re.IGNORECASE),
    re.compile(r"\bopen\s*\(.*['\"]w", re.IGNORECASE),
    re.compile(r"__globals__", re.IGNORECASE),
    re.compile(r"__builtins__", re.IGNORECASE),
    re.compile(r"__subclasses__\s*\(", re.IGNORECASE),
    re.compile(r"pickle\.loads\s*\(", re.IGNORECASE),
    re.compile(r"marshal\.loads\s*\(", re.IGNORECASE),
    re.compile(r"base64\.b64decode\s*\(.*\)", re.IGNORECASE),
    re.compile(r"\bgetattr\s*\(.*__", re.IGNORECASE),
    re.compile(r"\bsetattr\s*\(.*__", re.IGNORECASE),
    re.compile(r"\bdelattr\s*\(.*__", re.IGNORECASE),
]

# AST node type names that are inherently dangerous
DEFAULT_DANGEROUS_AST_NODES: Set[str] = set()
# These are caught via pattern scanning, but keeping for extensibility


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class PoisonFinding:
    """A single dangerous pattern found in tool code."""
    pattern_name: str
    line_number: int
    snippet: str
    severity: str  # "low" | "medium" | "high" | "critical"

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] L{self.line_number}: {self.pattern_name} — {self.snippet!r}"


@dataclass
class ScanResult:
    """Result of scanning a piece of tool code."""
    source_name: str
    clean: bool
    findings: List[PoisonFinding] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# MemoryPoisonDetector
# ---------------------------------------------------------------------------

class MemoryPoisonDetector:
    """Scans tool code strings for dangerous patterns using regex + AST analysis.

    Typical usage::

        detector = MemoryPoisonDetector()
        result = detector.scan("def foo():\\n    exec('evil code')")
        if not result.clean:
            for finding in result.findings:
                print(finding)
    """

    def __init__(
        self,
        custom_patterns: Optional[List[re.Pattern]] = None,
        dangerous_ast_nodes: Optional[Set[str]] = None,
    ) -> None:
        self._patterns = custom_patterns or DEFAULT_DANGEROUS_PATTERNS
        self._dangerous_ast_nodes = dangerous_ast_nodes or DEFAULT_DANGEROUS_AST_NODES

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(
        self,
        source: str,
        source_name: str = "<memory>",
    ) -> ScanResult:
        """Scan source code for memory-poisoning patterns.

        Args:
            source:      The code string to analyse.
            source_name: A human-readable label for the source (for reporting).

        Returns:
            A :class:`ScanResult` with any findings.
        """
        findings: List[PoisonFinding] = []

        # 1. Regex-based pattern scanning
        findings.extend(self._scan_regex(source))

        # 2. AST-based structural analysis
        try:
            findings.extend(self._scan_ast(source))
        except SyntaxError:
            findings.append(PoisonFinding(
                pattern_name="syntax_error",
                line_number=0,
                snippet="<invalid Python>",
                severity="medium",
            ))

        return ScanResult(
            source_name=source_name,
            clean=len(findings) == 0,
            findings=findings,
        )

    # ------------------------------------------------------------------
    # Internal: regex scanning
    # ------------------------------------------------------------------

    def _scan_regex(self, source: str) -> List[PoisonFinding]:
        """Run all registered regex patterns against the source."""
        findings: List[PoisonFinding] = []

        for pattern in self._patterns:
            for match in pattern.finditer(source):
                line_number = source[:match.start()].count("\n") + 1
                snippet = source[max(0, match.start() - 20): match.end() + 20].strip()
                severity = self._classify_severity(pattern.pattern)

                findings.append(PoisonFinding(
                    pattern_name=pattern.pattern[:60],
                    line_number=line_number,
                    snippet=snippet,
                    severity=severity,
                ))

        return findings

    # ------------------------------------------------------------------
    # Internal: AST scanning
    # ------------------------------------------------------------------

    def _scan_ast(self, source: str) -> List[PoisonFinding]:
        """Analyse the AST for dangerous structural patterns."""
        findings: List[PoisonFinding] = []

        try:
            tree = ast.parse(source)
        except SyntaxError:
            raise  # let caller handle

        for node in ast.walk(tree):
            # Detect direct calls to exec/eval/compile
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in ("exec", "eval", "compile", "__import__"):
                        findings.append(PoisonFinding(
                            pattern_name=f"dangerous_call:{func_name}",
                            line_number=getattr(node, "lineno", 0),
                            snippet=ast.unparse(node)[:80],
                            severity="critical",
                        ))
                elif isinstance(node.func, ast.Attribute):
                    attr_name = f"{self._get_attribute_chain(node.func)}"
                    if "os.system" in attr_name or "subprocess" in attr_name:
                        findings.append(PoisonFinding(
                            pattern_name=f"dangerous_attr_call:{attr_name}",
                            line_number=getattr(node, "lineno", 0),
                            snippet=ast.unparse(node)[:80],
                            severity="critical",
                        ))

        return findings

    @staticmethod
    def _get_attribute_chain(node: ast.AST) -> str:
        """Rebuild a dotted attribute chain like ``os.path.join`` from an AST node."""
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return ".".join(reversed(parts))

    # ------------------------------------------------------------------
    # Severity classification
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_severity(pattern_text: str) -> str:
        """Classify pattern severity based on the danger level of the match."""
        critical_keywords = ["exec", "eval", "compile", "__import__", "os.system", "subprocess"]
        high_keywords = ["__globals__", "__builtins__", "__subclasses__", "pickle.loads", "marshal.loads"]
        medium_keywords = ["getattr.*__", "setattr.*__", "delattr.*__", "open.*w"]

        for kw in critical_keywords:
            if kw in pattern_text.lower():
                return "critical"
        for kw in high_keywords:
            if kw in pattern_text.lower():
                return "high"
        for kw in medium_keywords:
            if kw in pattern_text.lower():
                return "medium"
        return "low"

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def is_clean(self, source: str) -> bool:
        """Quick check — returns ``True`` if no dangerous patterns found."""
        return self.scan(source).clean
