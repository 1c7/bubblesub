# bubblesub - ASS subtitle editor
# Copyright (C) 2018 Marcin Kurczewski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse
import asyncio
import sys
import traceback
import typing as T

import quamash
from PyQt5 import QtCore, QtGui, QtWidgets

from bubblesub.data import ROOT_DIR

if T.TYPE_CHECKING:
    from bubblesub.api import Api
    from bubblesub.api.log import LogLevel


class MySplashScreen(QtWidgets.QSplashScreen):
    def __init__(self, *args: T.Any, **kwargs: T.Any) -> None:
        super().__init__(*args, **kwargs)
        self._painted = False

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(
            QtCore.Qt.SplashScreen
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        self._painted = True

    def showMessage(self, text: str) -> None:
        self._painted = False
        super().showMessage(text, QtCore.Qt.AlignBottom, QtCore.Qt.white)
        self._ensure_painted()

    def _ensure_painted(self) -> None:
        while not self._painted:
            QtCore.QThread.usleep(1e3)
            QtWidgets.QApplication.processEvents()


class Application:
    def __init__(self, args: argparse.Namespace):
        self._args = args
        self._splash: T.Optional[QtWidgets.QSplashScreen] = None

        QtCore.pyqtRemoveInputHook()

        self._app = QtWidgets.QApplication(sys.argv + ["--name", "bubblesub"])
        self._app.setApplicationName("bubblesub")
        self._loop = quamash.QEventLoop(self._app)
        asyncio.set_event_loop(self._loop)

    def splash_screen(self) -> None:
        pixmap = QtGui.QPixmap(str(ROOT_DIR / "bubblesub.png"))
        pixmap = pixmap.scaledToWidth(640)
        self._splash = MySplashScreen(pixmap)
        self._splash.show()
        self._splash.showMessage("Loading API...")

    def run(self, api: "Api") -> None:
        from bubblesub.ui.console import Console
        from bubblesub.ui.main_window import MainWindow
        from bubblesub.cfg import ConfigError

        def on_error(ex_type, ex_obj, ex_tb) -> None:
            api.log.error("An unhandled error occurred: ")
            api.log.error(
                "".join(traceback.format_exception(ex_type, ex_obj, ex_tb))
            )

        sys.excepthook = on_error

        console = Console(api, None)
        self._app.aboutToQuit.connect(api.media.shutdown)

        try:
            if self._splash:
                self._splash.showMessage("Loading config...")
            if not self._args.no_config:
                api.cfg.load(api.cfg.DEFAULT_PATH)
        except ConfigError as ex:
            api.log.error(str(ex))

        if self._splash:
            self._splash.showMessage("Loading commands...")
        api.cmd.reload_commands()

        if self._splash:
            self._splash.showMessage("Loading UI...")
        main_window = MainWindow(api, console)
        api.gui.set_main_window(main_window)

        main_window.show()

        if self._args.file:
            api.cmd.run_cmdline([["open", "--path", self._args.file]])

        if self._splash:
            self._splash.finish(main_window)

        with self._loop:
            self._loop.run_forever()

        if not self._args.no_config:
            assert api.cfg.root_dir is not None
            api.cfg.save(api.cfg.root_dir)
