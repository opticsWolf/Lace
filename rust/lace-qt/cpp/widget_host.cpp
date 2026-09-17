// Phase-3 QWidget-coexistence spike: one native frame holding a QTextEdit
// (QWidget text editing) beside a QML scene (Quick text editing), proving
// the two worlds run side by side on this toolchain. No Q_OBJECT members,
// so no moc step is needed. Deeper integration (a WidgetHost item inside a
// dock tab) is a Phase-6/7 C++ task; see rust/README.md.
#include <QApplication>
#include <QQuickView>
#include <QSplitter>
#include <QTextEdit>
#include <QTimer>
#include <QUrl>
#include <QWidget>

extern "C" int run_widget_host(int argc, char **argv, const char *qml_path, bool smoke) {
    QApplication app(argc, argv);

    QSplitter splitter;
    splitter.setWindowTitle(QStringLiteral("Lace widget host — QWidget beside QML"));

    auto *editor = new QTextEdit(&splitter);
    editor->setPlainText(QStringLiteral("QTextEdit (QWidget).\nType here — the QML TextArea lives next door."));
    splitter.addWidget(editor);

    auto *view = new QQuickView();
    view->setResizeMode(QQuickView::SizeRootObjectToView);
    view->setSource(QUrl::fromLocalFile(QString::fromUtf8(qml_path)));
    QWidget *container = QWidget::createWindowContainer(view, &splitter);
    container->setMinimumSize(320, 240);
    splitter.addWidget(container);

    splitter.resize(960, 600);
    splitter.show();

    if (smoke) {
        QTimer::singleShot(1500, &app, &QApplication::quit);
    }
    return app.exec();
}
