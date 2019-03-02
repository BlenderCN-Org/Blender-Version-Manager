import asyncio
import os
import shutil
import subprocess
import threading
import time

import psutil
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QCursor, QFont
from PyQt5.QtWidgets import QHBoxLayout, QMessageBox, QPushButton, QSizePolicy


class B3dItemLayout(QHBoxLayout):
    def __init__(self, root_folder, version, is_latest, parent):
        super(B3dItemLayout, self).__init__(None)

        self.btn_open_style = \
            ("""QPushButton[IsRunning=false]
                {
                    color: rgb(255, 255, 255);
                    background-color: rgb(51, 51, 51);
                    border-style: solid;
                    border-color: rgb(51, 51, 51);
                    border-width: 6px;
                }

                QPushButton[IsRunning=false]:pressed
                {
                    background-color: rgb(80, 80, 80);
                    border-color: rgb(80, 80, 80);
                }

                QPushButton[IsRunning=false]:hover
                {
                    background-color: rgb(80, 80, 80);
                    border-color: rgb(80, 80, 80);
                }

                QPushButton[IsRunning=true]
                {
                    color: rgb(255, 255, 255);
                    background-color: rgb(204, 102, 51);
                    border-style: solid;
                    border-color: rgb(204, 102, 51);
                    border-width: 6px;
                }

                QPushButton[IsRunning=true]:pressed
                {
                    background-color: rgb(204, 102, 51);
                    border-color: rgb(204, 102, 51);
                }

                QPushButton[IsRunning=true]:hover
                {
                    background-color: rgb(204, 102, 51);
                    border-color: rgb(204, 102, 51);
                }""")

        self.btn_delete_style = \
            ("""QPushButton[IsRunning=false]
                {
                    color: rgb(255, 255, 255);
                    background-color: rgb(51, 51, 51);
                    border-style: solid;
                    border-color: rgb(51, 51, 51);
                    border-width: 0px 4px 0px 4px;
                    qproperty-icon: url(:/icons/delete.svg);
                    qproperty-iconSize: 20px;
                }

                QPushButton[IsRunning=false]:pressed
                {
                    background-color: rgb(80, 80, 80);
                    border-color: rgb(80, 80, 80);
                }

                QPushButton[IsRunning=false]:hover
                {
                    background-color: rgb(80, 80, 80);
                    border-color: rgb(80, 80, 80);
                }

                QPushButton[IsRunning=true]
                {
                    color: rgb(255, 255, 255);
                    background-color: rgb(0, 122, 204);
                    border-style: solid;
                    border-color: rgb(0, 122, 204);
                    border-width: 0px 13px 0px 13px;
                    qproperty-icon: none;
                }

                QPushButton[IsRunning=true]:pressed
                {
                    background-color: rgb(80, 80, 80);
                    border-color: rgb(80, 80, 80);
                }

                QPushButton[IsRunning=true]:hover
                {
                    background-color: rgb(80, 80, 80);
                    border-color: rgb(80, 80, 80);
                }""")

        self.parent = parent
        self.root_folder = root_folder
        self.version = version
        self.pids = []

        self.setContentsMargins(6, 0, 6, 0)
        self.setSpacing(0)

        ctime = os.path.getctime(os.path.join(
            root_folder, version, "blender.exe"))
        fctime = time.strftime("%d-%b-%Y", time.gmtime(ctime))

        self.btnOpen = QPushButton(
            (version.split('-',)[-2]).replace("git.", "Git-") + " | " + fctime)
        self.btnOpen.clicked.connect(self.open)

        if (is_latest):
            self.btnOpen.setIcon(parent.star_icon)
            self.parent.blender_action.triggered.disconnect()
            self.parent.blender_action.triggered.connect(self.open)
        else:
            self.btnOpen.setIcon(parent.fake_icon)

        self.btnOpen.setFont(QFont("MS Shell Dlg 2", 10))
        self.btnOpen.setCursor(QCursor(Qt.PointingHandCursor))
        self.btnOpen.setStyleSheet(self.btn_open_style)

        self.btnOpen.setProperty('IsRunning', False)

        self.btnDelete = QPushButton("")
        self.btnDelete.setFlat(True)
        self.btnDelete.setToolTip("Delete From Drive")
        self.btnDelete.setSizePolicy(
            QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.btnDelete.setCursor(QCursor(Qt.PointingHandCursor))
        self.btnDelete.clicked.connect(lambda: self.delete())
        self.btnDelete.setStyleSheet(self.btn_delete_style)

        self.btnDelete.setProperty('IsRunning', False)

        self.addWidget(self.btnOpen)
        self.addWidget(self.btnDelete)

    def open(self):
        process = subprocess.Popen(os.path.join(
            self.root_folder, self.version, "blender.exe"))
        self.pids.append(process.pid)

        if (len(self.pids) == 1):
            self.observe_instances = ObserveInstances(self)
            self.observe_instances.started.connect(self.observe_started)
            self.observe_instances.finished.connect(self.observe_finished)
            self.observe_instances.count_changed.connect(self.count_changed)
            self.observe_instances.start()
        else:
            self.count_changed()

    def observe_started(self):
        self.count_changed()
        self.btnOpen.setProperty('IsRunning', True)
        self.btnOpen.setStyle(self.btnOpen.style())
        self.btnDelete.setToolTip("Number of Running Instances")
        self.btnDelete.setProperty('IsRunning', True)
        self.btnDelete.setStyle(self.btnDelete.style())
        self.btnDelete.setEnabled(False)

    def observe_finished(self):
        self.btnOpen.setProperty('IsRunning', False)
        self.btnOpen.setStyle(self.btnOpen.style())
        self.btnDelete.setIcon(self.parent.trash_icon)
        self.btnDelete.setText("")
        self.btnDelete.setToolTip("Delete From Drive")
        self.btnDelete.setEnabled(True)
        self.btnDelete.setProperty('IsRunning', False)
        self.btnDelete.setStyle(self.btnDelete.style())

    def count_changed(self):
        self.btnDelete.setText(str(len(self.pids)))

    def delete(self):
        delete = QMessageBox.warning(
            self.parent,
            "Warning",
            "Are you sure you want to delete\n'" + self.btnOpen.text() + "'\nfrom drive?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if delete == QMessageBox.Yes:
            threading.Thread(target=lambda: asyncio.run(
                self.delete_tread())).start()

    async def delete_tread(self):
        self.btnOpen.setText("Deleting...")
        self.btnOpen.setEnabled(False)
        self.btnDelete.hide()
        shutil.rmtree(os.path.join(self.root_folder, self.version))
        self.parent.cleanup_layout(self.layout())


class ObserveInstances(QThread):
    started = pyqtSignal()
    finished = pyqtSignal()
    count_changed = pyqtSignal()

    def __init__(self, parent):
        QThread.__init__(self)
        self.parent = parent

    def run(self):
        self.started.emit()

        while True:
            for pid in self.parent.pids:
                if not psutil.pid_exists(pid):
                    self.parent.pids.remove(pid)

                if len(self.parent.pids) > 0:
                    self.count_changed.emit()
                else:
                    self.finished.emit()
                    return

            QThread.sleep(1)
