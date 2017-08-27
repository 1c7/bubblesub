import bubblesub.util
import bubblesub.ui.util
from bubblesub.ui.styles_model import StylesModel, StylesModelColumn
from bubblesub.api.cmd import CoreCommand
from PyQt5 import QtCore
from PyQt5 import QtWidgets


class StyleList(QtWidgets.QWidget):
    selection_changed = QtCore.pyqtSignal()

class StyleList(QtWidgets.QWidget):
    def __init__(self, api, model, selection_model, parent):
        super().__init__(parent)
        self._api = api
        selection_model.selectionChanged.connect(self._selection_changed)

        self._styles_list_view = QtWidgets.QListView(self)
        self._styles_list_view.setModel(model)
        self._styles_list_view.setSelectionModel(selection_model)

        self._add_button = QtWidgets.QPushButton('Add', self)
        self._add_button.clicked.connect(self._add_button_clicked)
        self._remove_button = QtWidgets.QPushButton('Remove', self)
        self._remove_button.setEnabled(False)
        self._remove_button.clicked.connect(self._remove_button_clicked)
        self._rename_button = QtWidgets.QPushButton('Rename', self)
        self._rename_button.setEnabled(False)
        self._rename_button.clicked.connect(self._rename_button_clicked)

        strip = QtWidgets.QWidget(self)
        layout = QtWidgets.QHBoxLayout(strip, margin=0)
        layout.addWidget(self._add_button)
        layout.addWidget(self._remove_button)
        layout.addWidget(self._rename_button)

        layout = QtWidgets.QVBoxLayout(self, margin=0)
        layout.addWidget(self._styles_list_view)
        layout.addWidget(strip)

    @property
    def _selected_style(self):
        selected_row = self._selected_row
        if selected_row is None:
            return None
        return self._api.subs.styles[selected_row]

    @property
    def _selected_row(self):
        indexes = self._styles_list_view.selectedIndexes()
        if not indexes:
            return None
        return indexes[0].row()

    def _selection_changed(self, event):
        anything_selected = len(event.indexes()) > 0
        self._remove_button.setEnabled(anything_selected)
        self._rename_button.setEnabled(anything_selected)

    def _add_button_clicked(self, _event):
        style_name = self._prompt_for_unique_style_name()
        if not style_name:
            return
        style = self._api.subs.styles.insert_one(style_name)
        self._styles_list_view.selectionModel().select(
            self._styles_list_view.model().index(
                self._api.subs.styles.index(style), 0),
            QtCore.QItemSelectionModel.Select)

    def _prompt_for_unique_style_name(self, style_name=''):
        prompt_text = 'Name of the new style:'
        while True:
            dialog = QtWidgets.QInputDialog(self)
            dialog.setLabelText(prompt_text)
            dialog.setTextValue(style_name)
            dialog.setInputMode(QtWidgets.QInputDialog.TextInput)
            if not dialog.exec_():
                return None
            style_name = dialog.textValue()

            exists = False
            for style in self._api.subs.styles:
                if style.name == style_name:
                    exists = True

            if not exists:
                return style_name

            prompt_text = (
                '"{}" already exists. Choose different name:'
                .format(style_name))

    def _remove_button_clicked(self, _event):
        if not bubblesub.ui.util.ask(
                'Are you sure you want to remove style "{}"?'
                .format(self._selected_style.name)):
            return

        style = self._selected_style
        self._styles_list_view.selectionModel().clear()
        self._api.subs.styles.remove(self._api.subs.styles.index(style), 1)

    def _rename_button_clicked(self, _event):
        style = self._selected_style
        old_name = style.name
        new_name = self._prompt_for_unique_style_name(old_name)
        if not new_name:
            return

        with self._api.undo.bulk():
            style.name = new_name
            for line in self._api.subs.lines:
                if line.style == old_name:
                    line.style = new_name
            self._styles_list_view.selectionModel().select(
                self._styles_list_view.model().index(
                    self._api.subs.styles.index(style), 0),
                QtCore.QItemSelectionModel.Select)


class FontGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent):
        super().__init__('Font', parent)
        self.font_name_edit = QtWidgets.QLineEdit(self)
        self.font_size_edit = QtWidgets.QSpinBox(self, minimum=0)
        self.bold_checkbox = QtWidgets.QCheckBox('Bold', self)
        self.italic_checkbox = QtWidgets.QCheckBox('Italic', self)
        self.underline_checkbox = QtWidgets.QCheckBox('Underline', self)
        self.strike_out_checkbox = QtWidgets.QCheckBox('Strike-out', self)

        layout = QtWidgets.QGridLayout(self)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        layout.addWidget(QtWidgets.QLabel('Name:', self), 0, 0)
        layout.addWidget(self.font_name_edit, 0, 1)
        layout.addWidget(QtWidgets.QLabel('Size:', self), 1, 0)
        layout.addWidget(self.font_size_edit, 1, 1)
        layout.addWidget(QtWidgets.QLabel('Style:', self), 2, 0)
        layout.addWidget(self.bold_checkbox, 2, 1)
        layout.addWidget(self.italic_checkbox, 3, 1)
        layout.addWidget(self.underline_checkbox, 4, 1)
        layout.addWidget(self.strike_out_checkbox, 5, 1)


class AlignmentGroupBox(QtWidgets.QGroupBox):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__('Alignment', parent)
        self.radio_buttons = {
            x: QtWidgets.QRadioButton(
                [
                    '\N{SOUTH WEST ARROW}',
                    '\N{DOWNWARDS ARROW}',
                    '\N{SOUTH EAST ARROW}',
                    '\N{LEFTWARDS ARROW}',
                    '\N{BLACK DIAMOND}',
                    '\N{RIGHTWARDS ARROW}',
                    '\N{NORTH WEST ARROW}',
                    '\N{UPWARDS ARROW}',
                    '\N{NORTH EAST ARROW}',
                ][x - 1], self)
            for x in range(1, 10)
        }
        layout = QtWidgets.QGridLayout(self)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.addWidget(self.radio_buttons[7], 0, 0)
        layout.addWidget(self.radio_buttons[8], 0, 1)
        layout.addWidget(self.radio_buttons[9], 0, 2)
        layout.addWidget(self.radio_buttons[4], 1, 0)
        layout.addWidget(self.radio_buttons[5], 1, 1)
        layout.addWidget(self.radio_buttons[6], 1, 2)
        layout.addWidget(self.radio_buttons[1], 2, 0)
        layout.addWidget(self.radio_buttons[2], 2, 1)
        layout.addWidget(self.radio_buttons[3], 2, 2)

        for radio_button in self.radio_buttons.values():
            radio_button.toggled.connect(
                lambda _event: self.changed.emit())

    def get_value(self):
        for idx, radio_button in self.radio_buttons.items():
            if radio_button.isChecked():
                return idx
        return -1

    def set_value(self, value):
        if value in self.radio_buttons:
            self.radio_buttons[value].setChecked(True)

    value = QtCore.pyqtProperty(int, get_value, set_value)


class ColorsGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent):
        super().__init__('Colors', parent)
        self.primary_color_button = bubblesub.ui.util.ColorPicker(self)
        self.secondary_color_button = bubblesub.ui.util.ColorPicker(self)
        self.outline_color_button = bubblesub.ui.util.ColorPicker(self)
        self.back_color_button = bubblesub.ui.util.ColorPicker(self)

        layout = QtWidgets.QGridLayout(self)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        layout.addWidget(QtWidgets.QLabel('Primary:', self), 0, 0)
        layout.addWidget(self.primary_color_button, 0, 1)
        layout.addWidget(QtWidgets.QLabel('Secondary:', self), 1, 0)
        layout.addWidget(self.secondary_color_button, 1, 1)
        layout.addWidget(QtWidgets.QLabel('Outline:', self), 2, 0)
        layout.addWidget(self.outline_color_button, 2, 1)
        layout.addWidget(QtWidgets.QLabel('Shadow:', self), 3, 0)
        layout.addWidget(self.back_color_button, 3, 1)


class OutlineGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent):
        super().__init__('Outline', parent)
        self.outline_width_edit = QtWidgets.QDoubleSpinBox(
            self, minimum=0, maximum=999)
        self.shadow_width_edit = QtWidgets.QDoubleSpinBox(
            self, minimum=0, maximum=999)

        layout = QtWidgets.QGridLayout(self)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        layout.addWidget(QtWidgets.QLabel('Outline:', self), 0, 0)
        layout.addWidget(self.outline_width_edit, 0, 1)
        layout.addWidget(QtWidgets.QLabel('Shadow:', self), 1, 0)
        layout.addWidget(self.shadow_width_edit, 1, 1)


class MarginGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent):
        super().__init__('Margins', parent)
        self.margin_left_edit = QtWidgets.QSpinBox(
            self, minimum=0, maximum=999)
        self.margin_right_edit = QtWidgets.QSpinBox(
            self, minimum=0, maximum=999)
        self.margin_vertical_edit = QtWidgets.QSpinBox(
            self, minimum=0, maximum=999)

        layout = QtWidgets.QGridLayout(self)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        layout.addWidget(QtWidgets.QLabel('Left:', self), 0, 0)
        layout.addWidget(self.margin_left_edit, 0, 1)
        layout.addWidget(QtWidgets.QLabel('Right:', self), 1, 0)
        layout.addWidget(self.margin_right_edit, 1, 1)
        layout.addWidget(QtWidgets.QLabel('Vertical:', self), 2, 0)
        layout.addWidget(self.margin_vertical_edit, 2, 1)


class MiscGroupBox(QtWidgets.QGroupBox):
    def __init__(self, parent):
        super().__init__('Transformations', parent)
        self.scale_x_edit = QtWidgets.QDoubleSpinBox(
            self, minimum=0, maximum=999)
        self.scale_y_edit = QtWidgets.QDoubleSpinBox(
            self, minimum=0, maximum=999)
        self.angle_edit = QtWidgets.QDoubleSpinBox(
            self, minimum=0, maximum=999)
        self.spacing_edit = QtWidgets.QDoubleSpinBox(
            self, minimum=0, maximum=999)

        layout = QtWidgets.QGridLayout(self)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        layout.addWidget(QtWidgets.QLabel('Scale X:', self), 0, 0)
        layout.addWidget(self.scale_x_edit, 0, 1)
        layout.addWidget(QtWidgets.QLabel('Scale Y:', self), 1, 0)
        layout.addWidget(self.scale_y_edit, 1, 1)
        layout.addWidget(QtWidgets.QLabel('Angle:', self), 2, 0)
        layout.addWidget(self.angle_edit, 2, 1)
        layout.addWidget(QtWidgets.QLabel('Spacing:', self), 3, 0)
        layout.addWidget(self.spacing_edit, 3, 1)


class StyleEditor(QtWidgets.QWidget):
    def __init__(self, model, selection_model, parent):
        super().__init__(parent)
        self._model = model
        selection_model.selectionChanged.connect(self._selection_changed)

        self.font_group_box = FontGroupBox(self)
        self.colors_group_box = ColorsGroupBox(self)
        self.outline_group_box = OutlineGroupBox(self)
        self.margins_group_box = MarginGroupBox(self)
        self.misc_group_box = MiscGroupBox(self)
        self.alignment_group_box = AlignmentGroupBox(self)

        left_widget = QtWidgets.QWidget(self)
        left_layout = QtWidgets.QVBoxLayout(left_widget, margin=0)
        left_layout.addWidget(self.font_group_box)
        left_layout.addWidget(self.colors_group_box)
        left_layout.addWidget(self.outline_group_box)

        right_widget = QtWidgets.QWidget(self)
        right_layout = QtWidgets.QVBoxLayout(right_widget, margin=0)
        right_layout.addWidget(self.misc_group_box)
        right_layout.addWidget(self.margins_group_box)
        right_layout.addWidget(self.alignment_group_box)

        layout = QtWidgets.QHBoxLayout(self, margin=0)
        layout.addWidget(left_widget)
        layout.addWidget(right_widget)

        mapping = {
            StylesModelColumn.FontName:
                self.font_group_box.font_name_edit,
            StylesModelColumn.FontSize:
                self.font_group_box.font_size_edit,
            StylesModelColumn.Bold:
                self.font_group_box.bold_checkbox,
            StylesModelColumn.Italic:
                self.font_group_box.italic_checkbox,
            StylesModelColumn.Underline:
                self.font_group_box.underline_checkbox,
            StylesModelColumn.StrikeOut:
                self.font_group_box.strike_out_checkbox,
            StylesModelColumn.PrimaryColor:
                (self.colors_group_box.primary_color_button, b'color'),
            StylesModelColumn.SecondaryColor:
                (self.colors_group_box.secondary_color_button, b'color'),
            StylesModelColumn.BackColor:
                (self.colors_group_box.back_color_button, b'color'),
            StylesModelColumn.OutlineColor:
                (self.colors_group_box.outline_color_button, b'color'),
            StylesModelColumn.ShadowWidth:
                self.outline_group_box.shadow_width_edit,
            StylesModelColumn.OutlineWidth:
                self.outline_group_box.outline_width_edit,
            StylesModelColumn.ScaleX:
                self.misc_group_box.scale_x_edit,
            StylesModelColumn.ScaleY:
                self.misc_group_box.scale_y_edit,
            StylesModelColumn.Angle:
                self.misc_group_box.angle_edit,
            StylesModelColumn.Spacing:
                self.misc_group_box.spacing_edit,
            StylesModelColumn.MarginLeft:
                self.margins_group_box.margin_left_edit,
            StylesModelColumn.MarginRight:
                self.margins_group_box.margin_right_edit,
            StylesModelColumn.MarginVertical:
                self.margins_group_box.margin_vertical_edit,
            StylesModelColumn.Alignment:
                (self.alignment_group_box, b'value'),
        }

        self.mapper = QtWidgets.QDataWidgetMapper()
        self.mapper.setModel(self._model)
        for column_idx, widget in mapping.items():
            if isinstance(widget, tuple):
                widget, class_property = widget
                self.mapper.addMapping(widget, column_idx, class_property)
            else:
                self.mapper.addMapping(widget, column_idx)

        self._connect_signals()

    def _selection_changed(self, event):
        if event.indexes():
            self.setEnabled(True)
            self.mapper.setCurrentIndex(event.indexes()[0].row())
        else:
            self.setEnabled(False)

    def _connect_signals(self):
        self.mapper.setSubmitPolicy(QtWidgets.QDataWidgetMapper.ManualSubmit)
        for widget in [
            self.font_group_box.font_name_edit
        ]:
            widget.textChanged.connect(self._submit)

        for widget in [
            self.colors_group_box.primary_color_button,
            self.colors_group_box.secondary_color_button,
            self.colors_group_box.back_color_button,
            self.colors_group_box.outline_color_button,
            self.alignment_group_box,
        ]:
            widget.changed.connect(self._submit)

        for widget in [
            self.font_group_box.font_size_edit,
            self.outline_group_box.shadow_width_edit,
            self.outline_group_box.outline_width_edit,
            self.misc_group_box.scale_x_edit,
            self.misc_group_box.scale_y_edit,
            self.misc_group_box.angle_edit,
            self.misc_group_box.spacing_edit,
            self.margins_group_box.margin_left_edit,
            self.margins_group_box.margin_right_edit,
            self.margins_group_box.margin_vertical_edit,
        ]:
            widget.valueChanged.connect(self._submit)

        for widget in [
            self.font_group_box.bold_checkbox,
            self.font_group_box.italic_checkbox,
            self.font_group_box.underline_checkbox,
            self.font_group_box.strike_out_checkbox,
        ]:
            widget.toggled.connect(self._submit)

    def _submit(self, *_args):
        self.mapper.submit()


class StylesManagerDialog(QtWidgets.QDialog):
    def __init__(self, api, main_window):
        super().__init__(main_window)
        model = StylesModel(api)
        selection_model = QtCore.QItemSelectionModel(model)

        self._style_list = StyleList(api, model, selection_model, self)
        self._style_editor = StyleEditor(model, selection_model, self)
        self._style_editor.setEnabled(False)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self._style_list)
        layout.addWidget(self._style_editor)


class StylesManagerCommand(CoreCommand):
    name = 'edit/manage-styles'
    menu_name = 'Manage styles...'

    def enabled(self):
        return True

    async def run(self):
        async def run(api, main_window):
            StylesManagerDialog(api, main_window).exec_()

        await self.api.gui.exec(run)
