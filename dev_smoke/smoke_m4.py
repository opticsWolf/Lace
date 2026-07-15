import sys
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QMouseEvent
from PySide6.QtCore import QEvent, QPointF, Qt

app = QApplication(sys.argv)
from lace.dock_chrome import DragDetector

w = QWidget()
w.resize(300, 300)
fired = []
d = DragDetector(w)
d.drag_started.connect(lambda pos: fired.append(pos))


def send(kind, gx, gy, button, buttons):
    e = QMouseEvent(kind, QPointF(gx, gy), QPointF(gx, gy), button, buttons, Qt.NoModifier)
    app.sendEvent(w, e)


def press(x, y): send(QEvent.MouseButtonPress, x, y, Qt.LeftButton, Qt.LeftButton)
def move(x, y):  send(QEvent.MouseMove, x, y, Qt.NoButton, Qt.LeftButton)
def release(x, y): send(QEvent.MouseButtonRelease, x, y, Qt.LeftButton, Qt.NoButton)

# 1. Small move below the drag threshold must NOT fire.
press(10, 10); move(12, 12); release(12, 12)
assert not fired, f"small move should not trigger a drag: {fired}"

# 2. A move past the threshold fires exactly once, carrying the press position.
press(10, 10); move(250, 250)
assert len(fired) == 1, f"expected one drag, got {len(fired)}"
assert fired[0].x() == 10 and fired[0].y() == 10, f"wrong press pos: {fired[0]}"
release(250, 250)

# 3. After the drag started, further moves in the same press don't re-fire.
move(260, 260)
assert len(fired) == 1, f"drag re-fired: {len(fired)}"

# 4. A move with no active press (after release) does nothing.
move(5, 5)
assert len(fired) == 1

print("M4 DRAGDETECTOR OK")
