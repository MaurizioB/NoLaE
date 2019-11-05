from PyQt5 import QtCore, QtGui, uic
from . import icons
from collections import namedtuple
from itertools import cycle

from .const import *
from .classes import *
from .utils import *

TPatch = namedtuple('TPatch', 'label patch input')
TPatch.__new__.__defaults__ = (None, ) * len(TPatch._fields)
TPatch.__new__.__defaults__ = (None, )

class NoTextDelegate(QtWidgets.QStyledItemDelegate):
    def displayText(self, value, locale):
        return ''

class OutputWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        uic.loadUi('output_widget.ui', self)
        self.main = self.parent()

class EditorWin(QtWidgets.QMainWindow):
    labelChanged = QtCore.pyqtSignal(object, object)
    widgetSaved = QtCore.pyqtSignal(int)

    def __init__(self, parent=None, mode='control'):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.main = self.parent()
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.conf_dict = self.main.conf_dict
        self.map_dict = self.main.map_dict
        uic.loadUi('patch.ui', self)
        self.statusbar_create()
        self.patch_edit.textChanged.connect(self.patch_update)
        self.patch = ''
        self.patch_edit.valid = False
        self.main.widgetChanged.connect(self.widget_change)
        self.main.widgetUpdated.connect(self.widget_change)
        self.patch_edit.focusInEvent = self.patch_edit_focusIn
        self.patch_edit.focusOutEvent = self.patch_edit_focusOut
        self.enable_chk.toggled.connect(self.enable_set)
        self.led_select_btn.clicked.connect(self.led_select)
        self.led_reset_btn.clicked.connect(self.led_reset)
        self.main.outputChanged.connect(self.output_update)
        self.dest_combo.currentIndexChanged.connect(self.dest_update)
        self.led_combo.currentIndexChanged.connect(self.led_combo_update)
        self.text_edit.textEdited.connect(self.text_update)
        self.led_base_flash_chk.toggled.connect(lambda state: self.led_flash_combo.setEnabled(state))
        self.led_action_combo.lineEdit().textEdited.connect(self.led_action_text_update)
        self.led_action_combo.currentIndexChanged.connect(self.led_action_update)
        self.led_action_adv_chk.toggled.connect(lambda state: self.led_action_adv_combo.setEnabled(state))
        self.restore_btn.clicked.connect(self.widget_restore)
        self.tool_group.setEnabled = self.tool_group_setEnabled
        self.toggle_chk.toggled.connect(self.toggle_set)
        self.toggle_listview.wheelEvent = self.toggle_chk_wheelEvent
        self.toggle_add_btn.clicked.connect(self.toggle_value_add)
        self.toggle_remove_btn.clicked.connect(self.toggle_value_remove)
        self.toggle_listview.closeEditor = self.toggle_validate
#        self.toggle_listview.focusOutEvent = lambda event: self.toggle_listview.clearSelection()
        self.toggle_colors_edit_btn.clicked.connect(self.toggle_colors_edit)
        self.range_chk.toggled.connect(self.range_set)
        self.convert_chk.toggled.connect(self.convert_set)
        self.chan_reset_btn.clicked.connect(self.chan_reset)
        self.convert_ctrl_radio.toggled.connect(self.convert_group_toggle)
        self.convert_note_radio.toggled.connect(self.convert_group_toggle)
        self.convert_sysex_radio.toggled.connect(self.convert_group_toggle)
        self.force_note_change_radio.toggled.connect(self.force_note_change_toggle)
        self.convert_piano_btn.clicked.connect(self.piano_show)
        self.force_sysex_btn.clicked.connect(self.sysex_input)
        self.force_sysex_listview.edit = self.sysex_edit
        self.force_sysex_listview.closeEditor = self.sysex_validate
        self.force_sysex_spin.valueChanged.connect(self.sysex_highlight)

        self.convert_ctrl_radio.id = ToCtrl
        self.convert_note_radio.id = ToNote
        self.convert_sysex_radio.id = ToSysEx
        self.sysex_create()

        self.current_widget = None
        self.output_update()
        self.models_setup()
        self.base_group.setEnabled(False)
        self.patch_group.setEnabled(False)
        self.convert_set(False)
        self.patch_templates_menu_create()
        self.patch_toolbtn.setMenu(self.patch_templates)
#        self.toggle_set(False)
        metrics = QtGui.QFontMetrics(self.patch_edit.font())
        self.patch_edit.setTabStopWidth(4*metrics.width(' '))

        self.piano = Piano(self)
        self.piano.setModal(True)
        self.led_dialog = LedGrid(self)
        self.led_dialog.setModal(True)
        self.sysex_dialog = SysExDialog(self)
        self.sysex_dialog.setModal(True)
        saveAction = QAction(self)
        saveAction.setShortcut('Ctrl+s')
        saveAction.triggered.connect(self.main_save)
        self.addAction(saveAction)

        self.toggle_timer = QtCore.QTimer()
        self.toggle_timer.setInterval(500)
        self.toggle_timer.timeout.connect(self.toggle_flash)
        self.toggle_start()

    def toggle_start(self):
        self.toggle_timer_status = cycle([LedPixmapRole, LedFlashPixmapRole])
        self.toggle_flash()
        self.toggle_timer.start()

    def toggle_chk_wheelEvent(self, event):
        if event.orientation() == QtCore.Qt.Vertical:
            hbar = self.toggle_listview.horizontalScrollBar()
            if event.delta() < 1:
                hbar.setValue(hbar.value()+hbar.pageStep())
            else:
                hbar.setValue(hbar.value()-hbar.pageStep())

    def toggle_validate(self, delegate, hint):
        QtGui.QListView.closeEditor(self.toggle_listview, delegate, hint)
        index = self.toggle_listview.currentIndex().row()
        item = self.toggle_listview.model().item(index, 0)
        value = item.text()
        try:
            int_value = int(value)
            if int_value < 0:
                item.setText('0')
            elif int_value > 127:
                item.setText('127')
        except:
            item.setText('127')

    def toggle_set(self, value):
        self.toggle_listview.setEnabled(value)
        self.toggle_remove_btn.setEnabled(value)
        self.toggle_add_btn.setEnabled(value)
        self.toggle_colors_edit_btn.setEnabled(value)
        if not self.current_widget:
            return
        if value:
            if not (self.current_widget.get('toggle') or self.current_widget.get('toggle_values') or self.current_widget.get('toggle_model')):
                toggle_model = QtGui.QStandardItemModel()
                led_type = get_led_type(self.led_combo.currentIndex()-1)
                for i in [0, 127]:
                    item = QtGui.QStandardItem(str(i))
                    item.setFlags(item.flags() ^ QtCore.Qt.ItemIsDropEnabled)
                    toggle_model.appendRow(item)
                    if led_type is None: continue
                    if led_type == FullColors:
                        color = led_full_scale[i]
                        pixmap = self.colormap_full_pixmap[(color&3, color>>4)]
                    elif led_type == DevColors:
                        color = led_dev_scale[i]
                        pixmap = self.colormap_dev_pixmap[1 if i==0 else -1]
                    else:
                        color = led_dir_scale[i]
                        pixmap = self.colormap_dir_pixmap[1 if i==0 else -1]
                    item.setData(color, LedRole)
                    item.setData(pixmap, LedPixmapRole)
                self.current_widget['toggle_values'] = (0, 127)
                self.current_widget['toggle_model'] = toggle_model
                self.toggle_listview.setModel(toggle_model)
            self.toggle_colors_edit_btn.setEnabled(self.led_combo.currentIndex())
            self.range_chk.setChecked(False)
        self.current_widget['toggle'] = value

    def toggle_value_add(self):
        if self.toggle_listview.model().rowCount() > 16:
            return
        item = QtGui.QStandardItem('127')
        item.setFlags(item.flags() ^ QtCore.Qt.ItemIsDropEnabled)
        led_type = get_led_type(self.led_combo.currentIndex()-1)
        if led_type is not None:
            if led_type == FullColors:
                color = led_full_scale[i]
                pixmap = self.colormap_full_pixmap[(color&3, color>>4)]
            elif led_type == DevColors:
                color = led_dev_scale[i]
                pixmap = self.colormap_dev_pixmap[1 if i==0 else -1]
            else:
                color = led_dir_scale[i]
                pixmap = self.colormap_dir_pixmap[1 if i==0 else -1]
            item.setData(color, LedRole)
            item.setData(pixmap, LedPixmapRole)
        self.toggle_listview.model().appendRow(item)
        self.toggle_range_check()

    def toggle_value_remove(self):
        if self.toggle_listview.model().rowCount() <= 2:
            return
        index = self.toggle_listview.currentIndex().row()
        if index < 0:
            index = self.toggle_listview.model().rowCount()-1
        self.toggle_listview.model().takeRow(index)
        self.toggle_range_check()

    def toggle_range_check(self):
        if not self.toggle_listview.model():
            return
        if self.toggle_listview.model().rowCount() >= 8:
            self.toggle_add_btn.setEnabled(False)
        else:
            self.toggle_add_btn.setEnabled(True)
        if self.toggle_listview.model().rowCount() <= 2:
            self.toggle_remove_btn.setEnabled(False)
        else:
            self.toggle_remove_btn.setEnabled(True)

    def toggle_colors_edit(self):
        led = self.led_combo.currentIndex()
        if led == 0:
            return
        dialog = ToggleColors(self, get_led_type(led-1))
        res = dialog.exec_()
        if res:
            model, scale = res
            self.toggle_listview.setModel(model)
            self.current_widget['toggle_model'] = model
            self.current_widget['led_scale'] = scale

    def toggle_flash(self):
        model = self.toggle_listview.model()
        if model is None or model.rowCount() <= 0: return
        led_role = next(self.toggle_timer_status)
        for i in range(model.rowCount()):
            item = model.item(i)
            pixmap = item.data(led_role).toPyObject()
            if pixmap is not None:
                item.setData(pixmap, QtCore.Qt.DecorationRole)


    def range_set(self, value):
        self.range_min_spin.setEnabled(value)
        self.range_max_spin.setEnabled(value)
        self.range_combo.setEnabled(True if value and not isinstance(self.current_widget.get('widget'), QtWidgets.QPushButton) else False)
        self.range_min_lbl.setEnabled(value)
        self.range_max_lbl.setEnabled(value)
        self.range_scale_lbl.setEnabled(True if value and not isinstance(self.current_widget.get('widget'), QtWidgets.QPushButton) else False)
        if value:
            self.toggle_chk.setChecked(False)
            if not self.current_widget.get('range'):
                self.current_widget['range'] = True
                self.current_widget['range_values'] = (0, 127, 0)
        else:
            self.current_widget['range'] = False

    def convert_set(self, value):
        for button in self.convert_group.buttons():
            button.setEnabled(value)
        self.force_note_frame.setVisible(value)
        self.force_sysex_frame.setVisible(value)
        self.force_ctrl_frame.setVisible(value)
        if self.convert_ctrl_radio.isChecked():
            ctrl = True
            note = sysex = False
        elif self.convert_note_radio.isChecked():
            note = True
            ctrl = sysex = False
        else:
            sysex = True
            note = ctrl = False
        self.force_ctrl_lbl.setEnabled(ctrl)
        self.force_ctrl_spin.setEnabled(ctrl)
        self.force_note_toggle_chk.setEnabled(note)
        self.force_note_event_lbl.setEnabled(note)
        self.force_note_change_radio.setEnabled(note)
        self.force_vel_change_radio.setEnabled(note)
        self.force_note_lbl.setEnabled(note)
        self.force_note_combo.setEnabled(True if (note and self.force_vel_change_radio.isChecked()) else False)
        self.convert_piano_btn.setEnabled(True if (note and self.force_vel_change_radio.isChecked()) else False)
        self.force_vel_lbl.setEnabled(note)
        self.force_vel_spin.setEnabled(note)
        self.force_sysex_listview.setEnabled(sysex)
        self.force_sysex_btn.setEnabled(sysex)
        self.force_sysex_lbl.setEnabled(sysex)
        self.force_sysex_spin.setEnabled(sysex)

    def convert_group_toggle(self, value):
        if not value:
            return
        if self.sender() == self.convert_ctrl_radio:
            ctrl = True
            note = sysex = False
        elif self.sender() == self.convert_note_radio:
            note = True
            ctrl = sysex = False
        else:
            sysex = True
            note = ctrl = False
        self.force_ctrl_lbl.setEnabled(ctrl)
        self.force_ctrl_spin.setEnabled(ctrl)
        self.force_note_toggle_chk.setEnabled(note)
        self.force_note_event_lbl.setEnabled(note)
        self.force_note_change_radio.setEnabled(note)
        self.force_vel_change_radio.setEnabled(note)
        self.force_note_lbl.setEnabled(note)
        self.force_note_combo.setEnabled(True if (note and self.force_vel_change_radio.isChecked()) else False)
        self.convert_piano_btn.setEnabled(True if (note and self.force_vel_change_radio.isChecked()) else False)
        self.force_vel_lbl.setEnabled(note)
        self.force_vel_spin.setEnabled(note)
        self.force_sysex_listview.setEnabled(sysex)
        self.force_sysex_btn.setEnabled(sysex)
        self.force_sysex_lbl.setEnabled(sysex)
        self.force_sysex_spin.setEnabled(sysex)

    def force_note_change_toggle(self, value):
        self.force_note_combo.setEnabled(not value)
        self.convert_piano_btn.setEnabled(not value)

    def sysex_create(self, values=None):
        self.sysex_model = QtGui.QStandardItemModel()
        if not values:
            for sysex in ['F0', '00', 'F7']:
                item = QtGui.QStandardItem(sysex)
                self.sysex_model.appendRow(item)
        else:
            if values[0] != 0xf0 or len(values) < 2:
                item = QtGui.QStandardItem('F0')
                self.sysex_model.appendRow(item)
            for byte in values:
                item = QtGui.QStandardItem('{:02X}'.format(byte))
                item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable)
                self.sysex_model.appendRow(item)
            if values[-1] != 0xf7:
                item = QtGui.QStandardItem('F7')
                self.sysex_model.appendRow(item)
        self.sysex_model.item(0).setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable)
        self.sysex_model.item(self.sysex_model.rowCount()-1).setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable)
        self.force_sysex_listview.setModel(self.sysex_model)
        self.force_sysex_spin.setMaximum(self.sysex_model.rowCount()-2)
        self.sysex_highlight(self.force_sysex_spin.value())

    def sysex_input(self):
        if self.sysex_model.rowCount() > 3:
            sysex = ' '.join([str(self.sysex_model.item(i).text()) for i in range(self.sysex_model.rowCount())])
        else:
            sysex = None
        res = self.sysex_dialog.exec_(sysex)
        if not res:
            return
        self.sysex_create(res)

    def sysex_edit(self, index, trigger, event):
        self.sysex_old = self.sysex_model.itemFromIndex(index).text()
        return QtGui.QListView.edit(self.force_sysex_listview, index, trigger, event)

    def sysex_validate(self, delegate, hint):
        QtGui.QListView.closeEditor(self.force_sysex_listview, delegate, hint)
        index = self.force_sysex_listview.currentIndex().row()
        item = self.force_sysex_listview.model().item(index, 0)
        value = item.text()
        try:
            int_value = int(value)
            if int_value < 0:
                item.setText('0')
        except:
            try:
                item.setText('{:02X}'.format(int(value, 16)))
            except:
                item.setText(self.sysex_old)

    def sysex_highlight(self, index):
        for i in range(1, self.sysex_model.rowCount()):
            setBold(self.sysex_model.item(i), False)
        setBold(self.sysex_model.item(index))


    def closeEvent(self, event):
        if self.current_widget:
            self.widget_save()

    def event(self, event):
        if event.type() == QtCore.QEvent.WindowDeactivate:
            self.widget_save()
        return QtWidgets.QMainWindow.event(self, event)

    def main_save(self, *args):
        self.widget_save()
        self.main.config_save()
        self.main.title_set()


    def patch_templates_menu_create(self):
        action_dict = [(
                       'Ctrl value split', (
                            TPatch('2 value filter to 0, 127', 'CtrlValueSplit({(0,63): Ctrl(EVENT_DATA1, 0), (64,127): Ctrl(EVENT_DATA1, 127)})'), 
                            TPatch('3 value filter to 0, 64, 127', 'CtrlValueSplit({(0,42): Ctrl(EVENT_DATA1, 0), (43,84): Ctrl(EVENT_DATA1, 64), (85,127): Ctrl(EVENT_DATA1, 127)})'), 
                            TPatch('4 value filter to 0, 32, 64, 127', 'CtrlValueSplit({(0,31): Ctrl(EVENT_DATA1, 0), (32,63): Ctrl(EVENT_DATA1, 42), (64,95): Ctrl(EVENT_DATA1, 84), (96, 127): Ctrl(EVENT_DATA1, 127)})'), 
                            TPatch('6 value filter to 0, 26, 51, 77, 102, 127', 'CtrlValueSplit({(0,21): Ctrl(EVENT_DATA1, 0), (22,42): Ctrl(EVENT_DATA1, 26), (43,63): Ctrl(EVENT_DATA1, 51), (64, 85): Ctrl(EVENT_DATA1, 77), (86, 106): Ctrl(EVENT_DATA1, 102), (107, 127): Ctrl(EVENT_DATA1, 127)})')
                       )), (
                       'Ctrl Remap', (
                            TPatch('Remap to Ctrl...', 'Ctrl({}, EVENT_VALUE)', ((int, 127, 'Set Ctrl number to remap to'), )), 
                       )), 
#                       TPatch('Test',  'oirgour'), 
                      ]
        self.patch_templates = QtGui.QMenu()
#        print action_dict.items()
        for item in action_dict:
            if isinstance(item, TPatch):
                action = QAction(item.label, self)
                action.patch = item.patch
                if item.input:
                    action.input = item.input
                else:
                    action.input = None
                action.triggered.connect(self.patch_template_set)
                self.patch_templates.addAction(action)
            else:
                label, patch_list = item
                submenu = self.patch_templates.addMenu(label)
                for tpatch in patch_list:
                    action = QAction(tpatch.label, self)
                    action.patch = tpatch.patch
                    if tpatch.input:
                        action.input = tpatch.input
                    else:
                        action.input = None
                    action.triggered.connect(self.patch_template_set)
                    submenu.addAction(action)

    def patch_template_set(self):
        action = self.sender()
        patch = action.patch
        if action.input:
            for req in action.input:
                if req[0] == int:
                    value, res = QtWidgets.QInputDialog.getInt(self, action.text(), req[-1], min=0, max=req[1])
                    if not res:
                        return
                    patch = patch.format(value)
                
        if self.patch_edit.toPlainText().toLatin1() == 'Pass()':
            self.patch_edit.setPlainText(patch)
            return
        doc = self.patch_edit.document()
        excursor = self.patch_edit.textCursor()
        cursor = QtGui.QTextCursor(doc)
        cursor.setPosition(excursor.position())
        cursor.insertText(patch)

    def widget_restore(self):
        self.clear_fields(False)
        self.labelChanged.emit(self.current_widget['widget'], True)

    def clear_fields(self, disable=True):
        self.dest_combo.setCurrentIndex(0)
        self.text_edit.setText('')
        if self.current_widget:
            widget = self.current_widget['widget']
            self.led_combo.setCurrentIndex(widget.siblingLed+1 if widget.siblingLed else 0)
        else:
            self.led_combo.setCurrentIndex(0)
        self.led_base_combo.setCurrentIndex(0)
        self.led_base_combo.setModelColumn(0)
        self.led_action_combo.setCurrentIndex(-1)
#        self.led_action_combo.setModelColumn(0)
        self.patch_edit.setPlainText('')
        if disable:
            self.enable_chk.setChecked(False)

    def output_update(self):
        prev_index = self.dest_combo.currentIndex()
        self.dest_combo.blockSignals(True)
        self.output_model = QtGui.QStandardItemModel(self.dest_combo)
        self.dest_combo.setModel(self.output_model)
        for i in range(self.main.output_model.rowCount()):
            item = self.main.output_model.item(i).clone()
            item.setText('{}: {}{}'.format(i+1, item.text(), ' (default)' if i == 0 else ''))
            font = item.font()
            font.setBold(False)
            item.setFont(font)
            self.output_model.appendRow(item)
        if self.current_widget and prev_index > 0:
            if prev_index >= self.output_model.rowCount():
                prev_index = self.output_model.rowCount()-1
                self.dest_combo.blockSignals(False)
            self.dest_combo.setCurrentIndex(prev_index)
        self.dest_combo.blockSignals(False)

    def models_setup(self):
        def create_table():
            table = QtGui.QTableView(self)
            table.setShowGrid(False)
            table.verticalHeader().hide()
            table.horizontalHeader().hide()
            table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
            table.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
            return table

        #Led list
        self.ledlist_model = QtGui.QStandardItemModel(self.led_combo)
        self.led_combo.setModel(self.ledlist_model)
        item = QtGui.QStandardItem('Disabled')
        item.led = None
        item.ledSet = None
        item.ledTrigger = None
        self.ledlist_model.appendRow(item)
        for widget in self.main.widget_order:
            if widget.siblingLed == None:
                continue
            item = QtGui.QStandardItem(widget.readable)
            item.led = widget.siblingLed
            item.ledSet = widget.ledSet
            item.ledTrigger = widget.ledTrigger
            self.ledlist_model.appendRow(item)

        #LED base color combo
        self.colormap_full_pixmap = {(r, g):get_pixmap(r*85, g*85) for r in range(4) for g in range(4)}
        self.colormap_full_model = QtGui.QStandardItemModel()
        self.colormap_flash_model = QtGui.QStandardItemModel()
        self.led_base_combo.setModel(self.colormap_full_model)
        self.led_flash_combo.setModel(self.colormap_flash_model)
        self.color_table = create_table()
        self.color_table.selectionChanged = lambda sel, prev, combo=self.led_base_combo: self.color_column_check(combo, sel, prev)
        self.flash_color_table = create_table()
        self.flash_color_table.selectionChanged = lambda sel, prev, combo=self.led_flash_combo: self.color_column_check(combo, sel, prev)
        self.led_base_combo.setView(self.color_table)
        self.led_flash_combo.setView(self.flash_color_table)
        for row in range(4):
            row_list = []
            flash_row_list = []
            for col in range(4):
                item = QtGui.QStandardItem()
                item.setData(row+col*16, LedRole)
                item.setIcon(QtGui.QIcon(self.colormap_full_pixmap[row, col]))
                row_list.append(item)

                flash_row_list.append(item.clone())
            self.colormap_full_model.appendRow(row_list)
            self.colormap_flash_model.appendRow(flash_row_list)
            self.color_table.resizeColumnToContents(row)
            self.flash_color_table.resizeColumnToContents(row)
        min_width = sum([self.color_table.columnWidth(c) for c in range(self.colormap_full_model.columnCount())])
        self.color_table.setMinimumWidth(min_width)
        self.flash_color_table.setMinimumWidth(min_width)

        self.colormap_dev_pixmap = [get_pixmap(r*42, r*38) for r in range(len(dev_scale))]
        self.colormap_dev_model = QtGui.QStandardItemModel()
        self.colormap_dev_flash_model = QtGui.QStandardItemModel()
        for l in range(len(dev_scale)):
            led_value = dev_scale[l]
            item = QtGui.QStandardItem()
            item.setData(led_value, LedRole)
            item.setIcon(QtGui.QIcon(self.colormap_dev_pixmap[l]))
            self.colormap_dev_model.appendRow(item)
            self.colormap_dev_flash_model.appendRow(item.clone())
        self.led_base_combo.setSizeAdjustPolicy(self.led_base_combo.AdjustToContents)
        self.led_flash_combo.setSizeAdjustPolicy(self.led_flash_combo.AdjustToContents)

        self.colormap_dir_pixmap = [get_pixmap(r*51) for r in range(len(dir_scale))]
        self.colormap_dir_model = QtGui.QStandardItemModel()
        self.colormap_dir_flash_model = QtGui.QStandardItemModel()
        for l in range(len(dir_scale)):
            led_value = dir_scale[l]
            item = QtGui.QStandardItem()
            item.setData(led_value, LedRole)
            item.setIcon(QtGui.QIcon(self.colormap_dir_pixmap[l]))
            self.colormap_dir_model.appendRow(item)
            self.colormap_dir_flash_model.appendRow(item.clone())

        #LED action combo
        self.action_table = create_table()
        self.action_table.selectionChanged = lambda sel, prev, combo=self.led_action_combo: self.action_column_check(combo, sel, prev)
        self.led_action_combo.setView(self.action_table)
        self.action_full_model = QtGui.QStandardItemModel()
        self.led_action_combo.setModel(self.action_full_model)
        pass_item = QtGui.QStandardItem('Pass')
        disc_item = QtGui.QStandardItem('Ignore')
        self.toggle_item = QtGui.QStandardItem('Toggle')
        self.action_full_model.appendRow([pass_item, disc_item, self.toggle_item])
        self.action_table.setSpan(0, 2, 1, 2)
        self.action_table.resizeRowToContents(0)

        self.action_flash_table = create_table()
        self.action_flash_table.selectionChanged = lambda sel, prev, combo=self.led_action_adv_combo: self.action_column_check(combo, sel, prev)
        self.led_action_adv_combo.setView(self.action_flash_table)
        self.action_flash_model = QtGui.QStandardItemModel()
        self.led_action_adv_combo.setModel(self.action_flash_model)

        for row in range(4):
            row_list = []
            flash_row_list = []
            for col in range(4):
                row_list.append(self.colormap_full_model.item(row, col).clone())
                flash_row_list.append(self.colormap_flash_model.item(row, col).clone())
            self.action_full_model.appendRow(row_list)
            self.action_flash_model.appendRow(flash_row_list)
            self.action_table.resizeColumnToContents(row)
            self.action_flash_table.resizeColumnToContents(row)
        self.action_table.setMinimumWidth(sum([self.action_table.columnWidth(c) for c in range(self.action_full_model.columnCount())]))
        self.action_flash_table.setMinimumWidth(sum([self.action_flash_table.columnWidth(c) for c in range(self.action_flash_model.columnCount())]))
        self.action_dev_model = QtGui.QStandardItemModel()
        self.action_dev_model.appendColumn([pass_item.clone(), disc_item.clone(), self.toggle_item.clone()])
        self.action_dev_flash_model = QtGui.QStandardItemModel()
        for l in range(len(dev_scale)):
            item = self.colormap_dev_model.item(l).clone()
            self.action_dev_model.appendRow(item)
            self.action_dev_flash_model.appendRow(item.clone())
        self.action_dir_model = QtGui.QStandardItemModel()
        self.action_dir_model.appendColumn([pass_item.clone(), disc_item.clone(), self.toggle_item.clone()])
        self.action_dir_flash_model = QtGui.QStandardItemModel()
        for l in range(len(dir_scale)):
            item = self.colormap_dir_model.item(l).clone()
            self.action_dir_model.appendRow(item)
            self.action_dir_flash_model.appendRow(item.clone())

        self.action_scale_model = QtGui.QStandardItemModel()
        for i, scale in enumerate([full_scale, full_revscale, full_mirrorscale, full_mirrorrevscale, full_volscale]):
            item = QtGui.QStandardItem()
            item.setIcon(QtGui.QIcon(scale_full_pixmap(scale)))
            item.setData(led_full_scale_list[i], ScaleRole)
            self.action_scale_model.appendRow(item)
        self.action_dev_scale_model = QtGui.QStandardItemModel()
        for i, scale in enumerate([dev_scale[1:], dev_revscale, dev_mirrorscale, dev_mirrorrevscale, dev_volscale]):
            item = QtGui.QStandardItem()
            item.setIcon(QtGui.QIcon(scale_dev_pixmap(scale)))
            item.setData(led_dev_scale_list[i], ScaleRole)
            self.action_dev_scale_model.appendRow(item)
        self.action_dir_scale_model = QtGui.QStandardItemModel()
        for i, scale in enumerate([dir_scale[1:], dir_revscale, dir_mirrorscale, dir_mirrorrevscale, dir_volscale]):
            item = QtGui.QStandardItem()
            item.setIcon(QtGui.QIcon(scale_dir_pixmap(scale)))
            item.setData(led_dir_scale_list[i], ScaleRole)
            self.action_dir_scale_model.appendRow(item)

#        self.action_scale_table = create_table()
#        self.action_scale_table.setIconSize(QtCore.QSize(64, 16))
#        self.action_scale_table.resizeColumnsToContents()
#        self.action_scale_table.resizeRowsToContents()
#        adv_width = sum([self.action_scale_table.columnWidth(c) for c in range(self.action_scale_model.columnCount())])
#        self.action_scale_table.setMinimumWidth(adv_width)
#        self.action_scale_table.setMaximumWidth(adv_width)

        #setting default leds:
        setBold(self.colormap_full_model.item(0, 3))
        setBold(self.colormap_dev_model.item(1))
        setBold(self.colormap_dir_model.item(1))
        setBold(self.action_full_model.item(4, 3))
        setBold(self.action_dev_model.item(9))
        setBold(self.action_dir_model.item(8))

        #creating notes for force_note_combo
        self.note_model = QtGui.QStandardItemModel()
        item = QtGui.QStandardItem('(incoming)')
        self.note_model.appendRow(item)
        for n in range(128):
            note_name = md.util.note_name(n).upper()
            if '#' in note_name:
                note_name = '{} {}'.format(note_name[:2], note_name[2:])
            else:
                note_name = '{} {}'.format(note_name[:1], note_name[1:])
            item = QtGui.QStandardItem(note_name)
            self.note_model.appendRow(item)
        for o in range(11):
            setBold(self.note_model.item(o*12+1, 0))
        self.force_note_combo.setModel(self.note_model)


    def color_column_check(self, combo, selected, previous):
        index = combo.view().selectedIndexes()[0]
        combo.setModelColumn(index.column())
        combo.setCurrentIndex(index.row())

    def action_column_check(self, combo, selected, previous):
        index = combo.view().selectedIndexes()
        if index:
            combo.setModelColumn(index[0].column())
            combo.setCurrentIndex(index[0].row())
        else:
            print('What\'s wrong with index? {}'.format(index))
            combo.setModelColumn(0)
            combo.setCurrentIndex(0)

    def enable_set(self, value):
        #TODO: if no patch and no dict value, just clear!
        #maybe we don't need this anymore?
        if not self.current_widget:
            #we need to set these for startup and template change
            if not value:
                self.base_group.setEnabled(value)
                self.patch_group.setEnabled(value)
            return
        self.base_group.setEnabled(value)
        self.patch_group.setEnabled(value)
        self.current_widget['enabled'] = value
        self.tool_group.setEnabled(value)
        self.patch_edit.setStyleSheet('color: {}'.format(patch_colors[self.patch_edit.valid][value]))
        if value:
            patch = self.current_widget.get('patch')
            text = self.current_widget.get('text')
            if not text:
                text = patch if patch else None
            self.labelChanged.emit(self.current_widget['widget'], text if text else True)
        else:
            self.labelChanged.emit(self.current_widget['widget'], False)

    def tool_group_setEnabled(self, value):
        for button in self.tool_group.buttons():
            button.setEnabled(value)
#        self.toggle_listview.setEnabled(value)
#        if self.current_widget:
#            if not isinstance(self.current_widget['widget'], QtWidgets.QPushButton):
#                for button in self.convert_group.buttons():
#                    button.setEnabled(False)
#                self.convert_chk.setEnabled(False)
#                self.convert_chk.setChecked(False)
#    #            self.toggle_chk.setEnabled(False)
#    #            self.toggle_chk.setChecked(False)
#                toggle_model = QtGui.QStandardItemModel()
#                self.toggle_listview.setModel(toggle_model)
#            else:
#                pass
        if value:
            self.toggle_range_check()
        else:
            self.toggle_listview.setEnabled(False)
            self.range_min_spin.setEnabled(False)
            self.range_max_spin.setEnabled(False)
            self.range_combo.setEnabled(False)
            self.range_min_lbl.setEnabled(False)
            self.range_max_lbl.setEnabled(False)
            self.range_scale_lbl.setEnabled(False)
#            self.force_ctrl_frame.setEnabled(False)
            self.force_ctrl_frame.setVisible(False)
#            self.force_note_frame.setEnabled(False)
            self.force_note_frame.setVisible(False)
            self.force_sysex_frame.setVisible(False)

    def chan_reset(self):
        self.chan_spin.setValue(0)

    def led_reset(self):
        default_led = self.current_widget['widget'].siblingLed
        self.led_combo.setCurrentIndex(default_led+1 if default_led is not None else 0)

    def led_combo_update(self, led):
        if not self.current_widget:
            return
        widget = self.current_widget['widget']
        if led == 0:
            self.led_base_combo.setEnabled(False)
            self.led_action_combo.setEnabled(False)
            self.toggle_colors_edit_btn.setEnabled(False)
            if self.current_widget.get('led'):
                if isinstance(widget, QtGui.QSlider):
                    self.current_widget.pop('led')
                else:
                    self.current_widget['led'] = False
            return
        self.led_base_combo.setEnabled(True)
        self.led_action_combo.setEnabled(True)
        if isinstance(widget, QtWidgets.QPushButton):
            is_scale = False
            self.action_flash_table.setIconSize(QtCore.QSize(16, 16))
        else:
            is_scale = True
            self.action_flash_table.setIconSize(QtCore.QSize(64, 16))
        led_type = get_led_type(led-1)
        if led_type == FullColors:
            if self.led_base_combo.model() != self.colormap_full_model:
                self.led_base_combo.setModel(self.colormap_full_model)
                self.led_flash_combo.setModel(self.colormap_flash_model)
                self.led_action_combo.setModel(self.action_full_model)
            if is_scale:
                self.led_action_adv_combo.setModel(self.action_scale_model)
            else:
                self.led_action_adv_combo.setModel(self.action_flash_model)
        elif led_type == DevColors:
            if self.led_base_combo.model() != self.colormap_dev_model:
                self.led_base_combo.setModelColumn(0)
                self.led_base_combo.setModel(self.colormap_dev_model)
                self.led_flash_combo.setModel(self.colormap_dev_flash_model)
                self.led_action_combo.setModelColumn(0)
                self.led_action_combo.setModel(self.action_dev_model)
            self.led_action_adv_combo.setModel(self.action_dev_scale_model if is_scale else self.action_dev_flash_model)
        else:
            if self.led_base_combo.model() != self.colormap_dir_model:
                self.led_base_combo.setModelColumn(0)
                self.led_base_combo.setModel(self.colormap_dir_model)
                self.led_flash_combo.setModel(self.colormap_dir_flash_model)
                self.led_action_combo.setModelColumn(0)
                self.led_action_combo.setModel(self.action_dir_model)
            self.led_action_adv_combo.setModel(self.action_dir_scale_model if is_scale else self.action_dir_flash_model)
        for col in range(self.led_base_combo.model().columnCount()):
            self.color_table.resizeColumnToContents(col)
            self.action_table.resizeColumnToContents(col)
        self.action_flash_table.resizeColumnsToContents()
        if col == 0:
            self.action_table.setRowHeight(1, self.action_table.rowHeight(0))
            self.action_table.setRowHeight(2, self.action_table.rowHeight(0))
        else:
            small_height = self.action_table.rowHeight(self.action_table.model().rowCount()-1)
            self.action_table.setRowHeight(1, small_height)
            self.action_table.setRowHeight(2, small_height)
        self.color_table.setMinimumWidth(sum([self.color_table.columnWidth(c) for c in range(self.led_base_combo.model().columnCount())]))
        self.action_table.setMinimumWidth(sum([self.action_table.columnWidth(c) for c in range(self.action_full_model.columnCount())]))
        self.current_widget['led'] = led - 1
        self.toggle_colors_edit_btn.setEnabled(self.current_widget.get('toggle', True))

    def led_select(self):
        res = self.led_dialog.exec_(self.led_combo.currentIndex()-1)
        if res:
            self.led_combo.setCurrentIndex(res)

    def dest_update(self, index):
        if not self.current_widget:
            return
        self.current_widget['dest'] = self.dest_combo.currentIndex()+1

    def text_update(self, text):
        self.current_widget['text'] = str(self.text_edit.text().toLatin1())
        self.labelChanged.emit(self.current_widget['widget'], self.text_edit.text())

    def led_action_update(self, index):
        print('changing!!!')
        if index == 0:
            if self.led_action_combo.modelColumn() == 0:
                self.led_action_adv_chk.setEnabled(True)
            else:
                self.led_action_adv_chk.setEnabled(False)
        elif index > 0:
            self.led_action_adv_chk.setEnabled(True)
        else:
            self.led_action_adv_chk.setEnabled(False)

    def led_action_text_update(self, text):
        cols = self.led_action_combo.model().columnCount()
        if cols == 1:
            found = self.led_action_combo.model().findItems('{}'.format(text),  column=0)
            if len(found):
                self.led_action_combo.setCurrentIndex(found[0].row())
        else:
            for c in range(cols):
                found = self.led_action_combo.model().findItems('{}'.format(text),  column=c)
                if len(found):
                    self.led_action_combo.setModelColumn(c)
                    self.led_action_combo.setCurrentIndex(found[0].row())
                    break
        if len(found):
            return
        if self.led_action_combo.currentIndex() >= 0:
            lineEdit = self.led_action_combo.lineEdit()
            pos = lineEdit.cursorPosition()
            self.led_action_combo.setCurrentIndex(-1)
            lineEdit.setText(text)
            lineEdit.setCursorPosition(pos)

    def patch_update(self):
        if not self.current_widget:
            return
        patch = str(self.patch_edit.toPlainText().toLatin1())
        self.current_widget['patch'] = patch
        if len(patch):
            self.patch_edit.valid = patch_validate(patch)
        else:
            self.patch_edit.valid = True
        self.patch_edit.setStyleSheet('color: {}'.format(patch_colors[self.patch_edit.valid][self.enable_chk.isChecked()]))
        if self.enable_chk.isChecked():
            if self.text_edit.text():
                self.labelChanged.emit(self.current_widget['widget'], self.text_edit.text())
            else:
                self.labelChanged.emit(self.current_widget['widget'], patch if len(patch) else True)

    def statusbar_create(self):
        self.statusbar.addWidget(QtWidgets.QLabel('Current mapping:'))
        self.statusbar_empty = QtWidgets.QLabel('(None)')
        self.statusbar_empty.setEnabled(False)
        self.statusbar.addWidget(self.statusbar_empty)
        etype_edit = QtWidgets.QLabel('', self.statusbar)
        etype_edit.setFixedWidth(40)
        event_edit = QtWidgets.QLabel('', self.statusbar)
        event_edit.setFixedWidth(50)
        event_lbl = QtWidgets.QLabel('event', self.statusbar)
        echan_lbl = QtWidgets.QLabel('Channel', self.statusbar)
        echan_edit = QtWidgets.QLabel('', self.statusbar)
        echan_edit.setFixedWidth(12)
        eext_lbl = QtWidgets.QLabel('Range', self.statusbar)
        eext_edit = QtWidgets.QLabel('', self.statusbar)
        eext_edit.setFixedWidth(48)
        emode_lbl = QtWidgets.QLabel('Mode', self.statusbar)
        emode_edit = QtWidgets.QLabel('', self.statusbar)
        emode_edit.setFixedWidth(42)
        self.statusbar_edits = [etype_edit, event_edit, echan_edit, eext_edit, emode_edit]
        self.statusbar_labels = [event_lbl, echan_lbl, eext_lbl, emode_lbl]
        self.statusbar.addWidget(etype_edit)
        self.statusbar.addWidget(event_lbl)
        self.statusbar.addWidget(event_edit)
        self.statusbar.addWidget(echan_lbl)
        self.statusbar.addWidget(echan_edit)
        self.statusbar.addWidget(eext_lbl)
        self.statusbar.addWidget(eext_edit)
        self.statusbar.addWidget(emode_lbl)
        self.statusbar.addWidget(emode_edit)
        for widget in self.statusbar_labels:
            widget.hide()
        for widget in self.statusbar_edits:
            widget.hide()
            widget.setFrameStyle(QtWidgets.QLabel.Sunken)
            widget.setFrameShape(QtWidgets.QLabel.Panel)

    def status_update(self, event_data):
        if not event_data:
            for widget in self.statusbar_labels+self.statusbar_edits:
                widget.hide()
            self.statusbar_empty.show()
            return
        self.statusbar_empty.hide()
        chan, event_type, data1, ext, mode = event_data
        if ext == True:
            ext = '0-127'
        else:
            ext = '{}-{}'.format(ext[0], ext[1])
        data1 = '{} ({})'.format(data1, md.util.note_name(data1))
        event_data = event_type, data1, chan, ext, mode
        for widget in self.statusbar_labels:
            widget.show()
        for i, widget in enumerate(self.statusbar_edits):
            widget.show()
            widget.setText(str(event_data[i]))

    def get_led_basevalue(self, led=None):
        if led is None:
            led = self.led_combo.currentIndex() - 1
        led_type = get_led_type(led)
        if led_type == FullColors:
            led_basevalue_item = self.colormap_full_model.item(self.led_base_combo.currentIndex(), self.led_base_combo.modelColumn())
            led_basevalue = self.colormap_full_model.data(self.colormap_full_model.indexFromItem(led_basevalue_item), LedRole).toPyObject()
        elif led_type == DevColors:
            led_basevalue_item = self.colormap_dev_model.item(self.led_base_combo.currentIndex())
            led_basevalue = self.colormap_dev_model.data(self.colormap_dev_model.indexFromItem(led_basevalue_item), LedRole).toPyObject()
        else:
            led_basevalue_item = self.colormap_dir_model.item(self.led_base_combo.currentIndex())
            led_basevalue = self.colormap_dir_model.data(self.colormap_dir_model.indexFromItem(led_basevalue_item), LedRole).toPyObject()
        if self.led_base_flash_chk.isChecked():
            if led_type == FullColors:
                led_baseflash_item = self.colormap_flash_model.item(self.led_flash_combo.currentIndex(), self.led_flash_combo.modelColumn())
                led_baseflash = self.colormap_flash_model.data(self.colormap_flash_model.indexFromItem(led_baseflash_item), LedRole).toPyObject()
            elif led_type == DevColors:
                led_baseflash_item = self.colormap_dev_flash_model.item(self.led_flash_combo.currentIndex(), self.led_flash_combo.modelColumn())
                led_baseflash = self.colormap_dev_flash_model.data(self.colormap_dev_flash_model.indexFromItem(led_baseflash_item), LedRole).toPyObject()
            else:
                led_baseflash_item = self.colormap_dir_flash_model.item(self.led_flash_combo.currentIndex(), self.led_flash_combo.modelColumn())
                led_baseflash = self.colormap_dir_flash_model.data(self.colormap_dir_flash_model.indexFromItem(led_baseflash_item), LedRole).toPyObject()
            led_basevalue += (led_baseflash+1) << 6
        return led_basevalue

    def widget_save(self, template=None):
        if not self.current_widget:
            return
        if template is None:
            template = self.main.template
        pre_save = copy(self.current_widget)
        widget = self.current_widget.get('widget')
        enabled = self.current_widget.get('enabled', True)
#        dest = self.current_widget.get('dest', 1)
        text = self.current_widget.get('text', '')
        if self.chan_spin.value() > 0:
            self.current_widget['chan'] = self.chan_spin.value()
        else:
            try:
                self.current_widget.pop('chan')
            except:
                pass
        convert = self.convert_group.checkedButton().id
        if self.convert_chk.isChecked():
            self.current_widget['convert'] = True
        else:
            self.current_widget['convert'] = False
        self.current_widget['convert_type'] = convert
        if self.convert_ctrl_radio.isChecked():
            self.current_widget['convert_values'] = self.force_ctrl_spin.value()
        elif self.convert_sysex_radio.isChecked():
            self.current_widget['convert_values'] = (' '.join([str(self.sysex_model.item(i).text()) for i in range(self.sysex_model.rowCount())]), self.force_sysex_spin.value())
        else:
            if self.force_note_change_radio.isChecked():
                self.current_widget['convert_values'] = (None, self.force_vel_spin.value())
            else:
                if self.force_note_combo.currentIndex() == 0:
                    note = None
                else:
                    note = self.force_note_combo.currentIndex()-1
                self.current_widget['convert_values'] = (note, self.force_vel_spin.value())

        patch = self.current_widget.get('patch')
        if text is not None:
            text = text.strip()
            self.current_widget['text'] = text
        else:
            text = ''
        if len(text):
            pass
        elif patch:
            text = patch
        else:
            text = True
        self.labelChanged.emit(widget, text if enabled else False)
        led_index = self.led_combo.currentIndex()
        if led_index > 0:
            led_item = self.ledlist_model.item(led_index)
            if led_item.led == widget.siblingLed:
                self.current_widget['led'] = True
#            led_type = get_led_type(led_index-1)
#            if led_type == FullColors:
#                led_basevalue_item = self.colormap_full_model.item(self.led_base_combo.currentIndex(), self.led_base_combo.modelColumn())
#                led_basevalue = self.colormap_full_model.data(self.colormap_full_model.indexFromItem(led_basevalue_item), LedRole).toPyObject()
#            elif led_type == DevColors:
#                led_basevalue_item = self.colormap_dev_model.item(self.led_base_combo.currentIndex())
#                led_basevalue = self.colormap_dev_model.data(self.colormap_dev_model.indexFromItem(led_basevalue_item), LedRole).toPyObject()
#            else:
#                led_basevalue_item = self.colormap_dir_model.item(self.led_base_combo.currentIndex())
#                led_basevalue = self.colormap_dir_model.data(self.colormap_dir_model.indexFromItem(led_basevalue_item), LedRole).toPyObject()
#            if self.led_base_flash_chk.isChecked():
#                if led_type == FullColors:
#                    led_baseflash_item = self.colormap_flash_model.item(self.led_flash_combo.currentIndex(), self.led_flash_combo.modelColumn())
#                    led_baseflash = self.colormap_flash_model.data(self.colormap_flash_model.indexFromItem(led_baseflash_item), LedRole).toPyObject()
#                elif led_type == DevColors:
#                    led_baseflash_item = self.colormap_dev_flash_model.item(self.led_flash_combo.currentIndex(), self.led_flash_combo.modelColumn())
#                    led_baseflash = self.colormap_dev_flash_model.data(self.colormap_dev_flash_model.indexFromItem(led_baseflash_item), LedRole).toPyObject()
#                else:
#                    led_baseflash_item = self.colormap_dir_flash_model.item(self.led_flash_combo.currentIndex(), self.led_flash_combo.modelColumn())
#                    led_baseflash = self.colormap_dir_flash_model.data(self.colormap_dir_flash_model.indexFromItem(led_baseflash_item), LedRole).toPyObject()
#                led_basevalue += (led_baseflash+1) << 6
            led_basevalue = self.get_led_basevalue(led_index-1)
            if led_basevalue == 0:
                self.current_widget['led_basevalue'] = Disabled
            elif led_item.ledSet == led_basevalue:
                self.current_widget['led_basevalue'] = Enabled
            else:
                self.current_widget['led_basevalue'] = led_basevalue
            led_action = str(self.led_action_combo.currentText())
            if led_action in ['Pass', 'Ignore', 'Toggle']:
                led_action = eval(led_action)
                if led_action == Pass and not isinstance(widget, QtWidgets.QPushButton) and self.led_action_adv_chk.isChecked():
                    self.current_widget['led_scale'] = self.led_action_adv_combo.currentIndex()
                    #TODO: completa con toggle?
            else:
                action_index = self.led_action_combo.currentIndex()
                if action_index >= 0:
                    led_action_item = self.action_full_model.item(action_index, self.led_action_combo.modelColumn())
                    led_action = self.action_full_model.data(self.action_full_model.indexFromItem(led_action_item), LedRole).toPyObject()
                else:
                    try:
                        led_action = int(led_action, 0)
                        if 0 <= led_action < 1024:
                            led_action = Pass
                    except:
                        led_action = Pass
            self.current_widget['led_action'] = led_action

        tooltip = self.main.widget_tooltip(widget, self.current_widget)
        widget.setToolTip(tooltip)
        toggle_model = self.current_widget.get('toggle_model')
        if toggle_model:
            self.current_widget['toggle_values'] = tuple([int(toggle_model.item(i).text()) for i in range(toggle_model.rowCount())])
        vrange = self.current_widget.get('range')
        if vrange:
            range_start = self.range_min_spin.value()
            range_end = self.range_max_spin.value()
            range_type = self.range_combo.currentIndex()
            self.current_widget['range_values'] = range_start, range_end, range_type

        self.main.conf_dict[template][widget] = self.current_widget
        self.widgetSaved.emit(template)
        post_save = copy(self.current_widget)
        #TODO: this is temporary, we should find a better way to track data changes
        if post_save.get('led_basevalue') == Enabled:
            post_save.pop('led_basevalue')
        if post_save.get('led_action') == Pass:
            post_save.pop('led_action')
        if isinstance(post_save.get('led'), bool) and post_save.get('led') == True:
            post_save['led'] = post_save['widget'].siblingLed
        if post_save.get('convert') == False:
            post_save.pop('convert')
            post_save.pop('convert_type')
            post_save.pop('convert_values')
        if pre_save != post_save:
            self.main.dataChanged.emit()

    def widget_change(self, widget, force=False):
        self.enable_chk.setEnabled(True)
        #save previous widget
        if self.current_widget:
            if not force:
                if self.current_widget['widget'] == widget:
                    return
                self.widget_save()

        if not self.isVisible():
            return
        #Prepare editor window
        self.status_update(self.main.map_dict[self.main.template].get(widget))
        self.base_group.setTitle('Base configuration: {}'.format(widget.readable))
        led_index = self.led_combo.currentIndex()
        led_item = self.ledlist_model.item(led_index, 0)
        setBold(led_item, False)
        if widget.siblingLed is not None:
            setBold(self.ledlist_model.item(widget.siblingLed+1))
        else:
            setBold(self.ledlist_model.item(0))
        widget_dict = self.main.conf_dict[self.main.template][widget]
        if not isinstance(widget, QtWidgets.QPushButton):
            self.led_action_adv_chk.setText('Scale')
            self.toggle_item.setEnabled(False)
        else:
            self.led_action_adv_chk.setText('Flash')
            self.toggle_item.setEnabled(True)
        if widget_dict == None:
            self.current_widget = {'widget': widget, 'enabled': False}
            self.enable_chk.setChecked(False)
            self.dest_combo.setCurrentIndex(0)
            self.patch_edit.setPlainText('')
            siblingLed = widget.siblingLed
            if siblingLed is not None:
                self.led_combo.setCurrentIndex(siblingLed+1 if siblingLed is not None else 0)
                if siblingLed < 40:
                    self.led_base_combo.setModelColumn(3)
                    self.led_base_combo.setCurrentIndex(0)
                    self.led_action_combo.setModelColumn(0)
                    self.led_action_combo.setCurrentIndex(0)
                else:
                    self.led_base_combo.setModelColumn(0)
                    self.led_base_combo.setCurrentIndex(1)
                    self.led_action_combo.setModelColumn(0)
                    self.led_action_combo.setCurrentIndex(1)
            #other values stuff to reset
            self.toggle_chk.setChecked(False)
            toggle_model = QtGui.QStandardItemModel()
            self.toggle_listview.setModel(toggle_model)
            self.range_chk.setChecked(False)
            self.convert_chk.setChecked(False)
            self.convert_ctrl_radio.setChecked(True)
            self.text_edit.setText('')
            self.labelChanged.emit(widget, False)
            
            self.enable_chk.setFocus()
            return

        widget_dict['widget'] = widget
        enabled = widget_dict.get('enabled', True)
        self.current_widget = widget_dict
        if enabled and self.enable_chk.isChecked():
                self.tool_group.setEnabled(True)
        self.enable_chk.setChecked(enabled)

        #Destination port
        dest = widget_dict.get('dest', 1)-1
        self.dest_combo.blockSignals(True)
        if dest == None:
            self.dest_combo.setCurrentIndex(0)
        else:
            if dest >= self.output_model.rowCount():
                dest = self.output_model.rowCount()-1
            self.dest_combo.setCurrentIndex(dest)
        self.dest_combo.blockSignals(False)

        #Text
        text = widget_dict.get('text', '')
        self.text_edit.setText(text)

        #Destination channel
        chan = widget_dict.get('chan')
        if chan == None:
            self.chan_spin.setValue(0)
        else:
            self.chan_spin.setValue(chan)

        #Convert event type
        convert = widget_dict.get('convert', False)
        if isinstance(convert, bool):
            convert_type = widget_dict.get('convert_type', ToCtrl)
        else:
            convert_type = convert
        if convert == False:
            self.convert_ctrl_radio.setChecked(True)
            self.convert_chk.setChecked(False)
        else:
            self.convert_chk.setChecked(True)
        if convert_type == ToCtrl:
            self.convert_ctrl_radio.setChecked(True)
            self.force_ctrl_spin.setValue(widget_dict.get('convert_values', 0))
            self.force_note_change_radio.setChecked(True)
            self.force_note_combo.setCurrentIndex(0)
            self.force_vel_spin.setValue(127)
        elif convert_type == ToSysEx:
            self.convert_sysex_radio.setChecked(True)
            sysex, sysex_id = widget_dict.get('convert_values', ('F0 00 F7', 1))
            sysex = [int(x, 16) for x in sysex.split()]
            self.sysex_create(sysex)
            self.force_sysex_spin.setMaximum(len(sysex)-2)
            self.force_sysex_spin.setValue(sysex_id)
        else:
            self.convert_note_radio.setChecked(True)
            convert_note, convert_vel = widget_dict.get('convert_values', (None, 0))
            if convert_note is None:
                self.force_note_change_radio.setChecked(True)
                self.force_note_combo.setCurrentIndex(0)
            else:
                self.force_note_combo.setCurrentIndex(convert_note+1)
            self.force_vel_spin.setValue(convert_vel)
            self.force_ctrl_spin.setValue(0)

        #Patch
        patch = widget_dict.get('patch')
        if patch:
#            self.patch_edit.setStyleSheet('color: black')
            self.patch_edit.setPlainText(str(patch))
        elif enabled:
            self.patch_edit.blockSignals(True)
            self.patch_edit.setStyleSheet('color: gray')
            self.patch_edit.setPlainText('Pass()')
            self.patch_edit.valid = True
            self.patch_edit.blockSignals(False)

        #LED
        led = widget_dict.get('led', True)
        self.led_combo.blockSignals(True)
        if led == None or (isinstance(led, bool) and led == False):
            self.led_combo.setCurrentIndex(0)
            led = None
        #TODO: maybe we can use Enabled and Disabled?
        elif isinstance(led, bool) and led == True:
            if widget.siblingLed is not None:
                led = widget.siblingLed
                self.led_combo.setCurrentIndex(led+1)
            else:
                led = None
                self.led_combo.setCurrentIndex(0)
#            self.led_combo.setCurrentIndex(widget.siblingLed+1 if widget.siblingLed is not None else 0)
        else:
            self.led_combo.setCurrentIndex(led+1)
        self.led_combo.blockSignals(False)
        #we block signals, just to be sure to emit one and one only
#        self.led_combo.currentIndexChanged.emit(self.led_combo.currentIndex())
        self.led_combo_update(self.led_combo.currentIndex())

        led_basevalue = widget_dict.get('led_basevalue', Enabled)
        led_baseflash = None
        cols = self.led_base_combo.model().columnCount()
        if led_basevalue in [0, None, Disabled]:
            self.led_base_combo.setModelColumn(0)
            self.led_base_combo.setCurrentIndex(0)
        else:
            if led_basevalue == Enabled:
                if cols == 1:
                    self.led_base_combo.setModelColumn(0)
                    self.led_base_combo.setCurrentIndex(1)
                else:
                    self.led_base_combo.setModelColumn(3)
                    self.led_base_combo.setCurrentIndex(0)
            else:
                if led_basevalue > 63:
                    led_baseflash = (led_basevalue >> 6) - 1
                    led_basevalue &= 63
                if cols == 1:
                    index = findIndex(self.led_base_combo.model(), led_basevalue, LedRole)
                    if index is not None:
                        self.led_base_combo.setCurrentIndex(index.row())
                    else:
                        self.led_base_combo.setCurrentIndex(1)
                else:
                    column = led_basevalue >> 4
                    row = led_basevalue & 3
                    self.led_base_combo.setModelColumn(column)
                    self.led_base_combo.setCurrentIndex(row)
        if led_baseflash is not None:
            self.led_base_flash_chk.setChecked(True)
            if cols == 1:
                if index is not None:
                    self.led_flash_combo.setCurrentIndex(index.row())
                else:
                    self.led_flash_combo.setCurrentIndex(0)
            else:
                column = led_baseflash >> 4
                row = led_baseflash & 3
                self.led_flash_combo.setModelColumn(column)
                self.led_flash_combo.setCurrentIndex(row)
        else:
            self.led_base_flash_chk.setChecked(False)
            self.led_flash_combo.setModelColumn(0)
            self.led_flash_combo.setCurrentIndex(0)

        #led action
        led_action = widget_dict.get('led_action', Pass)
        led_type = get_led_type(led)
        led_scale = widget_dict.get('led_scale', None)
        if led_type is not None:
            if led_scale is None:
                led_scale = led_scale_types_simple[led_type]
            elif isinstance(led_scale, int):
                led_scale = led_scale_types_full[led_type][led_scale]
        if led_action == Pass:
            self.led_action_combo.setModelColumn(0)
            self.led_action_combo.setCurrentIndex(0)
            if isinstance(led_scale, int):
                self.led_action_adv_combo.setCurrentIndex(led_scale)
                self.led_action_adv_chk.setChecked(True)
            elif isinstance(led_scale, list):
                self.led_action_adv_chk.setChecked(True)
            elif led_scale is None:
                self.led_action_adv_chk.setChecked(False)
        elif led_action == Ignore:
            if cols == 1:
                self.led_action_combo.setCurrentIndex(1)
            else:
                self.led_action_combo.setModelColumn(1)
                self.led_action_combo.setCurrentIndex(0)
        elif led_action == Toggle:
            if cols == 1:
                self.led_action_combo.setCurrentIndex(2)
            else:
                self.led_action_combo.setModelColumn(2)
                self.led_action_combo.setCurrentIndex(0)
        elif isinstance(led_action, int):
            if cols == 1:
                found = self.led_action_combo.model().findItems('{}'.format(hex(led_action)),  column=0)
                if len(found):
                    self.led_action_combo.setCurrentIndex(found[0].row())
                else:
                    self.led_action_combo.lineEdit().setText(led_action)
            else:
                is_found = False
                for c in range(cols):
                    found = self.led_action_combo.model().findItems('{}'.format(hex(led_action)),  column=c)
                    if len(found):
                        self.led_action_combo.setModelColumn(c)
                        self.led_action_combo.setCurrentIndex(found[0].row())
                        is_found = True
                        break
                if not is_found:
                    self.led_action_combo.setModelColumn(0)
                    self.led_action_combo.setCurrentIndex(-1)
                    #TODO: set led value text?
#                    self.led_action_combo.lineEdit().setText(led_action)
        else:
            self.led_action_combo.lineEdit().setText(led_action)

        #Toggle and Range
        vrange = self.current_widget.get('range', False)
        self.range_chk.setChecked(vrange)
        range_start, range_end, range_type = self.current_widget.get('range_values', (0, 127, 0))
        self.range_min_spin.setValue(range_start)
        self.range_max_spin.setValue(range_end)
        self.range_combo.setCurrentIndex(range_type)
        self.range_combo.setEnabled(True if vrange and not isinstance(widget, QtWidgets.QPushButton) else False)
        self.range_scale_lbl.setEnabled(True if vrange and not isinstance(widget, QtWidgets.QPushButton) else False)
        if not isinstance(widget, QtWidgets.QPushButton):
            self.toggle_chk.setChecked(False)
            self.toggle_chk.setEnabled(False)
            toggle_model = QtGui.QStandardItemModel()
        else:
#            self.toggle_chk.setEnabled(True)
            toggle = self.current_widget.get('toggle', False)
            if toggle:
                self.toggle_chk.setChecked(True)
                if vrange:
                    self.current_widget['range'] = False
                    self.range_chk.setChecked(False)
            else:
                self.toggle_chk.setChecked(False)
                self.toggle_listview.setEnabled(False)
            toggle_model = self.current_widget.get('toggle_model')
            if not toggle_model:
                toggle_values = self.current_widget.get('toggle_values')
                toggle_model = QtGui.QStandardItemModel()
                if toggle_values:
                    if len(led_scale) > len(toggle_values):
                        v_len = len(toggle_values)
                        div = len(led_scale)/(v_len-1)
                        led_scale = [led_scale[i*div] for i in range(v_len-1)] + [led_scale[-1]]
                        self.current_widget['led_scale'] = 0
                    else:
                        self.current_widget['led_scale'] = led_scale
                    for i, value in enumerate(toggle_values):
                        item = QtGui.QStandardItem(str(value))
                        item.setFlags(item.flags() ^ QtCore.Qt.ItemIsDropEnabled)
                        if led_type is not None:
                            led_value = led_scale[i]
                            if led_value > 63:
                                led_flash_value = (led_value >> 6) - 1
                                led_value &= 63
                            else:
                                led_flash_value = None
                            if led_type == FullColors:
                                led_pixmap = self.colormap_full_pixmap[(led_value&3, led_value>>4)]
                                if led_flash_value is not None:
                                    led_flash_pixmap = self.colormap_full_pixmap[(led_flash_value&3, led_flash_value>>4)]
                            elif led_type == DevColors:
                                led_pixmap = self.colormap_dev_pixmap[dev_scale.index(led_value)]
                                if led_flash_value is not None:
                                    led_flash_pixmap = self.colormap_dev_pixmap[led_flash_value]
                            else:
                                led_pixmap = self.colormap_dir_pixmap[dir_scale.index(led_value)]
                                if led_flash_value is not None:
                                    led_flash_pixmap = self.colormap_dir_pixmap[led_flash_value]
                            item.setData(led_value, LedRole)
                            item.setData(led_pixmap, LedPixmapRole)
                            if led_flash_value is not None:
                                item.setData(led_flash_value, LedFlashRole)
                                item.setData(led_flash_pixmap, LedFlashPixmapRole)
                        toggle_model.appendRow(item)
                    self.current_widget['toggle'] = self.current_widget.get('toggle', True)
                    self.current_widget['toggle_model'] = toggle_model
        self.toggle_listview.setModel(toggle_model)

        if force:
            if text:
                self.labelChanged.emit(self.current_widget['widget'], text)
            elif patch:
                self.labelChanged.emit(self.current_widget['widget'], patch)
            else:
                self.labelChanged.emit(self.current_widget['widget'], True)

        self.toggle_start()


    def patch_edit_focusIn(self, event):
        QtGui.QPlainTextEdit.focusInEvent(self.patch_edit, event)
        patch = self.current_widget.get('patch')
        if not patch:
            self.patch_edit.setPlainText('')

    def patch_edit_focusOut(self, event):
        QtGui.QPlainTextEdit.focusOutEvent(self.patch_edit, event)
        patch = self.current_widget.get('patch')
        if not patch:
            self.patch_edit.blockSignals(True)
            self.patch_edit.setStyleSheet('color: gray')
            self.patch_edit.setPlainText('Pass')
            self.patch_edit.blockSignals(False)

    def piano_show(self):
        key = self.force_note_combo.currentIndex()
        res = self.piano.exec_(key-1 if key > 0 else None)
        if res > 0:
            self.force_note_combo.setCurrentIndex(res)



