"""
Python AST Code Map Generator — PySide6 GUI
Scans a project folder and produces an LLM-ready code map.
"""

import ast
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QProgressBar,
    QFrame, QSplitter, QStatusBar, QComboBox, QCheckBox, QScrollArea,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont, QTextCharFormat, QColor, QSyntaxHighlighter, QPalette


# ─────────────────────────────────────────────
#  Data classes
# ─────────────────────────────────────────────

@dataclass
class FunctionInfo:
    name: str
    lineno: int
    args: list
    decorators: list
    docstring: Optional[str]
    calls: list = field(default_factory=list)
    is_async: bool = False


@dataclass
class ClassInfo:
    name: str
    lineno: int
    bases: list
    docstring: Optional[str]
    methods: list = field(default_factory=list)


@dataclass
class ModuleMap:
    path: str
    docstring: Optional[str]
    imports: list
    functions: list
    classes: list
    globals: list


# ─────────────────────────────────────────────
#  AST visitor
# ─────────────────────────────────────────────

class CodeMapVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports: list = []
        self.functions: list = []
        self.classes: list = []
        self.globals: list = []
        self._current_class: Optional[ClassInfo] = None

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}")
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        cls = ClassInfo(
            name=node.name,
            lineno=node.lineno,
            bases=[ast.unparse(b) for b in node.bases],
            docstring=ast.get_docstring(node),
        )
        prev = self._current_class
        self._current_class = cls
        self.generic_visit(node)
        self._current_class = prev
        self.classes.append(cls)

    def _visit_func(self, node):
        calls = list({
            ast.unparse(n.func)
            for n in ast.walk(node)
            if isinstance(n, ast.Call) and hasattr(n, "func")
        })
        fn = FunctionInfo(
            name=node.name,
            lineno=node.lineno,
            args=[a.arg for a in node.args.args],
            decorators=[ast.unparse(d) for d in node.decorator_list],
            docstring=ast.get_docstring(node),
            calls=calls,
            is_async=isinstance(node, ast.AsyncFunctionDef),
        )
        if self._current_class:
            self._current_class.methods.append(fn)
        else:
            self.functions.append(fn)

    visit_FunctionDef = _visit_func
    visit_AsyncFunctionDef = _visit_func

    def visit_Assign(self, node):
        if self._current_class is None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.globals.append(target.id)
        self.generic_visit(node)


def build_module_map(filepath: str) -> ModuleMap:
    source = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source)
    visitor = CodeMapVisitor()
    visitor.visit(tree)
    return ModuleMap(
        path=filepath,
        docstring=ast.get_docstring(tree),
        imports=visitor.imports,
        functions=visitor.functions,
        classes=visitor.classes,
        globals=visitor.globals,
    )


# ─────────────────────────────────────────────
#  Serialisers
# ─────────────────────────────────────────────

def to_text(m: ModuleMap) -> str:
    lines = [f"## Module: {m.path}"]
    if m.docstring:
        lines.append(f'  Purpose: {m.docstring.splitlines()[0]}')
    if m.imports:
        lines.append(f"  Imports: {', '.join(m.imports)}")
    if m.globals:
        lines.append(f"  Globals: {', '.join(m.globals)}")

    for cls in m.classes:
        bases = f"({', '.join(cls.bases)})" if cls.bases else ""
        lines.append(f"\n  class {cls.name}{bases}  [line {cls.lineno}]")
        if cls.docstring:
            lines.append(f'    "{cls.docstring.splitlines()[0]}"')
        for fn in cls.methods:
            prefix = "async " if fn.is_async else ""
            decs = "".join(f"@{d} " for d in fn.decorators)
            lines.append(f"    {decs}{prefix}def {fn.name}({', '.join(fn.args)})")
            if fn.docstring:
                lines.append(f'      "{fn.docstring.splitlines()[0]}"')
            if fn.calls:
                lines.append(f"      calls: {', '.join(fn.calls[:6])}")

    for fn in m.functions:
        prefix = "async " if fn.is_async else ""
        decs = "".join(f"@{d} " for d in fn.decorators)
        lines.append(f"\n  {decs}{prefix}def {fn.name}({', '.join(fn.args)})  [line {fn.lineno}]")
        if fn.docstring:
            lines.append(f'    "{fn.docstring.splitlines()[0]}"')
        if fn.calls:
            lines.append(f"    calls: {', '.join(fn.calls[:6])}")

    return "\n".join(lines)


def _fn_to_dict(fn: FunctionInfo) -> dict:
    return {
        "name": fn.name, "line": fn.lineno,
        "args": fn.args, "decorators": fn.decorators,
        "docstring": fn.docstring, "calls": fn.calls,
        "async": fn.is_async,
    }

def to_json(m: ModuleMap) -> dict:
    return {
        "path": m.path,
        "docstring": m.docstring,
        "imports": m.imports,
        "globals": m.globals,
        "functions": [_fn_to_dict(f) for f in m.functions],
        "classes": [
            {
                "name": c.name, "line": c.lineno,
                "bases": c.bases, "docstring": c.docstring,
                "methods": [_fn_to_dict(f) for f in c.methods],
            }
            for c in m.classes
        ],
    }


EXCLUDE_DIRS = {"__pycache__", ".venv", "venv", "env", ".git", "node_modules",
                "dist", "build", ".mypy_cache", ".pytest_cache"}


# ─────────────────────────────────────────────
#  Worker thread
# ─────────────────────────────────────────────

class ScanWorker(QObject):
    progress = Signal(int, int, str)   # current, total, filename
    finished = Signal(list, dict)      # (module_maps, stats)
    error = Signal(str)

    def __init__(self, root: str, fmt: str, include_calls: bool):
        super().__init__()
        self.root = root
        self.fmt = fmt
        self.include_calls = include_calls

    def run(self):
        try:
            files = [
                p for p in Path(self.root).rglob("*.py")
                if not any(part in EXCLUDE_DIRS for part in p.parts)
            ]
            total = len(files)
            maps = []
            stats = {"modules": 0, "classes": 0, "functions": 0, "errors": 0}

            for i, fp in enumerate(files):
                self.progress.emit(i + 1, total, fp.name)
                try:
                    m = build_module_map(str(fp))
                    if not self.include_calls:
                        for fn in m.functions:
                            fn.calls = []
                        for cls in m.classes:
                            for fn in cls.methods:
                                fn.calls = []
                    maps.append(m)
                    stats["modules"] += 1
                    stats["classes"] += len(m.classes)
                    stats["functions"] += len(m.functions) + sum(
                        len(c.methods) for c in m.classes)
                except SyntaxError:
                    stats["errors"] += 1

            self.finished.emit(maps, stats)
        except Exception as e:
            self.error.emit(str(e))


# ─────────────────────────────────────────────
#  Simple syntax highlighter for the output pane
# ─────────────────────────────────────────────

class MapHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []

        def rule(pattern, color, bold=False):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            import re
            self._rules.append((re.compile(pattern), fmt))

        rule(r"^## Module:.*", "#7dd3fc", bold=True)
        rule(r"\bclass\s+\w+", "#f9a8d4", bold=True)
        rule(r"\b(?:async\s+)?def\s+\w+", "#86efac")
        rule(r"@\w+", "#fbbf24")
        rule(r'"[^"]*"', "#a5b4fc")
        rule(r"\[line \d+\]", "#6b7280")
        rule(r"\bcalls:.*", "#94a3b8")
        rule(r"Purpose:.*", "#d1d5db")
        rule(r"Imports:.*", "#d1d5db")
        rule(r"Globals:.*", "#d1d5db")

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


# ─────────────────────────────────────────────
#  Main Window
# ─────────────────────────────────────────────

DARK = """
QMainWindow, QWidget {
    background-color: #0f1117;
    color: #e2e8f0;
    font-family: "Segoe UI", "SF Pro Text", system-ui, sans-serif;
    font-size: 13px;
}

QLabel#title {
    font-size: 20px;
    font-weight: 700;
    color: #f8fafc;
    letter-spacing: 0.5px;
}
QLabel#subtitle {
    color: #64748b;
    font-size: 12px;
}

QPushButton {
    background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 7px 18px;
    font-size: 13px;
}
QPushButton:hover { background-color: #273549; border-color: #4f7ec0; }
QPushButton:pressed { background-color: #172033; }
QPushButton:disabled { color: #475569; border-color: #1e293b; }

QPushButton#primary {
    background-color: #1d4ed8;
    border-color: #2563eb;
    color: #fff;
    font-weight: 600;
}
QPushButton#primary:hover  { background-color: #2563eb; }
QPushButton#primary:pressed { background-color: #1e40af; }
QPushButton#primary:disabled { background-color: #1e3a5f; color: #6b7280; }

QPushButton#save {
    background-color: #065f46;
    border-color: #059669;
    color: #ecfdf5;
    font-weight: 600;
}
QPushButton#save:hover  { background-color: #047857; }
QPushButton#save:disabled { background-color: #1a2e28; color: #6b7280; }

QTextEdit {
    background-color: #0a0d14;
    color: #cbd5e1;
    border: 1px solid #1e293b;
    border-radius: 6px;
    font-family: "Cascadia Code", "Fira Code", "JetBrains Mono", monospace;
    font-size: 12px;
    padding: 8px;
    selection-background-color: #1d4ed8;
}

QProgressBar {
    background-color: #1e293b;
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2563eb, stop:1 #7c3aed);
    border-radius: 4px;
}

QComboBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 5px 10px;
    color: #e2e8f0;
    min-width: 90px;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #1e293b;
    border: 1px solid #334155;
    selection-background-color: #1d4ed8;
}

QCheckBox { spacing: 6px; }
QCheckBox::indicator {
    width: 15px; height: 15px;
    border: 1px solid #475569;
    border-radius: 3px;
    background-color: #1e293b;
}
QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #2563eb;
}

QFrame#card {
    background-color: #141a25;
    border: 1px solid #1e293b;
    border-radius: 8px;
}
QFrame#divider {
    background-color: #1e293b;
    max-height: 1px;
}

QLabel#stat {
    color: #94a3b8;
    font-size: 12px;
}
QLabel#statval {
    color: #38bdf8;
    font-size: 14px;
    font-weight: 700;
}

QStatusBar {
    background-color: #0a0d14;
    color: #475569;
    border-top: 1px solid #1e293b;
    font-size: 11px;
}

QSplitter::handle { background-color: #1e293b; width: 2px; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python AST Code Map Generator")
        self.setMinimumSize(960, 660)
        self._root_dir: Optional[str] = None
        self._result_text: str = ""
        self._thread: Optional[QThread] = None
        self._worker: Optional[ScanWorker] = None
        self._setup_ui()
        self.setStyleSheet(DARK)

    # ── UI construction ──────────────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(18, 18, 18, 10)
        root_layout.setSpacing(12)

        # ── Header ──────────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        lbl_title = QLabel("AST Code Map")
        lbl_title.setObjectName("title")
        lbl_sub = QLabel("Extract structured code metadata for LLM context")
        lbl_sub.setObjectName("subtitle")
        title_col.addWidget(lbl_title)
        title_col.addWidget(lbl_sub)

        header.addLayout(title_col)
        header.addStretch()

        # Format selector
        header.addWidget(QLabel("Format:"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["Text", "JSON"])
        header.addWidget(self.fmt_combo)

        # Include calls checkbox
        self.chk_calls = QCheckBox("Include call graph")
        self.chk_calls.setChecked(True)
        header.addWidget(self.chk_calls)

        root_layout.addLayout(header)

        # ── Divider ─────────────────────────────────────────────────────────
        div = QFrame(); div.setObjectName("divider"); div.setFrameShape(QFrame.Shape.HLine)
        root_layout.addWidget(div)

        # ── Folder picker card ───────────────────────────────────────────────
        card = QFrame(); card.setObjectName("card")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(14, 10, 14, 10)
        card_layout.setSpacing(10)

        self.lbl_path = QLabel("No folder selected")
        self.lbl_path.setObjectName("stat")
        self.lbl_path.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.lbl_path.setWordWrap(False)

        btn_open = QPushButton("⊞  Open Folder…")
        btn_open.setFixedWidth(140)
        btn_open.clicked.connect(self._open_folder)

        self.btn_scan = QPushButton("▶  Generate Map")
        self.btn_scan.setObjectName("primary")
        self.btn_scan.setFixedWidth(150)
        self.btn_scan.setEnabled(False)
        self.btn_scan.clicked.connect(self._start_scan)

        card_layout.addWidget(btn_open)
        card_layout.addWidget(self.lbl_path, 1)
        card_layout.addWidget(self.btn_scan)
        root_layout.addWidget(card)

        # ── Progress ─────────────────────────────────────────────────────────
        prog_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        self.lbl_progress = QLabel("")
        self.lbl_progress.setObjectName("stat")
        self.lbl_progress.setFixedWidth(260)
        prog_row.addWidget(self.progress_bar)
        prog_row.addWidget(self.lbl_progress)
        root_layout.addLayout(prog_row)

        # ── Stats row ────────────────────────────────────────────────────────
        stats_row = QHBoxLayout()
        stats_row.setSpacing(24)

        def stat_pair(label):
            col = QVBoxLayout(); col.setSpacing(1)
            val = QLabel("—"); val.setObjectName("statval")
            lbl = QLabel(label); lbl.setObjectName("stat")
            col.addWidget(val); col.addWidget(lbl)
            stats_row.addLayout(col)
            return val

        self.stat_modules  = stat_pair("Modules")
        self.stat_classes  = stat_pair("Classes")
        self.stat_funcs    = stat_pair("Functions")
        self.stat_errors   = stat_pair("Errors")
        stats_row.addStretch()

        self.btn_save = QPushButton("⬇  Save to File…")
        self.btn_save.setObjectName("save")
        self.btn_save.setFixedWidth(150)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_file)
        stats_row.addWidget(self.btn_save)

        root_layout.addLayout(stats_row)

        # ── Output pane ──────────────────────────────────────────────────────
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText(
            "Generated code map will appear here…\n\n"
            "1. Click 'Open Folder' to pick your Python project\n"
            "2. Click 'Generate Map' to scan all .py files\n"
            "3. Click 'Save to File' to export the result"
        )
        self.highlighter = MapHighlighter(self.output.document())
        root_layout.addWidget(self.output, 1)

        # ── Status bar ───────────────────────────────────────────────────────
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

    # ── Actions ──────────────────────────────────────────────────────────────

    def _open_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Python Project Folder", str(Path.home()))
        if folder:
            self._root_dir = folder
            display = folder if len(folder) <= 60 else "…" + folder[-57:]
            self.lbl_path.setText(display)
            self.btn_scan.setEnabled(True)
            self.status.showMessage(f"Folder selected: {folder}")

    def _start_scan(self):
        if not self._root_dir:
            return

        self.btn_scan.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.output.clear()
        self.progress_bar.setValue(0)
        for s in (self.stat_modules, self.stat_classes, self.stat_funcs, self.stat_errors):
            s.setText("…")

        fmt = self.fmt_combo.currentText().lower()
        include_calls = self.chk_calls.isChecked()

        self._thread = QThread()
        self._worker = ScanWorker(self._root_dir, fmt, include_calls)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)

        self._thread.start()
        self.status.showMessage("Scanning…")

    def _on_progress(self, current: int, total: int, name: str):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.lbl_progress.setText(f"{current}/{total}  {name}")

    def _on_finished(self, maps: list, stats: dict):
        fmt = self.fmt_combo.currentText().lower()
        if fmt == "json":
            data = [to_json(m) for m in maps]
            self._result_text = json.dumps(data, indent=2)
        else:
            self._result_text = "\n\n".join(to_text(m) for m in maps)

        self.output.setPlainText(self._result_text)

        self.stat_modules.setText(str(stats["modules"]))
        self.stat_classes.setText(str(stats["classes"]))
        self.stat_funcs.setText(str(stats["functions"]))
        self.stat_errors.setText(str(stats["errors"]))

        self.btn_scan.setEnabled(True)
        self.btn_save.setEnabled(bool(self._result_text))
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.lbl_progress.setText("Done")
        self.status.showMessage(
            f"Scan complete — {stats['modules']} modules, "
            f"{stats['classes']} classes, {stats['functions']} functions"
        )

    def _on_error(self, msg: str):
        self.output.setPlainText(f"[Error]\n{msg}")
        self.btn_scan.setEnabled(True)
        self.status.showMessage(f"Error: {msg}")

    def _save_file(self):
        fmt = self.fmt_combo.currentText().lower()
        ext = "json" if fmt == "json" else "txt"
        default = str(Path(self._root_dir or ".") / f"code_map.{ext}")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Code Map",
            default,
            f"{'JSON' if fmt == 'json' else 'Text'} files (*.{ext});;All files (*)",
        )
        if path:
            Path(path).write_text(self._result_text, encoding="utf-8")
            self.status.showMessage(f"Saved → {path}")


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette base so native widgets also look dark
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor("#0f1117"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#e2e8f0"))
    pal.setColor(QPalette.ColorRole.Base, QColor("#0a0d14"))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#141a25"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#e2e8f0"))
    pal.setColor(QPalette.ColorRole.Button, QColor("#1e293b"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#e2e8f0"))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#1d4ed8"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(pal)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
