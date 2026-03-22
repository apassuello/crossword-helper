#!/usr/bin/env python3
"""process_tool_sources.py

Analyse source files downloaded by fetch_tool_sources.sh and print a
structured summary for each open-source crossword tool.

The script performs static analysis (regex-based extraction) -- it does NOT
execute any of the downloaded code.

Usage:
    python scripts/research/process_tool_sources.py [--input-dir DIR]

Defaults to data/research/ as input directory.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_read(path: Path, encoding: str = "utf-8") -> str:
    """Read a file, returning empty string on failure."""
    try:
        return path.read_text(encoding=encoding, errors="replace")
    except (OSError, UnicodeDecodeError):
        return ""


def count_lines(text: str) -> int:
    return text.count("\n") + (1 if text and not text.endswith("\n") else 0)


def extract_functions(text: str, lang: str) -> List[str]:
    """Extract top-level function/method names from source text."""
    if lang == "js":
        # JS: function name(, name(, async name(, name = function
        patterns = [
            r"(?:async\s+)?function\s+(\w+)\s*\(",
            r"(\w+)\s*\((?:[^)]*)\)\s*\{",
            r"(\w+)\s*=\s*(?:async\s+)?function",
            r"(\w+)\s*=\s*\([^)]*\)\s*=>",
        ]
    elif lang == "ts":
        patterns = [
            r"(?:export\s+)?(?:async\s+)?function\s+(\w+)",
            r"(\w+)\s*\([^)]*\)(?:\s*:\s*\w+)?\s*\{",
        ]
    elif lang == "py":
        patterns = [
            r"^def\s+(\w+)\s*\(",
            r"^class\s+(\w+)",
        ]
    else:
        return []

    names: List[str] = []
    for pat in patterns:
        names.extend(re.findall(pat, text, re.MULTILINE))
    # deduplicate preserving order
    seen = set()
    result = []
    for n in names:
        if n not in seen and not n.startswith("_"):
            seen.add(n)
            result.append(n)
    return result


def find_keywords(text: str, keywords: List[str]) -> Dict[str, int]:
    """Count occurrences of each keyword (case-insensitive)."""
    counts: Dict[str, int] = {}
    lower = text.lower()
    for kw in keywords:
        c = lower.count(kw.lower())
        if c > 0:
            counts[kw] = c
    return counts


# ---------------------------------------------------------------------------
# Per-tool analysers
# ---------------------------------------------------------------------------

ALGORITHM_KEYWORDS = [
    "beam search", "beam_search", "beamSearch",
    "backtrack", "backtracking",
    "constraint", "CSP", "arc consistency", "AC-3", "AC3",
    "heuristic", "MRV", "minimum remaining",
    "greedy", "DFS", "BFS", "priority queue",
    "brute force", "bruteforce",
    "lookahead", "propagat",
    "nogood", "tabu",
]

UX_KEYWORDS = [
    "undo", "redo", "keyboard", "shortcut",
    "symmetry", "symmetric",
    "nina", "rebus",
    "clue", "export", "import",
    "pause", "resume", "cancel",
    "progress", "worker", "Web Worker",
    "theme", "preferred", "preflex",
    "blacklist", "exclusion",
]

EXPORT_KEYWORDS = [
    ".puz", "ipuz", "exolve", "PDF", "pdf",
    "XPF", "xpf", "SVG", "svg",
    "HTML", "html", "JSON", "json",
]


@dataclass
class FileInfo:
    path: Path
    lang: str
    lines: int
    functions: List[str]
    algo_hits: Dict[str, int]
    ux_hits: Dict[str, int]
    export_hits: Dict[str, int]


@dataclass
class ToolSummary:
    name: str
    directory: str
    files: List[FileInfo] = field(default_factory=list)
    total_lines: int = 0


def analyse_file(path: Path) -> Optional[FileInfo]:
    """Analyse a single source file."""
    ext = path.suffix.lower()
    lang_map = {
        ".js": "js", ".ts": "ts", ".tsx": "ts",
        ".py": "py", ".md": "md",
    }
    lang = lang_map.get(ext)
    if lang is None:
        return None

    text = safe_read(path)
    if not text:
        return None

    lines = count_lines(text)
    functions = extract_functions(text, lang) if lang != "md" else []
    algo_hits = find_keywords(text, ALGORITHM_KEYWORDS)
    ux_hits = find_keywords(text, UX_KEYWORDS)
    export_hits = find_keywords(text, EXPORT_KEYWORDS)

    return FileInfo(
        path=path, lang=lang, lines=lines,
        functions=functions,
        algo_hits=algo_hits, ux_hits=ux_hits, export_hits=export_hits,
    )


def analyse_tool(name: str, tool_dir: Path) -> Optional[ToolSummary]:
    """Walk a tool directory and analyse all source files."""
    if not tool_dir.is_dir():
        return None

    summary = ToolSummary(name=name, directory=str(tool_dir))

    for root, _dirs, filenames in os.walk(tool_dir):
        for fname in sorted(filenames):
            fpath = Path(root) / fname
            info = analyse_file(fpath)
            if info:
                summary.files.append(info)
                summary.total_lines += info.lines

    return summary


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

SEPARATOR = "=" * 72

def print_tool_report(summary: ToolSummary) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {summary.name}")
    print(f"  {summary.directory}")
    print(SEPARATOR)
    print(f"  Total files analysed: {len(summary.files)}")
    print(f"  Total lines: {summary.total_lines:,}")

    # Language breakdown
    by_lang: Dict[str, int] = defaultdict(int)
    for f in summary.files:
        by_lang[f.lang] += f.lines
    print(f"  Language breakdown: {dict(by_lang)}")

    # Top files by size
    print("\n  Largest files:")
    for f in sorted(summary.files, key=lambda x: x.lines, reverse=True)[:5]:
        relpath = f.path.relative_to(summary.directory)
        print(f"    {relpath}: {f.lines:,} lines ({f.lang})")

    # Algorithm keywords
    combined_algo: Dict[str, int] = defaultdict(int)
    for f in summary.files:
        for kw, c in f.algo_hits.items():
            combined_algo[kw] += c
    if combined_algo:
        print("\n  Algorithm signals:")
        for kw, c in sorted(combined_algo.items(), key=lambda x: -x[1]):
            print(f"    {kw}: {c}")

    # UX keywords
    combined_ux: Dict[str, int] = defaultdict(int)
    for f in summary.files:
        for kw, c in f.ux_hits.items():
            combined_ux[kw] += c
    if combined_ux:
        print("\n  UX feature signals:")
        for kw, c in sorted(combined_ux.items(), key=lambda x: -x[1]):
            print(f"    {kw}: {c}")

    # Export formats
    combined_export: Dict[str, int] = defaultdict(int)
    for f in summary.files:
        for kw, c in f.export_hits.items():
            combined_export[kw] += c
    if combined_export:
        print("\n  Export format signals:")
        for kw, c in sorted(combined_export.items(), key=lambda x: -x[1]):
            print(f"    {kw}: {c}")

    # Key functions (from the largest non-md files)
    code_files = [f for f in summary.files if f.lang != "md" and f.functions]
    code_files.sort(key=lambda x: x.lines, reverse=True)
    if code_files:
        print("\n  Key functions/classes (top files):")
        for f in code_files[:4]:
            relpath = f.path.relative_to(summary.directory)
            funcs = f.functions[:15]
            print(f"    {relpath}:")
            for fn in funcs:
                print(f"      - {fn}")
            if len(f.functions) > 15:
                print(f"      ... and {len(f.functions) - 15} more")


def print_cross_tool_comparison(summaries: List[ToolSummary]) -> None:
    print(f"\n{'=' * 72}")
    print("  CROSS-TOOL COMPARISON")
    print(f"{'=' * 72}")

    # Size comparison
    print("\n  Codebase size:")
    for s in sorted(summaries, key=lambda x: x.total_lines, reverse=True):
        print(f"    {s.name:30s} {s.total_lines:>8,} lines  ({len(s.files)} files)")

    # Algorithm presence
    algo_keys = [
        "beam search", "beamSearch", "beam_search",
        "backtrack", "backtracking",
        "constraint", "CSP",
        "heuristic", "MRV",
        "greedy", "brute force", "bruteforce",
        "lookahead", "propagat",
        "priority queue",
    ]
    print("\n  Algorithm techniques detected:")
    header = f"    {'Technique':25s}"
    for s in summaries:
        header += f" {s.name[:12]:>12s}"
    print(header)
    print("    " + "-" * (25 + 13 * len(summaries)))

    for kw in algo_keys:
        row = f"    {kw:25s}"
        found_any = False
        for s in summaries:
            total = 0
            for f in s.files:
                total += f.algo_hits.get(kw, 0)
            marker = f"{total:>12d}" if total else f"{'--':>12s}"
            if total:
                found_any = True
            row += marker
        if found_any:
            print(row)

    # UX features
    ux_keys = [
        "undo", "redo", "keyboard", "shortcut",
        "symmetry", "symmetric",
        "nina", "rebus",
        "pause", "resume", "cancel",
        "theme", "preferred", "preflex",
        "blacklist", "exclusion",
        "clue",
        "Web Worker", "worker",
    ]
    print("\n  UX features detected:")
    header = f"    {'Feature':25s}"
    for s in summaries:
        header += f" {s.name[:12]:>12s}"
    print(header)
    print("    " + "-" * (25 + 13 * len(summaries)))

    for kw in ux_keys:
        row = f"    {kw:25s}"
        found_any = False
        for s in summaries:
            total = 0
            for f in s.files:
                total += f.ux_hits.get(kw, 0)
            marker = f"{total:>12d}" if total else f"{'--':>12s}"
            if total:
                found_any = True
            row += marker
        if found_any:
            print(row)

    # Export formats
    exp_keys = [".puz", "ipuz", "exolve", "PDF", "pdf", "XPF", "xpf", "SVG", "svg", "HTML", "html"]
    print("\n  Export formats detected:")
    header = f"    {'Format':25s}"
    for s in summaries:
        header += f" {s.name[:12]:>12s}"
    print(header)
    print("    " + "-" * (25 + 13 * len(summaries)))

    for kw in exp_keys:
        row = f"    {kw:25s}"
        found_any = False
        for s in summaries:
            total = 0
            for f in s.files:
                total += f.export_hits.get(kw, 0)
            marker = f"{total:>12d}" if total else f"{'--':>12s}"
            if total:
                found_any = True
            row += marker
        if found_any:
            print(row)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

TOOLS = [
    ("Exet", "exet"),
    ("CrossHatch", "crosshatch"),
    ("Crosslift", "crosslift"),
    ("MichaelWehar", "wehar-autofill"),
    ("pycrossword", "pycrossword"),
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyse fetched crossword tool source files."
    )
    parser.add_argument(
        "--input-dir", default="data/research",
        help="Directory containing fetched sources (default: data/research)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output JSON instead of human-readable text",
    )
    args = parser.parse_args()

    base = Path(args.input_dir)
    if not base.is_dir():
        print(f"Error: {base} does not exist. Run fetch_tool_sources.sh first.",
              file=sys.stderr)
        sys.exit(1)

    summaries: List[ToolSummary] = []
    for name, dirname in TOOLS:
        tool_dir = base / dirname
        s = analyse_tool(name, tool_dir)
        if s and s.files:
            summaries.append(s)
        else:
            print(f"[WARN] No files found for {name} in {tool_dir}", file=sys.stderr)

    if not summaries:
        print("No tool sources found. Run fetch_tool_sources.sh first.",
              file=sys.stderr)
        sys.exit(1)

    if args.json:
        output = []
        for s in summaries:
            tool_data = {
                "name": s.name,
                "total_lines": s.total_lines,
                "num_files": len(s.files),
                "files": [],
                "algorithm_signals": {},
                "ux_signals": {},
                "export_signals": {},
            }
            combined_algo: Dict[str, int] = defaultdict(int)
            combined_ux: Dict[str, int] = defaultdict(int)
            combined_export: Dict[str, int] = defaultdict(int)
            for f in s.files:
                tool_data["files"].append({
                    "path": str(f.path.relative_to(s.directory)),
                    "lang": f.lang,
                    "lines": f.lines,
                    "functions": f.functions[:20],
                })
                for kw, c in f.algo_hits.items():
                    combined_algo[kw] += c
                for kw, c in f.ux_hits.items():
                    combined_ux[kw] += c
                for kw, c in f.export_hits.items():
                    combined_export[kw] += c
            tool_data["algorithm_signals"] = dict(combined_algo)
            tool_data["ux_signals"] = dict(combined_ux)
            tool_data["export_signals"] = dict(combined_export)
            output.append(tool_data)
        print(json.dumps(output, indent=2))
    else:
        print("CROSSWORD TOOL SOURCE ANALYSIS")
        print(f"Base directory: {base}")
        for s in summaries:
            print_tool_report(s)
        print_cross_tool_comparison(summaries)


if __name__ == "__main__":
    main()
