import functools
import bubblesub.util
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets


def error(msg):
    box = QtWidgets.QMessageBox()
    box.setIcon(QtWidgets.QMessageBox.Critical)
    box.setText(msg)
    box.exec_()


def notice(msg):
    box = QtWidgets.QMessageBox()
    box.setIcon(QtWidgets.QMessageBox.Information)
    box.setText(msg)
    box.exec_()


def ask(msg):
    box = QtWidgets.QMessageBox()
    box.setText(msg)
    box.setIcon(QtWidgets.QMessageBox.Question)
    box.addButton('Yes', QtWidgets.QMessageBox.YesRole)
    box.addButton('No', QtWidgets.QMessageBox.NoRole)
    return box.exec_() == 0


def blend_colors(color1, color2, ratio):
    return QtGui.qRgb(
        color1.red() * (1 - ratio) + color2.red() * ratio,
        color1.green() * (1 - ratio) + color2.green() * ratio,
        color1.blue() * (1 - ratio) + color2.blue() * ratio)


class TimeEdit(QtWidgets.QLineEdit):
    def __init__(self, parent=None, allow_negative=False):
        super().__init__(parent)
        self._allow_negative = allow_negative
        if allow_negative:
            self.setInputMask('X9:99:99.999')
            self.setValidator(
                QtGui.QRegExpValidator(
                    QtCore.QRegExp(r'[+-]\d:\d\d:\d\d\.\d\d\d'), parent))
        else:
            self.setInputMask('9:99:99.999')
        self.reset_text()

    def reset_text(self):
        if self._allow_negative:
            self.setText('+0:00:00.000')
        else:
            self.setText('0:00:00.000')
        self.setCursorPosition(0)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)

        if not event.key() in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
            return

        text = self.text()
        delta = 10
        if event.key() == QtCore.Qt.Key_Up:
            time = bubblesub.util.str_to_ms(text) + delta
        elif event.key() == QtCore.Qt.Key_Down:
            time = bubblesub.util.str_to_ms(text) - delta

        text = bubblesub.util.ms_to_str(time)
        if self._allow_negative and time >= 0:
            text = '+' + text

        self.setText(text)
        self.textEdited.emit(self.text())


def _menu_about_to_show(menu):
    for action in menu.actions():
        if hasattr(action, 'cmd') and action.cmd:
            action.setEnabled(action.cmd.enabled(action.api))


class _CommandAction(QtWidgets.QAction):
    def __init__(self, api, cmd_name, cmd_args):
        super().__init__()
        self.api = api
        self.cmd_name = cmd_name
        self.cmd = bubblesub.cmd.registry.get(cmd_name)
        self.triggered.connect(
            functools.partial(
                api.run_cmd, bubblesub.cmd.registry.get(cmd_name), cmd_args))


def setup_cmd_menu(api, parent, menu_def):
    action_map = {}
    if hasattr(parent, 'aboutToShow'):
        parent.aboutToShow.connect(
            functools.partial(_menu_about_to_show, parent))
    for item in menu_def:
        if item is None:
            parent.addSeparator()
        elif isinstance(item[1], list):
            submenu = parent.addMenu(item[0])
            submenu.aboutToShow.connect(
                functools.partial(_menu_about_to_show, submenu))
            action_map.update(setup_cmd_menu(api, submenu, item[1]))
        else:
            action_name, cmd_name, *cmd_args = item
            action = _CommandAction(api, cmd_name, cmd_args)
            action.setParent(parent)
            action.setText(action_name)
            parent.addAction(action)
            action_map[(cmd_name, *cmd_args)] = action
    return action_map
