"""
Main UI: composes SceneModel, SceneRenderer and ZMQSubscriber.
Provides buttons: Load, Clear, Generate Test Data, Export JSON, Start/Stop SUB.
"""
import sys
import json
import subprocess
from PySide6 import QtCore, QtWidgets, QtGui

try:
    from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
except Exception:
    QVTKRenderWindowInteractor = None

from .scene_model import SceneModel
from .renderer import SceneRenderer
from .zmq_sub import ZMQSubscriber


def create_app(argv):
    app = QtWidgets.QApplication(argv)
    return app


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('3D Viewer')
        w = QtWidgets.QWidget()
        self.setCentralWidget(w)
        main_layout = QtWidgets.QHBoxLayout(w)

        # LEFT: 3D view (VTK)
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        if QVTKRenderWindowInteractor is None:
            # show a placeholder with clear install instructions when VTK is not available
            ph = QtWidgets.QWidget()
            ph_layout = QtWidgets.QVBoxLayout(ph)
            placeholder = QtWidgets.QLabel('VTK not available. Please install required dependency before running the application.')
            placeholder.setWordWrap(True)
            placeholder.setAlignment(QtCore.Qt.AlignCenter)
            ph_layout.addWidget(placeholder)
            cmd = "pip install -r requirements.txt"
            copy_btn = QtWidgets.QPushButton('Copy install command')
            def _copy():
                clipboard = QtWidgets.QApplication.clipboard()
                clipboard.setText(cmd)
                self.on_status('Install command copied to clipboard')
            copy_btn.clicked.connect(_copy)
            ph_layout.addWidget(copy_btn)
            ph_layout.addStretch()
            left_layout.addWidget(ph)
            self.vtk_widget = None
            self._left_placeholder = ph
        else:
            self.vtk_widget = QVTKRenderWindowInteractor(left_widget)
            left_layout.addWidget(self.vtk_widget)
            # initialize interactor
            self.vtk_widget.Initialize()
            self.vtk_widget.Start()

        main_layout.addWidget(left_widget, 1)

        # RIGHT: controls
        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)

        # File group
        file_group = QtWidgets.QGroupBox('File')
        file_layout = QtWidgets.QHBoxLayout(file_group)
        btn_load = QtWidgets.QPushButton('Load JSON')
        btn_load.clicked.connect(self.load_json)
        btn_clear = QtWidgets.QPushButton('Clear')
        btn_clear.clicked.connect(self.clear_scene)
        file_layout.addWidget(btn_load)
        file_layout.addWidget(btn_clear)
        right_layout.addWidget(file_group)

        # Generate / Export
        data_group = QtWidgets.QGroupBox('Data')
        data_layout = QtWidgets.QVBoxLayout(data_group)
        gen_btn = QtWidgets.QPushButton('Generate Test Data')
        gen_btn.clicked.connect(self.generate_data)
        export_btn = QtWidgets.QPushButton('Export JSON')
        export_btn.clicked.connect(self.export_json)
        data_layout.addWidget(gen_btn)
        data_layout.addWidget(export_btn)
        right_layout.addWidget(data_group)

        # ZMQ
        zmq_group = QtWidgets.QGroupBox('ZMQ')
        zmq_layout = QtWidgets.QFormLayout(zmq_group)
        self.addr_edit = QtWidgets.QLineEdit('tcp://127.0.0.1:5556')
        zmq_layout.addRow(QtWidgets.QLabel('Address:'), self.addr_edit)
        self.topic_edit = QtWidgets.QLineEdit('')
        zmq_layout.addRow(QtWidgets.QLabel('Topic (optional):'), self.topic_edit)
        self.btn_sub = QtWidgets.QPushButton('Start SUB')
        self.btn_sub.clicked.connect(self.toggle_sub)
        zmq_layout.addRow(self.btn_sub)
        right_layout.addWidget(zmq_group)

        # Mode: browse / select
        mode_group = QtWidgets.QGroupBox('Mode')
        mode_layout = QtWidgets.QHBoxLayout(mode_group)
        self.mode_browse = QtWidgets.QRadioButton('Browse')
        self.mode_browse.setChecked(True)
        self.mode_select = QtWidgets.QRadioButton('Select')
        mode_layout.addWidget(self.mode_browse)
        mode_layout.addWidget(self.mode_select)
        right_layout.addWidget(mode_group)

        # connect mode changes to update interaction
        self.mode_browse.toggled.connect(self._on_mode_changed)

        # Info & log
        info_group = QtWidgets.QGroupBox('Info')
        info_layout = QtWidgets.QVBoxLayout(info_group)
        self.info_label = QtWidgets.QLabel('Points: 0    Segments: 0')
        info_layout.addWidget(self.info_label)
        self.selected_info = QtWidgets.QTextEdit()
        self.selected_info.setReadOnly(True)
        self.selected_info.setFixedHeight(120)
        info_layout.addWidget(self.selected_info)
        right_layout.addWidget(info_group)

        log_group = QtWidgets.QGroupBox('Log')
        log_layout = QtWidgets.QVBoxLayout(log_group)
        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(200)
        log_layout.addWidget(self.log)
        right_layout.addWidget(log_group, 1)

        bottom_h = QtWidgets.QHBoxLayout()
        bottom_h.addStretch()
        self.status = QtWidgets.QLabel('Ready')
        bottom_h.addWidget(self.status)
        right_layout.addLayout(bottom_h)

        right_layout.setContentsMargins(6,6,6,6)
        main_layout.addWidget(right_panel)
        main_layout.setStretch(0, 3)
        main_layout.setStretch(1, 1)

        # Model / renderer / zmq
        self.model = SceneModel()
        self.sub = None
        if self.vtk_widget is not None:
            self.renderer = SceneRenderer(self.vtk_widget)
        else:
            self.renderer = None
        # install event filter to capture mouse events for selection
        if self.vtk_widget is not None:
            self.vtk_widget.installEventFilter(self)
    

    # status/log helpers
    def on_status(self, text: str):
        self.status.setText(text)
        self.log.append(text)

    def _update_info(self):
        p, s = self.model.counts
        self.info_label.setText(f'Points: {p}    Segments: {s}')

    # actions
    def load_json(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open JSON', filter='*.json')
        if not path:
            return
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            self.model.set_from_dict(data)
            self.renderer.render(self.model)
            self._update_info()
            self.on_status(f'Loaded: {path}')
        except Exception as e:
            self.on_status(f'Load error: {e}')

    def clear_scene(self):
        self.model.clear()
        self.renderer.clear()
        self._update_info()
        self.on_status('Cleared')

    def generate_data(self):
        # open dialog to ask sizes
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle('Generate Test Data')
        layout = QtWidgets.QFormLayout(dlg)
        npts = QtWidgets.QSpinBox(); npts.setRange(0, 10000); npts.setValue(50)
        nseg = QtWidgets.QSpinBox(); nseg.setRange(0, 10000); nseg.setValue(10)
        layout.addRow('Points:', npts)
        layout.addRow('Segments:', nseg)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        layout.addRow(btns)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        self.model.randomize(n_points=npts.value(), n_segments=nseg.value())
        self.renderer.render(self.model)
        self._update_info()
        self.on_status('Generated random test data')

    def eventFilter(self, obj, event):
        # intercept right-clicks on vtk widget when in select mode
        if obj is getattr(self, 'vtk_widget', None):
            # Prevent VTK from starting right-button interactions (pan/zoom)
            # when in Select mode by consuming the press and move events.
            if self.mode_select.isChecked():
                if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.RightButton:
                    return True
                if event.type() == QtCore.QEvent.MouseMove:
                    # if right button is held, consume move to avoid interaction
                    buttons = event.buttons()
                    if buttons & QtCore.Qt.RightButton:
                        return True
                if event.type() == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.RightButton:
                    if self.renderer is not None:
                        pos = event.pos()
                        # multi-select only when Alt is pressed. Some Linux WMs grab Alt
                        # so use global QApplication keyboardModifiers() as a fallback.
                        mods = QtWidgets.QApplication.keyboardModifiers()
                        alt = bool(mods & QtCore.Qt.AltModifier)
                        pid = self.renderer.pick_and_select(pos.x(), pos.y(), multi=alt)
                        if pid is not None:
                            # show latest point attributes
                            try:
                                pt = self.model.points[pid]
                                self.selected_info.setPlainText(json.dumps(pt, indent=2))
                            except Exception:
                                self.selected_info.setPlainText(str(pid))
                    return True
        return super().eventFilter(obj, event)

    def _on_mode_changed(self, checked: bool):
        # checked == True means Browse selected; False means Select
        if not hasattr(self, 'renderer') or self.renderer is None:
            return
        try:
            # Do not change the interactor style here. Right-button interaction
            # is suppressed via the event filter in Select mode so other
            # interactions (left-button rotate, etc.) remain available.
            return
        except Exception:
            pass

    def export_json(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Export JSON', filter='JSON files (*.json)')
        if not path:
            return
        try:
            self.model.export_json(path)
            self.on_status(f'Exported scene to: {path}')
        except Exception as e:
            self.on_status(f'Export error: {e}')

    def toggle_sub(self):
        if self.sub and self.sub.isRunning():
            self.sub.stop()
            self.sub = None
            self.btn_sub.setText('Start SUB')
            self.on_status('Subscriber stopped')
            return
        addr = self.addr_edit.text().strip()
        if not addr:
            self.on_status('Invalid addr')
            return
        topic = self.topic_edit.text().encode('utf-8') if self.topic_edit.text().strip() else b''
        self.sub = ZMQSubscriber(addr=addr, topic=topic)
        self.sub.msg_received.connect(self.on_msg)
        self.sub.status.connect(self.on_status)
        self.sub.start()
        self.btn_sub.setText('Stop SUB')
        self.on_status(f'Subscribing {addr}')

    @QtCore.Slot(object)
    def on_msg(self, msg):
        try:
            self.log.append('[recv] ' + (json.dumps(msg) if not isinstance(msg, str) else msg))
            if isinstance(msg, dict):
                self.model.set_from_dict(msg)
                self.renderer.render(self.model)
                self._update_info()
                self.on_status('Scene updated (dict)')
            else:
                self.on_status('Received unknown message type')
        except Exception as e:
            self.on_status(f'Update error: {e}')

    def closeEvent(self, event):
        if self.sub:
            self.sub.stop()
        super().closeEvent(event)
