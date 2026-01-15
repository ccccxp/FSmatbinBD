"""
Entry point for the new Qt-based GUI preview.
Run with: python qt_main.py
"""
import sys
import os

# ============================================================
# 关键：确保在 PyInstaller 打包后能正确找到 src 模块
# PyInstaller 使用 contents_directory='internal' 时，
# 数据文件会被放在 internal 目录下
# ============================================================
def setup_path():
    """设置 Python 模块搜索路径，确保打包后能找到所有模块"""
    if getattr(sys, 'frozen', False):
        # 打包后的运行环境
        # sys._MEIPASS 是 PyInstaller 解压的临时目录（对于 onefile）
        # 或者是可执行文件所在目录（对于 onedir）
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        
        # 检查 internal 目录（contents_directory 设置）
        internal_path = os.path.join(os.path.dirname(sys.executable), 'internal')
        if os.path.exists(internal_path):
            if internal_path not in sys.path:
                sys.path.insert(0, internal_path)
        
        # 也添加 base_path
        if base_path not in sys.path:
            sys.path.insert(0, base_path)
    else:
        # 开发环境：添加项目根目录
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

# 在任何导入之前设置路径
setup_path()


def check_integrity():
    """启动前进行完整性校验"""
    try:
        from src.core.about_secure import verify_integrity, get_integrity_error_message
        if not verify_integrity():
            # 完整性校验失败，显示错误并退出
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication(sys.argv)
            QMessageBox.critical(
                None, 
                "完整性校验失败 / Integrity Check Failed",
                get_integrity_error_message()
            )
            sys.exit(1)
    except ImportError:
        # 模块导入失败，也认为是篡改
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "完整性校验失败 / Integrity Check Failed",
            "关键模块缺失，程序无法启动。\nCritical module missing. Program cannot start."
        )
        sys.exit(1)


# 首先进行完整性校验
check_integrity()

from PySide6.QtWidgets import QApplication
from src.gui_qt.main_window import launch


def main():
    app, _ = launch()
    sys.exit(app.exec())


if __name__ == "__main__":
    """qt_main.py

    Qt 预览入口。

    说明：近期出现过 `QFont::setPointSize: Point size <= 0 (-1)` 警告，
    该警告通常意味着某处把字号设置成了非法值（<=0）。

    这里安装一个 Qt message handler：当捕获到这条警告时，打印当前 Python 调用栈，
    方便快速定位是哪段代码触发。
    """

    import os
    import sys
    import traceback

    from PySide6.QtCore import QTimer, qInstallMessageHandler
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    from src.gui_qt.main_window import launch


    def _qt_message_handler(mode, context, message):
        # 只在遇到字体字号警告时附带 Python 调用栈，避免刷屏。
        if "QFont::setPointSize" in str(message):
            stack = "".join(traceback.format_stack(limit=30))
            sys.stderr.write(f"\n[QtWarning] {message}\n--- Python stack (most recent call last) ---\n{stack}\n")


    def main():
        # 调试开关：默认不刷屏。
        # 需要定位 Qt 警告/字体问题时，可临时设置：set COPILOT_QT_DEBUG=1
        debug_enabled = os.environ.get("COPILOT_QT_DEBUG", "").strip() not in ("", "0", "false", "False")
        if debug_enabled:
            qInstallMessageHandler(_qt_message_handler)
        app, _ = launch()

        def _scan_invalid_fonts():
            if not debug_enabled:
                return
            bad = []
            for w in app.allWidgets():
                try:
                    f = w.font()
                    if f and f.pointSize() <= 0:
                        bad.append((w, f))
                except Exception:
                    continue

            if bad:
                sys.stderr.write(f"\n[FontScan] Found {len(bad)} widget(s) with pointSize<=0\n")
                for w, f in bad[:80]:
                    try:
                        sys.stderr.write(
                            f"  - {type(w).__name__} objectName='{w.objectName()}' pointSize={f.pointSize()} pixelSize={f.pixelSize()} family='{f.family()}'\n"
                        )
                    except Exception:
                        sys.stderr.write(f"  - {type(w).__name__} (print failed)\n")
            else:
                sys.stderr.write("\n[FontScan] No widget with pointSize<=0 found.\n")

            # 兜底：如果确实存在 bad widget，给它们单独补一个合法字号（尽量不改变 family）。
            for w, f in bad:
                try:
                    nf = QFont(f)
                    if nf.pointSize() <= 0:
                        nf.setPointSize(10)
                    w.setFont(nf)
                except Exception:
                    continue

        # 等 UI 都创建完再扫一次（仅 debug 时）
        QTimer.singleShot(0, _scan_invalid_fonts)
        sys.exit(app.exec())


    if __name__ == "__main__":
        main()
