#!/usr/bin/env python3
"""
Advanced circular import detector for Lace.

AST-based: analyzes *module-level* imports only.  Imports inside functions,
methods, and ``if TYPE_CHECKING:`` blocks are excluded, because those are
lazy / type-only and can never produce a runtime import cycle.  Docstrings
are ignored by construction (they are not AST import nodes).

This avoids the false positives of a naive line scanner, which previously
reported ``from .x`` / ``from lace.x`` lines inside docstrings and lazy
imports as real dependency edges.

Usage:
    python circular_import_detector.py              # scan lace/ (default)
    python circular_import_detector.py <package-dir> # scan another package
    python circular_import_detector.py --json        # machine-readable output
    python circular_import_detector.py --graph       # print the internal edge map

Exit code is 0 when no cycles are found and 1 when cycles exist, so the tool
can be used as a CI guard.
"""

import ast
import json
import os
import sys
from pathlib import Path

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def _resolve_lace_root(start: str) -> str:
    """Return the directory containing the ``lace`` package.

    The script may live in the repo root (``circular_import_detector.py``) or in
    ``tests/`` (``tests/circular_import_detector.py``); walk up from the script's
    own directory until a ``lace`` package directory is found.
    """
    current = Path(start).resolve()
    for _ in range(4):
        if (current / "lace").is_dir():
            return str(current)
        if current.parent == current:
            break
        current = current.parent
    return start


project_root = _resolve_lace_root(project_root)
sys.path.insert(0, project_root)


class ModuleGraph:
    """AST-derived module-level dependency graph for a single package dir."""

    def __init__(self, target_dir: Path):
        self.target = Path(target_dir)
        self.modules: dict[str, Path] = {}
        for path in sorted(self.target.glob("*.py")):
            if path.name.startswith("__"):
                continue
            self.modules[path.stem] = path
        self.name_to_module = self._build_name_map()
        self.graph: dict[str, set] = {name: set() for name in self.modules}
        for stem, path in self.modules.items():
            self.graph[stem] = self._edges(path)

    def _build_name_map(self) -> dict:
        """Map every top-level class/function/assignment to its defining module."""
        mapping = {}
        for stem, path in self.modules.items():
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                continue
            for node in tree.body:
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    mapping[node.name] = stem
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            mapping[target.id] = stem
        return mapping

    def _edges(self, path: Path) -> set:
        """Module-level imports of other package modules (runtime-relevant only)."""
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError) as e:
            print(f"  ! could not parse {path.name}: {e}", file=sys.stderr)
            return set()

        edges = set()
        for node in tree.body:
            # Skip `if TYPE_CHECKING:` blocks entirely (type-only, never run).
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                    continue
            # Imports nested inside functions/classes are lazy and skipped:
            # we only walk tree.body, so they are never visited.

            if isinstance(node, ast.ImportFrom):
                self._add_from_edges(node, edges)
            elif isinstance(node, ast.Import):
                self._add_import_edges(node, edges)
        return edges

    def _add_from_edges(self, node: ast.ImportFrom, edges: set) -> None:
        if node.level:  # relative: `from .x import y` / `from . import X`
            if node.module:
                base = node.module.split(".")[0]
                if base in self.modules:
                    edges.add(base)
            for alias in node.names:
                if alias.name == "*":
                    continue
                if alias.name in self.modules:
                    edges.add(alias.name)
                elif alias.name in self.name_to_module:
                    edges.add(self.name_to_module[alias.name])
            return
        mod = node.module or ""
        if mod.startswith("lace."):
            base = mod[len("lace."):].split(".")[0]
            if base in self.modules:
                edges.add(base)
        elif mod in self.modules:
            edges.add(mod)
        elif mod == "lace":  # `from lace import X` -> module that defines X
            for alias in node.names:
                if alias.name in self.name_to_module:
                    edges.add(self.name_to_module[alias.name])

    def _add_import_edges(self, node: ast.Import, edges: set) -> None:
        for alias in node.names:
            name = alias.name
            if name.startswith("lace."):
                base = name[len("lace."):].split(".")[0]
                if base in self.modules:
                    edges.add(base)
            elif name in self.modules:
                edges.add(name)

    # ------------------------------------------------------------------ cycles
    def find_cycles(self) -> list:
        """Tarjan SCC: return each strongly-connected component that is a
        cycle (len > 1, or a module importing itself)."""
        index, low = {}, {}
        stack, on_stack = [], set()
        counter = [0]
        sccs = []

        def strongconnect(v: str) -> None:
            index[v] = low[v] = counter[0]
            counter[0] += 1
            stack.append(v)
            on_stack.add(v)
            for w in self.graph[v]:
                if w not in index:
                    strongconnect(w)
                    low[v] = min(low[v], low[w])
                elif w in on_stack:
                    low[v] = min(low[v], index[w])
            if low[v] == index[v]:
                component = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    component.append(w)
                    if w == v:
                        break
                if len(component) > 1 or v in self.graph[v]:
                    sccs.append(component)

        for module_name in self.graph:
            if module_name not in index:
                strongconnect(module_name)
        return sccs

    def sample_cycle(self, scc: list) -> list:
        """Return one concrete path ``[start, ..., start]`` inside the SCC."""
        nodes = set(scc)
        for start in sorted(nodes):
            path = [start]
            seen = {start}

            def dfs(u: str) -> bool:
                for w in sorted(self.graph[u]):
                    if w not in nodes:
                        continue
                    if w == start:
                        return True
                    if w not in seen:
                        seen.add(w)
                        path.append(w)
                        if dfs(w):
                            return True
                        path.pop()
                return False

            if dfs(start):
                return path + [start]
        return list(scc)  # fallback (should not happen for a real SCC)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    show_graph = "--graph" in argv
    argv = [a for a in argv if a not in ("--json", "--graph")]

    target = Path(argv[0]) if argv else Path(project_root) / "lace"
    if not target.is_dir():
        print(f"error: '{target}' is not a directory", file=sys.stderr)
        return 2

    print("Advanced Circular Import Detection (AST-based)")
    print("=" * 50)
    print(f"Scanning {target} ...")

    graph = ModuleGraph(target)
    edge_count = sum(len(v) for v in graph.graph.values())
    print(
        f"{len(graph.modules)} modules, {edge_count} module-level internal edges "
        f"(TYPE_CHECKING blocks and function-level imports excluded)"
    )

    if show_graph:
        for name in sorted(graph.graph):
            if graph.graph[name]:
                print(f"  {name}: {', '.join(sorted(graph.graph[name]))}")

    cycles = graph.find_cycles()

    if as_json:
        print(json.dumps({"cycles": [sorted(c) for c in cycles]}, indent=2))
        return 1 if cycles else 0

    if not cycles:
        print("\nNo circular imports detected at module level.")
        return 0

    print(f"\nCircular imports found ({len(cycles)} strongly-connected component(s)):")
    for component in sorted(cycles, key=len, reverse=True):
        print("  " + " -> ".join(graph.sample_cycle(component)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
