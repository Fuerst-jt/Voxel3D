"""
Entry point: small wrapper that uses v3d package (UI, model and renderer are decoupled)
"""
import sys

from v3d.ui import create_app, MainWindow


def main():
    app = create_app(sys.argv)
    mw = MainWindow()
    mw.resize(1000, 700)
    mw.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
