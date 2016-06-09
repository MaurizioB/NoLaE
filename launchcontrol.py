#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import sys, argparse
import mididings as md
import string
from collections import namedtuple, OrderedDict
from copy import copy
from PyQt4 import QtCore, QtGui, uic
import icons

backend = 'alsa'
default_map = 'default.nlm'
led_scale = [48, 49, 50, 51, 35, 19, 2, 3]
dev_scale = [0x00, 0x10, 0x11, 0x22, 0x23, 0x20, 0x33]
dir_scale = [0x00, 0x01, 0x21, 0x22, 0x32, 0x33]
led_fullscale = [x for t in [[a for r in range(16)] for a in led_scale] for x in t]
row_heights = {0: 80, 1: 80, 2: 80, 3: 160, 4: 40, 5: 40}
str_allowed = set(string.ascii_letters+string.digits+'.'+' ')

#TODO Split is missing, update function with regex
md_replace = ('Ctrl', 'Port', 'Channel', 'Velocity', 
           'Note', 'Pitchbend', 'Aftertouch', 'Program', 'SysEx', 'Generator', 
           'extra.Harmonize', 'LimitPolyphony', 'MakeMonophonic', 'LatchNotes', 'Panic'
           'Discard', 'Pass', 'Sanitize', 'Print', 
           'EVENT'
           )

patch_colors = (('darkred', 'red'), ('gray', 'black'))

class Const(object):
    def __init__(self):
        self.name = None
    def get_name(self):
        return [k for k, v in globals().items() if v is self][0]
    def __str__(self):
        if not self.name:
            self.name = self.get_name()
        return self.name.title()
    def __repr__(self):
        if not self.name:
            self.name = self.get_name()
        return self.name

Pass, Ignore, Value, Push, Toggle, Widget, Mode, Ext = (Const() for i in range(8))
Disabled, Enabled, Triggered = (Const() for i in range(3))
GroupMode, DestMode = (Const() for i in range(2))
MAPCTRL = 0
Widget = namedtuple('Widget', 'inst ext mode')
TPatch = namedtuple('TPatch', 'label patch input')
TPatch.__new__.__defaults__ = (None, ) * len(TPatch._fields)
TPatch.__new__.__defaults__ = (None, )

def str_check(text):
    if isinstance(text, QtCore.QString):
        text = str(text.toLatin1())
    if set(text) <= str_allowed:
        return text
    new_text = ''
    for l in text:
        if l in str_allowed:
            new_text += l
    return new_text

def set_led(template=0, *led_list):
    sysex_string = [0xF0, 0x00, 0x20, 0x29, 0x02, 0x11, 0x78, template]
    sysex_string.extend([x for t in led_list for x in t])
    sysex_string.append(0xf7)
    newevent = md.event.SysExEvent(md.engine.out_ports()[-1], sysex_string)
    md.engine.output_event(newevent)

def template_str(template):
    if template >= 8:
        return ('Factory', template-7)
    else:
        return ('User', template+1)

def elide_str(label, text):
    if not isinstance(text, str):
        text = str(text)
    metrics = QtGui.QFontMetrics(label.font())
    elided = metrics.elidedText(text, QtCore.Qt.ElideRight, label.width())
    return elided

def setBold(item, bold=True):
    font = item.font()
    font.setBold(bold)
    item.setFont(font)

def rgb_from_hex(value, mode=None):
    if not isinstance(value, int):
        return value
    if not mode:
        green, red = divmod(value, 16)
        return '#{:02x}{:02x}00'.format(red*85, green*85)
    elif mode == 'dev':
        try:
            color = dev_scale.index(value)
        except:
            green, red = divmod(value, 16)
            return '#{:02x}{:02x}00'.format(red*85, green*85)
        red = color*42
        green = color*38
        return '#{:02x}{:02x}00'.format(red, green)
    else:
        try:
            color = dir_scale.index(value)
        except:
            green, red = divmod(value, 16)
            return '#{:02x}{:02x}00'.format(red*85, green*85)
        red = color*51
        return '#{:02x}0000'.format(red)

def process_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-c', '--config')

    mapfile_group = parser.add_mutually_exclusive_group()
    mapfile_group.add_argument('-m', '--mapfile', dest='mapfile')
    mapfile_group.add_argument('-n', '--nomap', action='store_false', dest='mapfile')

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('-M', '--mapping', action='store_const', dest='mode', const='mapping')
    mode_group.add_argument('-E', '--editor', action='store_const', dest='mode', const='editor')

    parser.set_defaults(mapfile=default_map, mode='control')
    return parser.parse_args()


class SignalClass(object):
    def __init__(self, template, widget, ext=True, mode=Value, dest=Pass, patch=md.Pass(), text=None, led=True, led_basevalue=Enabled, led_action=Pass):
        self.widget = widget
        self.inst = widget
        self.template = template
        self.id = widget.id
        self.ext = ext if isinstance(ext, tuple) else (0, 127)
        self.mode = mode
        self.value = self.ext[0]
        self.dest = dest
        self.patch = patch
        self.label = widget.siblingLabel
        self.basetext = text if text else ''
        self.text = self.basetext.format(self.value)
        if led is not False:
            if widget.siblingLed is not None:
                self.led = widget.siblingLed
            else:
                self.led = None
        else:
            self.led = None
        
#        self.led_basevalue = led_basevalue
        if self.led:
            self.led_setup(led_basevalue)
        else:
            self.led_state = self.led_basevalue = 0
        self.led_assign(led_action)

    def __repr__(self):
        return 'Signal({w}, {p}, {l})'.format(w=self.widget.readable, p=self.patch, l=self.led)

    def led_setup(self, basevalue):
        if basevalue == Enabled:
            if self.id < 48:
                basevalue = 0x30
                triggervalue = 3
            elif 48 <= self.id < 52:
                basevalue = 0x10
                triggervalue = 0x33
            else:
                basevalue = 0x01
                triggervalue = 0x33
            self.led_state = self.led_basevalue = basevalue
            self.led_triggervalue = triggervalue
        elif basevalue == Disabled:
            self.led_state = self.led_basevalue = 0
        else:
            self.led_state = self.led_basevalue = basevalue
            self.led_triggervalue = 0x33 if 48 <= self.id < 52 else 3

    def led_pass_action(self, value):
        set_led(self.template, (self.led, led_fullscale[value]))

    def led_push_action(self, value):
        set_led(self.template, (self.led, self.led_triggervalue if value==self.ext[1] else self.led_basevalue))

    def led_ignore_action(self, event):
        pass

    def led_assign(self, action):
        if not self.led:
            self.led_action = self.led_ignore_action
            return
        if action == Pass:
            if isinstance(self.widget, QtGui.QPushButton):
                self.led_action = self.led_push_action
            else:
                self.led_action = self.led_pass_action
        elif isinstance(action, int):
            self.led_triggervalue = action
            if isinstance(self.widget, QtGui.QPushButton):
                self.led_action = self.led_push_action
            else:
                self.led_action = self.led_pass_action
        else:
            self.led_action = self.led_ignore_action

    def trigger(self, value):
#        self.action(event)
        self.led_action(value)


class TemplateClass(object):
    def __init__(self, main, id, name=None):
        self.main = main
        self.id = id
        self.name = name if name else id
        self.out_ports = None
        self.enabled = True
        self.widget_list = []
        self.current_widget = None

    def set_widget_signal(self, signal):
        self.widget_list[signal.id] = signal

    def get_widget(self, id):
        return self.main.widget_order[id]


class Router(QtCore.QThread):
    template_change = QtCore.pyqtSignal(int)
    midi_signal = QtCore.pyqtSignal(object)

    def __init__(self, main, mapping=False):
        QtCore.QThread.__init__(self)
        self.main = main
        self.already_set = False
        self.mapping = mapping
        if self.mapping:
            self.setup = self.setup_mapping
        else:
            self.setup = self.setup_control

    def setup_mapping(self):
        self.config = md.config(
            backend = backend,
            client_name='LCGate',
            in_ports = [
                ('LC_input', 'Launch.*'), 
                        ],
            out_ports=[
                ('LC_output', 'Launch.*'), 
                        ],
            )
        self.already_set = True

    def set_config(self, scenes, out_ports=None):
        self.scenes = scenes
        if out_ports:
            self.out_ports = out_ports
        else:
            self.out_ports = [('Output')]

    def setup_control(self):
        self.config = md.config(
            backend = backend,
            client_name='LCGate',
            in_ports = [
                ('LC_input', 'Launch.*'), 
                        ],
            out_ports = self.out_ports + [('LC_output', 'Launch.*')],
            )
        self.already_set = True

    def run(self):
        if not self.already_set:
            self.setup()
        if self.mapping:
            md.run(md.Call(self.event_mapping))
        else:
            md.run(scenes=self.scenes, control=md.Call(self.event_call))

    def event_mapping(self, event):
        if event.type == md.SYSEX:
            template = event.sysex[-2]
            self.template_change.emit(template)
            return
        elif event.type in [md.CTRL, md.NOTEON, md.NOTEOFF]:
            self.midi_signal.emit(copy(event))

    def event_call(self, event):
        if event.type == md.SYSEX:
            template = event.sysex[-2]
            md.engine.switch_scene(template+1)
            self.template_change.emit(template)
            return
        elif event.type in [md.CTRL, md.NOTEON, md.NOTEOFF]:
            self.midi_signal.emit(copy(event))

    def quit(self):
        md.engine.quit()
        QtCore.QThread.quit(self)

class MyToolTip(QtGui.QWidget):
    def __init__(self, parent, text):
        QtGui.QWidget.__init__(self, parent.parent())
#        self.resize(50, 100)
        self.label = QtGui.QLabel(text, self)
        self.label.setMinimumWidth(60)
        self.label.setMaximumWidth(60)
        self.label.setMinimumHeight(40)
        self.label.setWordWrap(True)
#        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.show()
        center = parent.x()+parent.width()/2
        self.setMinimumWidth(60)
        self.move(center-self.width()/2, parent.y()-10)
        self.setStyleSheet('background-color: rgba(210,210,210,210)')
        self.raise_()


class EditorWin(QtGui.QMainWindow):
    #TODO: forse questo signal andrebbe al main, non qui
    widgetChanged = QtCore.pyqtSignal(object)
    labelChanged = QtCore.pyqtSignal(object, object)

    def __init__(self, parent=None, mode='control'):
        QtGui.QMainWindow.__init__(self, parent)
        self.main = self.parent()
        self.map_dict = self.main.map_dict
        uic.loadUi('patch.ui', self)
        self.patch_edit.textChanged.connect(self.patch_update)
        self.patch = ''
        self.patch_edit.valid = False
        self.widgetChanged.connect(self.widget_change)
        self.patch_edit.focusInEvent = self.patch_edit_focusIn
        self.patch_edit.focusOutEvent = self.patch_edit_focusOut
        self.enable_chk.toggled.connect(self.enable_set)
        self.led_reset_btn.clicked.connect(self.led_reset)
        self.main.outputChanged.connect(self.output_update)
        self.dest_combo.currentIndexChanged.connect(self.dest_update)
        self.led_combo.currentIndexChanged.connect(self.led_combo_update)
        self.text_edit.textEdited.connect(self.text_update)
        self.led_action_combo.lineEdit().textEdited.connect(self.led_action_update)
        self.restore_btn.clicked.connect(self.widget_restore)

        self.current_widget = None
        self.output_update()
        self.models_setup()
        self.base_group.setEnabled(False)
        self.patch_group.setEnabled(False)
        self.patch_templates_menu_create()
        self.patch_toolbtn.setMenu(self.patch_templates)
        self.tool_group.setEnabled = self.tool_group_setEnabled
        #TODO: add setDisable if not selected

    def closeEvent(self, event):
        if self.current_widget:
            self.widget_save()

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
                action = QtGui.QAction(item.label, self)
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
                    action = QtGui.QAction(tpatch.label, self)
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
                    value, res = QtGui.QInputDialog.getInt(self, action.text(), req[-1], min=0, max=req[1])
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
        def pixmap(red=0, green=0):
            pixmap = QtGui.QPixmap(8, 8)
            color = QtGui.QColor()
            color.setRgb(red, green, 0)
            pixmap.fill(color)
            return pixmap
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
        self.colormap_full_pixmap = {(r, g):pixmap(r*85, g*85) for r in range(4) for g in range(4)}
        self.colormap_full_model = QtGui.QStandardItemModel()
        self.led_base_combo.setModel(self.colormap_full_model)
        self.color_table = create_table()
        self.color_table.selectionChanged = self.color_column_check
        self.led_base_combo.setView(self.color_table)
        for row in range(4):
            row_list = []
            for col in range(4):
                item = QtGui.QStandardItem('0x{:02x}'.format(row+col*16))
                item.setIcon(QtGui.QIcon(self.colormap_full_pixmap[row, col]))
#                if row == 0 and col == 3:
#                    font = item.font()
#                    font.setBold(True)
#                    item.setFont(font)
                row_list.append(item)
            self.colormap_full_model.appendRow(row_list)
            self.color_table.resizeColumnToContents(row)
        self.color_table.setMinimumWidth(sum([self.color_table.columnWidth(c) for c in range(self.colormap_full_model.columnCount())]))

        self.colormap_dev_pixmap = [pixmap(r*42, r*38) for r in range(7)]
        self.colormap_dev_model = QtGui.QStandardItemModel()
        for l in range(7):
            led_value = dev_scale[l]
            item = QtGui.QStandardItem('0x{:02x}'.format(led_value))
            item.setIcon(QtGui.QIcon(self.colormap_dev_pixmap[l]))
            self.colormap_dev_model.appendRow(item)
        self.led_base_combo.setSizeAdjustPolicy(self.led_base_combo.AdjustToContents)

        self.colormap_dir_pixmap = [pixmap(r*51) for r in range(6)]
        self.colormap_dir_model = QtGui.QStandardItemModel()
        for l in range(6):
            led_value = dir_scale[l]
            item = QtGui.QStandardItem('0x{:02x}'.format(led_value))
            item.setIcon(QtGui.QIcon(self.colormap_dir_pixmap[l]))
            self.colormap_dir_model.appendRow(item)

        #LED action combo
        self.action_table = create_table()
        self.action_table.selectionChanged = self.action_column_check
        self.led_action_combo.setView(self.action_table)
        self.action_full_model = QtGui.QStandardItemModel()
        self.led_action_combo.setModel(self.action_full_model)
        pass_item = QtGui.QStandardItem('Pass')
        disc_item = QtGui.QStandardItem('Ignore')
        self.action_full_model.appendRow([pass_item, disc_item])
        self.action_table.setSpan(0, 1, 1, 3)
        self.action_table.resizeRowToContents(0)
        for row in range(4):
            self.action_full_model.appendRow([self.colormap_full_model.item(row, col).clone() for col in range(4)])
            self.action_table.resizeColumnToContents(row)
        self.action_table.setMinimumWidth(sum([self.action_table.columnWidth(c) for c in range(self.action_full_model.columnCount())]))
        self.action_dev_model = QtGui.QStandardItemModel()
        self.action_dev_model.appendColumn([pass_item.clone(), disc_item.clone()])
        [self.action_dev_model.appendRow(self.colormap_dev_model.item(l).clone()) for l in range(7)]
        self.action_dir_model = QtGui.QStandardItemModel()
        self.action_dir_model.appendColumn([pass_item.clone(), disc_item.clone()])
        [self.action_dir_model.appendRow(self.colormap_dir_model.item(l).clone()) for l in range(6)]

        #setting default leds:
        setBold(self.colormap_full_model.item(0, 3))
        setBold(self.colormap_dev_model.item(1))
        setBold(self.colormap_dir_model.item(1))
        setBold(self.action_full_model.item(4, 3))
        setBold(self.action_dev_model.item(8))
        setBold(self.action_dir_model.item(7))


    def color_column_check(self, selected, previous):
        index = self.color_table.selectedIndexes()[0]
        self.led_base_combo.setModelColumn(index.column())
        self.led_base_combo.setCurrentIndex(index.row())

    def action_column_check(self, selected, previous):
        index = self.action_table.selectedIndexes()
        if index:
            self.led_action_combo.setModelColumn(index[0].column())
            self.led_action_combo.setCurrentIndex(index[0].row())
        else:
            print 'What\'s wrong with index? {}'.format(index)
            self.led_action_combo.setModelColumn(0)
            self.led_action_combo.setCurrentIndex(0)

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

    def led_reset(self):
        default_led = self.current_widget['widget'].siblingLed
        self.led_combo.setCurrentIndex(default_led+1 if default_led is not None else 0)

    def led_combo_update(self, led):
        if not self.current_widget:
            return
        if led == 0:
            self.led_base_combo.setEnabled(False)
            self.led_action_combo.setEnabled(False)
            if self.current_widget.get('led'):
                if isinstance(self.current_widget['widget'], QtGui.QSlider):
                    self.current_widget.pop('led')
                else:
                    self.current_widget['led'] = False
            return
        self.led_base_combo.setEnabled(True)
        self.led_action_combo.setEnabled(True)
        if led <= 40:
            if self.led_base_combo.model() != self.colormap_full_model:
                self.led_base_combo.setModel(self.colormap_full_model)
                self.led_action_combo.setModel(self.action_full_model)
        elif led <= 44:
            if self.led_base_combo.model() != self.colormap_dev_model:
                self.led_base_combo.setModelColumn(0)
                self.led_base_combo.setModel(self.colormap_dev_model)
                self.led_action_combo.setModelColumn(0)
                self.led_action_combo.setModel(self.action_dev_model)
        else:
            if self.led_base_combo.model() != self.colormap_dir_model:
                self.led_base_combo.setModelColumn(0)
                self.led_base_combo.setModel(self.colormap_dir_model)
                self.led_action_combo.setModelColumn(0)
                self.led_action_combo.setModel(self.action_dir_model)
        for col in range(self.led_base_combo.model().columnCount()):
            self.color_table.resizeColumnToContents(col)
            self.action_table.resizeColumnToContents(col)
        if col == 0:
            self.action_table.setRowHeight(1, self.action_table.rowHeight(0))
        else:
            self.action_table.setRowHeight(1, self.action_table.rowHeight(self.action_table.model().rowCount()-1))
        self.color_table.setMinimumWidth(sum([self.color_table.columnWidth(c) for c in range(self.led_base_combo.model().columnCount())]))
        self.action_table.setMinimumWidth(sum([self.action_table.columnWidth(c) for c in range(self.action_full_model.columnCount())]))
        self.current_widget['led'] = led - 1

    def dest_update(self, index):
        if not self.current_widget:
            return
        self.current_widget['dest'] = self.dest_combo.currentIndex()+1

    def text_update(self, text):
        self.current_widget['text'] = str(self.text_edit.text().toLatin1())
        self.labelChanged.emit(self.current_widget['widget'], self.text_edit.text())

    def led_action_update(self, text):
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
            patch_format = patch
            for rep in md_replace:
                patch_format = patch_format.replace(rep, 'md.'+rep)
            try:
                eval(patch_format)
                self.patch_edit.valid = True
            except:
                self.patch_edit.valid = False
        else:
            self.patch_edit.valid = True
        self.patch_edit.setStyleSheet('color: {}'.format(patch_colors[self.patch_edit.valid][self.enable_chk.isChecked()]))
        if self.enable_chk.isChecked():
            if self.text_edit.text():
                self.labelChanged.emit(self.current_widget['widget'], self.text_edit.text())
            else:
                self.labelChanged.emit(self.current_widget['widget'], patch if len(patch) else True)

    def widget_save(self, template=None):
        if not self.current_widget:
            return
        if not template:
            template = self.main.template
        widget = self.current_widget.get('widget')
        enabled = self.current_widget.get('enabled', True)
        dest = self.current_widget.get('dest', 1)
        text = self.current_widget.get('text', '')
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
#        widget.siblingLabel.setText(elide_str(widget.siblingLabel, text) if enabled else '')
        self.labelChanged.emit(widget, text if enabled else False)
        led_index = self.led_combo.currentIndex()
        if led_index > 0:
            led_item = self.ledlist_model.item(led_index)
            if led_item.led == 0:
                self.current_widget['led'] = False
            elif led_item.led == widget.siblingLed:
                self.current_widget['led'] = True
            led_basevalue = int(str(self.led_base_combo.currentText()), 0)
            if led_basevalue == 0:
                self.current_widget['led_basevalue'] = Disabled
            elif led_item.ledSet == led_basevalue:
                self.current_widget['led_basevalue'] = Enabled
            else:
                self.current_widget['led_basevalue'] = led_basevalue
            led_action = str(self.led_action_combo.currentText())
            if led_action in ['Pass', 'Ignore']:
                led_action = eval(led_action)
            else:
                try:
                    led_action = int(led_action, 0)
                except:
                    pass
            self.current_widget['led_action'] = led_action

        tooltip = self.main.widget_tooltip(widget, self.current_widget)
        widget.setToolTip(tooltip)
        self.main.map_dict[template][widget] = self.current_widget

    def widget_change(self, widget):
        self.enable_chk.setEnabled(True)
        self.tool_group.setEnabled(True)
        #save previous widget
        if self.current_widget:
#            print self.current_widget
            if self.current_widget['widget'] == widget:
                return
            self.widget_save()

        if not self.isVisible():
            return
        #Prepare editor window
        self.base_group.setTitle('Base configuration: {}'.format(widget.readable))
        led_index = self.led_combo.currentIndex()
        led_item = self.ledlist_model.item(led_index, 0)
        setBold(led_item, False)
        if widget.siblingLed is not None:
            setBold(self.ledlist_model.item(widget.siblingLed+1))
        else:
            setBold(self.ledlist_model.item(0))
        widget_dict = self.main.map_dict[self.main.template][widget]
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
            return

        widget_dict['widget'] = widget
        enabled = widget_dict.get('enabled', True)
        self.current_widget = widget_dict
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
        #TODO: maybe we can use Enabled and Disabled?
        elif isinstance(led, bool) and led == True:
            self.led_combo.setCurrentIndex(widget.siblingLed+1 if widget.siblingLed is not None else 0)
        else:
            self.led_combo.setCurrentIndex(led+1)
        self.led_combo.blockSignals(False)
        #we block signals, just to be sure to emit one and one only
#        self.led_combo.currentIndexChanged.emit(self.led_combo.currentIndex())
        self.led_combo_update(self.led_combo.currentIndex())

        led_basevalue = widget_dict.get('led_basevalue', Enabled)
        cols = self.led_base_combo.model().columnCount()
        if led_basevalue in [None, Disabled]:
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
                if cols == 1:
#                    self.led_base_combo.setModelColumn(0)
                    found = self.led_base_combo.model().findItems('0x{:02x}'.format(led_basevalue),  column=0)
                    if len(found):
                        self.led_base_combo.setCurrentIndex(found[0].row())
                    else:
                        self.led_base_combo.setCurrentIndex(1)
                else:
                    is_found = False
                    for c in range(cols):
                        found = self.led_base_combo.model().findItems('0x{:02x}'.format(led_basevalue),  column=c)
                        if len(found):
                            self.led_base_combo.setModelColumn(c)
                            self.led_base_combo.setCurrentIndex(found[0].row())
                            is_found = True
                            break
                    if not is_found:
                        self.led_base_combo.setModelColumn(3)
                        self.led_base_combo.setCurrentIndex(0)
        led_action = widget_dict.get('led_action', Pass)
        if led_action == Pass:
            self.led_action_combo.setModelColumn(0)
            self.led_action_combo.setCurrentIndex(0)
        elif led_action == Ignore:
            if cols == 1:
#                self.led_action_combo.setModelColumn(0)
                self.led_action_combo.setCurrentIndex(1)
            else:
                self.led_action_combo.setModelColumn(1)
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
                    self.led_action_combo.lineEdit().setText(led_action)
        else:
            self.led_action_combo.lineEdit().setText(led_action)


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


class OutputWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi('output_widget.ui', self)
        self.main = self.parent()


class Win(QtGui.QMainWindow):
    outputChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None, mode='control', map_file=None, config=None):
        QtGui.QMainWindow.__init__(self, parent)
        uic.loadUi('launchcontrol.ui', self)
        self.mapping = True if mode=='mapping' else False
        self.map_dict = {}
        for t in range(16):
            self.map_dict[t] = {}
        self.config = config
        self.template = 0
        self.router = Router(self, self.mapping)
        self.widget_setup()
        if mode != 'editor':
            if self.mapping:
                self.map_file = map_file
                self.setWindowTitle('{} - mapping mode'.format(self.windowTitle()))
                self.router.midi_signal.connect(self.midi_map)
                self.showmap_btn.clicked.connect(self.show_map)
                self.operation_start = self.mapping_start
            else:
                self.scenes, out_ports = self.routing_setup()
                self.router.set_config(self.scenes, out_ports=out_ports)
                self.router.midi_signal.connect(self.midi_action)
                self.operation_start = self.routing_start
            self.router.start()
            self.router.template_change.connect(self.template_remote_set)
            while not md.engine.active():
                pass
            self.startup()
#            self.template_connect(mode)
        else:
            self.operation_start = self.editor_start
        self.template_connect(mode)

        self.operation_start()

    def startupbox_resizeEvent(self, event):
        QtGui.QWidget.resizeEvent(self.startup_box, event)
        self.startup_box.setFixedSize(self.width(), self.height())

    def startupbox_setText(self, template=0):
        self.startup_box.setText('<p align=\'center\'>Preparing LaunchPad, please wait...<br>Preparing template {} of 16</p>'.format(template+1))

    def startup(self):
        self.startup_box = QtGui.QMessageBox(self)
        self.startupbox_setText()
        self.startup_box.setWindowFlags(QtCore.Qt.Widget)
        palette = self.startup_box.palette()
        palette.setColor(self.startup_box.backgroundRole(), QtGui.QColor(200, 200, 200, 200))
        self.startup_box.setAutoFillBackground(True)
        self.startup_box.setPalette(palette)
        self.startup_box.setStandardButtons(QtGui.QMessageBox.NoButton)
        self.startup_box.resizeEvent = self.startupbox_resizeEvent
        self.startup_box.open()

    def widget_setup(self):
        self.widget_order = []
        for i in range(24):
            widget = eval('self.knob_{:02d}'.format(i))
            widget.siblingLabel = eval('self.label_knob_{:02d}'.format(i))
            widget.siblingLed = i
            widget.id = i
            if i < 8:
                widget.readable = 'Send A knob {}'.format(i+1)
                widget.grid_row = 0
                widget.grid_col = i
            elif i < 16:
                widget.readable = 'Send B knob {}'.format(i-7)
                widget.grid_row = 1
                widget.grid_col = i-8
            else:
                widget.readable = 'Pan/Dev knob {}'.format(i-15)
                widget.grid_row = 2
                widget.grid_col = i-16
            widget.ledSet = 0x30
            widget.ledTrigger = 3
            self.widget_order.append(widget)
        for i in range(8):
            widget = eval('self.fader_{:02d}'.format(i))
            widget.siblingLabel = eval('self.label_fader_{:02d}'.format(i))
            widget.siblingLed = None
            widget.id = i+24
            widget.readable = 'Fader {}'.format(i+1)
            widget.grid_row = 3
            widget.grid_col = i
            widget.ledSet = 0x30
            widget.ledTrigger = 3
            self.widget_order.append(widget)
        for i in range(24):
            widget = eval('self.btn_{:02d}'.format(i))
            widget.siblingLabel = eval('self.btn_{:02d}'.format(i))
            widget.siblingLed = i+24
            widget.id = i+32
            if i < 16:
                if i < 8:
                    widget.readable = '{} button {}'.format('Focus', i+1)
                    widget.grid_row = 4
                    widget.grid_col = i
                else:
                    widget.readable = '{} button {}'.format('Control', i-7)
                    widget.grid_row = 5
                    widget.grid_col = i-8
                widget.ledSet = 0x30
                widget.ledTrigger = 3
            elif 16 <= i < 20:
                widget.ledSet = 0x10
                widget.ledTrigger = 0x30
            else:
                widget.ledSet = 1
                widget.ledTrigger = 3
            self.widget_order.append(widget)
        self.btn_16.readable = 'Device'
        self.btn_17.readable = 'Mute'
        self.btn_18.readable = 'Solo'
        self.btn_19.readable = 'Rec'
        self.btn_20.readable = 'Up'
        self.btn_21.readable = 'Down'
        self.btn_22.readable = 'Left'
        self.btn_23.readable = 'Right'

    def mapping_start(self):
        self.map_group.setVisible(True)
        self.template_manual_update(True)
#        if not self.mapping:
#            return

        self.savemap_btn.clicked.connect(self.save_map)
        self.automap_enabled = False
        self.singlemap_enabled = False
        self.map_dialog = QtGui.QMessageBox(self)
        self.map_dialog.setText('Mapping')
#        self.map_dialog.setWindowTitle('prot')
        self.map_dialog.setModal(True)
        self.map_dialog.setStandardButtons(QtGui.QMessageBox.Abort)
        self.map_dialog.finished.connect(self.single_map_stop)
        self.map_confirm = QtGui.QMessageBox(self)
        self.map_confirm.setWindowTitle('Event conflict!')
        self.map_confirm.setModal(True)
        self.map_confirm.setStandardButtons(QtGui.QMessageBox.Ok|QtGui.QMessageBox.Cancel)
        self.map_ext_dialog = QtGui.QDialog(self)
        self.map_ext_dialog.setWindowTitle('Set range')
        self.map_ext_dialog.setModal(True)
        grid = QtGui.QGridLayout(self.map_ext_dialog)
        self.map_ext_dialog.caption = QtGui.QLabel(self.map_ext_dialog)
        grid.addWidget(self.map_ext_dialog.caption, 0, 0, 1, 2)
        self.map_ext_dialog.min_lbl = QtGui.QLabel('Minimum', self.map_ext_dialog)
        grid.addWidget(self.map_ext_dialog.min_lbl, 1, 0)
        self.map_ext_dialog.min_spin = QtGui.QSpinBox(self.map_ext_dialog)
        self.map_ext_dialog.min_spin.setMinimum(0)
        self.map_ext_dialog.min_spin.setMaximum(127)
        grid.addWidget(self.map_ext_dialog.min_spin, 1, 1)
        self.map_ext_dialog.max_lbl = QtGui.QLabel('Maximum', self.map_ext_dialog)
        grid.addWidget(self.map_ext_dialog.max_lbl, 2, 0)
        self.map_ext_dialog.max_spin = QtGui.QSpinBox(self.map_ext_dialog)
        self.map_ext_dialog.max_spin.setMinimum(0)
        self.map_ext_dialog.max_spin.setMaximum(127)
        self.map_ext_dialog.max_spin.setValue(127)
        grid.addWidget(self.map_ext_dialog.max_spin, 2, 1)

        invert_btn = QtGui.QPushButton('Invert values', self.map_ext_dialog)
        def invertValues():
            min_value = self.map_ext_dialog.min_spin.value()
            max_value = self.map_ext_dialog.max_spin.value()
            self.map_ext_dialog.min_spin.setValue(max_value)
            self.map_ext_dialog.max_spin.setValue(min_value)
        invert_btn.clicked.connect(invertValues)
        grid.addWidget(invert_btn, 3, 1)

        button_box = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok|QtGui.QDialogButtonBox.Cancel)
        grid.addWidget(button_box, 4, 0, 1, 2)
        button_box.accepted.connect(self.map_ext_dialog.accept)
        button_box.rejected.connect(self.map_ext_dialog.reject)
        def setTextData(widget, ext):
#            widget = widget_data.inst
#            ext = widget_data.ext
            if not isinstance(ext, tuple):
                ext = (0, 127)
            self.map_ext_dialog.caption.setText('Set range values for <b>{}</b>:'.format(widget.readable))
            self.map_ext_dialog.min_spin.setValue(ext[0])
            self.map_ext_dialog.max_spin.setValue(ext[1])
            if isinstance(widget, QtGui.QPushButton):
                self.map_ext_dialog.min_lbl.setText('<b>OFF</b>')
                self.map_ext_dialog.max_lbl.setText('<b>ON</b>')
            else:
                self.map_ext_dialog.min_lbl.setText('Minimum')
                self.map_ext_dialog.max_lbl.setText('Maximum')
        self.map_ext_dialog.setTextData = setTextData
            

        self.automap_current = 0
        self.automap_chkbtn.toggled.connect(self.automap_set)

        for widget in self.widget_order:
            map_action = QtGui.QAction('Map', widget)
            map_action.triggered.connect(self.single_map_start)
            widget.addAction(map_action)
            widget.map_action = map_action
            ext_action = QtGui.QAction('Set range', widget)
            ext_action.triggered.connect(self.single_map_ext)
            widget.addAction(ext_action)
            clear_action = QtGui.QAction('Clear', widget)
            clear_action.triggered.connect(self.single_map_clear)
            widget.addAction(clear_action)
            #TODO: not important, disable if not set
            if isinstance(widget, QtGui.QPushButton):
                toggle_action = QtGui.QAction('Toggle', widget)
                toggle_action.setCheckable(True)
                toggle_action.triggered.connect(self.single_map_toggle_set)
                widget.addAction(toggle_action)
                widget.toggle_action = toggle_action
            else:
                widget.toggle_action = None

#        led_list = [(i, 0) for i in range(48)]
#        set_led(0, *led_list)
        set_led(0, *[(i, 0) for i in range(48)])
        mapping_raw = ''
        try:
            with open(self.map_file, 'r') as cf:
                for line in cf.readlines():
                    mapping_raw += line
        except:
            self.map_file = default_map
            try:
                with open(self.map_file, 'r') as cf:
                    for line in cf.readlines():
                        mapping_raw += line
            except:
                print 'Default mapping not found!'
        mapping_raw = mapping_raw.replace('CTRL', 'md.CTRL')
        mapping_raw = mapping_raw.replace('NOTE', 'md.NOTE')
        try:
            for k, v in eval(mapping_raw).items():
                self.map_dict[k] = {ctrl:Widget(getattr(self, '{}'.format(widget)), ext, mode) for ctrl, (widget, ext, mode) in v.items()}
            leds = []
            for ctrl, widget_data in self.map_dict[0].items():
                widget = widget_data.inst
                widget.siblingLabel.setText('Ch{},{}{}'.format(ctrl[0], 'CC' if ctrl[1] == md.CTRL else 'N', ctrl[2]))
                if widget.siblingLed is not None:
                    leds.append((widget.siblingLed, widget.ledSet))
            set_led(0, *leds)
        except Exception as e:
            print e
        self.enable_template_buttons(False)
        self.automap_chkbtn.setEnabled(False)
        self.clear_template_leds()
        if not any([True if len(d) else False for d in self.map_dict.values()]):
            self.savemap_btn.setEnabled(False)

        for widget in self.map_dict[0].values():
            widget.inst.map_action.setText('Remap')
            if isinstance(widget.inst, QtGui.QPushButton):
                widget.inst.toggle_action.setCheckable(True)
                if widget.mode == Toggle:
                    widget.inst.toggle_action.setChecked(True)
                    widget.inst.setCheckable(True)
                

    def enable_template_buttons(self, state):
        template_widgets = self.temp_id_group.buttons() + self.temp_type_group.buttons()
        for widget in template_widgets:
            widget.setEnabled(state)

    def clear_template_leds(self):
        def clear(template_iter):
            if template_iter == 16:
                self.enable_template_buttons(True)
                self.automap_chkbtn.setEnabled(True)
                self.startup_box.done(True)
                return
            self.startupbox_setText(template_iter)
            leds = []
            for widget in self.widget_order:
                if widget.siblingLed is None:
                    continue
                if widget in [w.inst for w in self.map_dict[template_iter].values()]:
                    leds.append((widget.siblingLed, widget.ledSet))
                else:
                    leds.append((widget.siblingLed, 0))
            set_led(template_iter, *leds)
            QtCore.QTimer.singleShot(200, lambda: clear(template_iter+1))
        QtCore.QTimer.singleShot(200, lambda: clear(1))


    def single_map_clear(self, widget=None):
        #TODO: (not important, just readability: rename widget and sender_widget
        if widget:
            sender_widget = widget
        else:
            sender_widget = self.sender().parent()
        if sender_widget not in [w.inst for w in self.map_dict[self.template].values()]:
            return
        sender_widget.map_action.setText('Map')
        sender_widget.siblingLabel.setText('')
        for ctrl, widget in self.map_dict[self.template].items():
            if widget.inst == sender_widget:
                break
        del self.map_dict[self.template][ctrl]
        if sender_widget.siblingLed is not None:
            set_led(self.template, (sender_widget.siblingLed, 0))
        if not any([True if len(d) else False for d in self.map_dict.values()]):
            self.savemap_btn.setEnabled(False)

    def single_map_toggle_set(self, value, widget=None):
        if widget:
            sender_widget = widget
        else:
            sender_widget = self.sender().parent()
        for e, w in self.map_dict[self.template].items():
            if w.inst == sender_widget:
                self.map_dict[self.template][e] = Widget(w.inst, w.ext, Toggle if value else Push)
                
        sender_widget.setCheckable(value)

    def map_confirm_response(self, old_widget, new_widget, event, is_set):
        event_type = 'CC' if event.type == md.CTRL else 'NOTE'
        if is_set:
            print is_set
            self.map_confirm.setText('{} already mapped by {} {} on channel {}.\nAlso, {} is already set.\nRemap this event to it?'.format(old_widget, event_type, event.data1, event.channel, new_widget))
        else:
            self.map_confirm.setText('{} already mapped by {} {} on channel {}.\nRemap this event to {}?'.format(old_widget, event_type, event.data1, event.channel, new_widget))
        return self.map_confirm.exec_()

    def single_map_ext(self):
        sender_widget = self.sender().parent()
        widget_is_set = False
        for event, widget_data in self.map_dict[self.template].items():
            widget = widget_data.inst
            if widget == sender_widget:
                widget_is_set = True
                break
        if not widget_is_set:
            return
        self.map_ext_dialog.setTextData(widget, widget_data.ext)
        res = self.map_ext_dialog.exec_()
        if not res:
            return
        ext = (self.map_ext_dialog.min_spin.value(),  self.map_ext_dialog.max_spin.value())
        if ext == (0, 127):
            ext = True
        self.map_dict[self.template][event] = Widget(widget, ext, widget_data.mode)

    def single_map_start(self):
        sender_widget = self.sender().parent()
        if sender_widget in [w.inst for w in self.map_dict[self.template].values()]:
            #TODO: assegna anche widget già impostati
            #TODO: ma che cazzo volevi dire qui sopra?
            pass
#            sender_widget.siblingLabel.setText('')
        self.automap_current = sender_widget.id
        self.singlemap_enabled = True
        self.led_flash(True)
        self.map_dialog.open()

    def single_map_stop(self):
        self.singlemap_enabled = False
        if self.map_dialog.result() == True:
            self.savemap_btn.setEnabled(True)
            return
#        self.map_dict[self.template][(event.channel, event_type, event.data1)] = widget_data[0]
        sender_widget = self.widget_order[self.automap_current]
        if sender_widget not in [w.inst for w in self.map_dict[self.template].values()]:
            if self.automap_current < 24:
                set_led(self.template, (self.automap_current, 0))
            elif 24 <= self.automap_current < 32:
                set_led(self.template, (self.automap_current, 0), (self.automap_current+8, 0))
            else:
                set_led(self.template, (self.automap_current-8, 0))
        else:
            if sender_widget.siblingLed:
                set_led(self.template, (sender_widget.siblingLed, 0x30 if sender_widget.siblingLed<40 else 0x33))

    def automap_set(self, state):
        self.automap_enabled = state
        if not isinstance(self.sender(), QtGui.QPushButton):
            self.automap_chkbtn.setEnabled(True)
        if state:
            self.enable_template_buttons(False)
            if len(self.map_dict[self.template].values()) == len(self.widget_order):
                self.automap_chkbtn.setChecked(False)
                return
            start = 0
            start_set = False
            for i, (widget, label, led) in enumerate(self.widget_order):
                if widget not in [w.inst for w in self.map_dict[self.template].values()]:
                    label.setText('')
                    widget.map_action.setText('Map')
                    if not start_set:
                        widget.setFocus(True)
                        start = i
                        start_set = True
                else:
                    widget.map_action.setText('Remap')
            self.automap_current = start
            if self.automap_current == len(self.widget_order):
                return
            self.led_flash(True)
        else:
            self.enable_template_buttons(True)
#            if self.sender() == self.automap_chkbtn:
#                self.automap_change_timer.stop()
            if self.automap_current == len(self.widget_order):
                return
            if self.automap_current < 24:
                set_led(self.template, (self.automap_current, 0))
            elif 24 <= self.automap_current < 32:
                set_led(self.template, (self.automap_current, 0), (self.automap_current+8, 0))
            else:
                set_led(self.template, (self.automap_current-8, 0))
            if not any([True if len(d) else False for d in self.map_dict.values()]):
                self.savemap_btn.setEnabled(False)
            else:
                self.savemap_btn.setEnabled(True)

    def midi_map(self, event):
        if self.automap_enabled:
            if event.type in [md.NOTEON, md.NOTEOFF]:
                event_type = md.NOTE
            else:
                event_type = event.type
            if (event.channel, event_type, event.data1) not in self.map_dict[self.template]:
                widget = self.widget_order[self.automap_current]
                if not isinstance(widget, QtGui.QPushButton):
                    mode = Value
                else:
                    #TODO: check for different button types
                    mode = Push
                self.map_dict[self.template][(event.channel, event_type, event.data1)] = Widget(widget, True, mode)
                widget.siblingLabel.setText('Ch{},{}{}'.format(event.channel, 'CC' if event_type == md.CTRL else 'N', event.data1))
                widget.map_action.setText('Remap')
                if widget.siblingLed is not None:
                    set_led(self.template, (widget.siblingLed, 0x30 if widget.siblingLed<40 else 0x33))
                else:
                    fader = int(str(widget.inst.objectName())[-1])
                    set_led(self.template, (fader+24, 0), (fader+32, 0))
                self.automap_current += 1
                if self.automap_current == len(self.widget_order):
                    if self.automap_cont_chk.isChecked() and self.template < 15:
                        self.automap_set(False)
                        self.automap_chkbtn.setEnabled(False)
                        #widget alert?
                        QtCore.QTimer.singleShot(300, self.next_map_setup)
                    else:
                        self.automap_current = 0
                        self.automap_chkbtn.setChecked(False)
                else:
                    widget_list = [w.inst for w in self.map_dict[self.template].values()]
                    while self.widget_order[self.automap_current].inst in widget_list:
                        self.automap_current += 1
                        if self.automap_current == len(self.widget_order):
                            if self.automap_cont_chk.isChecked and self.template <= 15:
                                self.automap_set(False)
                                self.automap_chkbtn.setEnabled(False)
                                #widget alert?
                                QtCore.QTimer.singleShot(300, self.next_map_setup)
                            else:
                                self.automap_current = 0
                                self.automap_chkbtn.setChecked(False)
                            break
                    if self.automap_current < len(self.widget_order):
                        self.widget_order[self.automap_current].inst.setFocus()
    #                self.led_flash(0x33, True)
        elif self.singlemap_enabled and not self.map_confirm.isVisible():
            self.map_dialog.done(True)
            if event.type in [md.NOTEON, md.NOTEOFF]:
                event_type = md.NOTE
            else:
                event_type = event.type
            widget = self.widget_order[self.automap_current]
            if not isinstance(widget, QtGui.QPushButton):
                mode = Value
            else:
                mode = Push
            widget_old = self.map_dict[self.template].get((event.channel, event_type, event.data1))
            prev_widget_deleted = False
            if widget_old and widget != widget_old.inst:
                widget_old = widget_old.inst
                widget_is_set = False
                for c, w in self.map_dict[self.template].items():
                    if w.inst == widget:
                        widget_is_set = c
                        del self.map_dict[self.template][c]
                        prev_widget_deleted = True
                        break
                if self.map_confirm_response(widget_old.readable, widget.readable, event, widget_is_set) == QtGui.QMessageBox.Ok:
                    map = True
                    widget_clear = self.map_dict[self.template].pop((event.channel, event_type, event.data1)).inst
                    if widget_clear != widget_old:
                        print 'WTF?!'
                        print widget_clear
                    else:
                        widget_clear.siblingLabel.setText('')
                        if widget_old.siblingLed is not None:
                            set_led(self.template, (widget_old.siblingLed, 0))
                else:
                    map = False
            else:
                map = True
            if map:
                if not prev_widget_deleted:
                    for c, w in self.map_dict[self.template].items():
                        if w.inst == widget:
                            del self.map_dict[self.template][c]
                            break
                self.map_dict[self.template][(event.channel, event_type, event.data1)] = Widget(widget, True, mode)
                widget.map_action.setText('Remap')
                widget.siblingLabel.setText('Ch{},{}{}'.format(event.channel, 'CC' if event_type == md.CTRL else 'N', event.data1))
                if widget.siblingLed is not None:
                    set_led(self.template, (widget.siblingLed, widget.ledSet))
                else:
                    fader_id = int(str(widget.objectName())[-1])
                    print fader_id
                    for fader_led in range(2):
                        widget = eval('self.btn_{:02d}'.format(fader_id+8*fader_led))
                        if widget in [w.inst for w in self.map_dict[self.template].values()]:
                            if widget.siblingLed is not None:
                                set_led(self.template, (widget.siblingLed, widget.ledSet))
                    #TODO: check for leds?
    #                set_led(self.template, (fader+24, 0), (fader+32, 0))
            self.singlemap_enabled = False

        widget = self.map_dict[self.template].get((event.channel, md.NOTE if event.type in [md.NOTEON, md.NOTEOFF] else event.type, event.data1))
        if widget:
            ext = widget.ext
            mode = widget.mode
            widget = widget.inst
            if isinstance(widget, QtGui.QDial):
                widget.setValue(event.data2)
                set_led(self.template, (widget.siblingLed, widget.ledTrigger))
                QtCore.QTimer.singleShot(200, lambda: set_led(self.template, (widget.siblingLed, widget.ledSet)))
            elif isinstance(widget, QtGui.QSlider):
                if not isinstance(ext, tuple) or ext[0]==ext[1]:
                    widget.setValue(event.data2)
                else:
                    value = event.data2
                    if ext[0] > ext[1]:
                        if value < ext[1]:
                            value = ext[1]
                        elif value > ext[0]:
                            value = ext[0]
                        fract = 127.0/(ext[0]-ext[1])
                        final = fract*(value-ext[1])
                        widget.setValue(127-final)
                    else:
                        if value < ext[0]:
                            value = ext[0]
                        elif value > ext[1]:
                            value = ext[1]
                        fract = 127.0/(ext[1]-ext[0])
                        final = fract*(value-ext[0])
                        widget.setValue(final)
                    
            else:
                if event.type == md.NOTEON:
                    widget.setDown(True)
                    set_led(self.template, (widget.siblingLed, widget.ledTrigger))
                elif event.type == md.NOTEOFF:
                    widget.setDown(False)
                    set_led(self.template, (widget.siblingLed, widget.ledSet))
                else:
                    if not isinstance(ext, tuple):
                        ext = (0, 127)
                    if event.data2 == ext[1]:
                        set_led(self.template, (widget.siblingLed, widget.ledTrigger))
                        widget.setDown(True)
                    elif event.data2 == ext[0]:
                        set_led(self.template, (widget.siblingLed, widget.ledSet))
                        widget.setDown(False)
#                    QtCore.QTimer.singleShot(200, lambda: set_led(self.template, (widget.siblingLed, widget.ledSet)))

    def next_map_setup(self):
        #TODO: check if next templates are empty or not
        led_cmd = {False: [(i, 0) for i in range(40)], True: [(i, 3) for i in range(40)]}
        led_cmd[True][24+self.template+1] = (24+self.template+1, 0x30)
        set_led(self.template+1, *[(i, 0) for i in range(40, 48)])
        cycle_n = 3
        flash_time = 200
        def flash_alert(cycle, state):
            if cycle == cycle_n and not state:
                return
            if not state:
                cycle = cycle+1
            set_led(self.template, *led_cmd[not state])
            QtCore.QTimer.singleShot(flash_time, lambda: flash_alert(cycle, not state))
        self.template_remote_set(self.template+1)
        self.template_send_request()
        QtCore.QTimer.singleShot(flash_time, lambda: flash_alert(0, True))
        QtCore.QTimer.singleShot(flash_time*cycle_n*2+flash_time, lambda: self.automap_set(True))

    def led_flash(self, state):
        if not (self.automap_enabled or self.singlemap_enabled or self.map_confirm.isVisible()) or self.automap_current == len(self.widget_order):
            return
        if state:
            if self.automap_current < 24:
                set_led(self.template, (self.automap_current, 0x33))
            elif 24 <= self.automap_current < 32:
                set_led(self.template, (self.automap_current, 0x33), (self.automap_current+8, 0x33))
            else:
                set_led(self.template, (self.automap_current-8, 0x33))
        else:
            if self.automap_current < 24:
                set_led(self.template, (self.automap_current, 0))
            elif 24 <= self.automap_current < 32:
                set_led(self.template, (self.automap_current, 0), (self.automap_current+8, 0))
            else:
                set_led(self.template, (self.automap_current-8, 0))
#            set_led(self.template, (self.automap_current, 0))
        QtCore.QTimer.singleShot(200, lambda: self.led_flash(not state))

    def show_map(self):
        pairing = []
        for ctrl, widget in self.map_dict[self.template].items():
            pairing.append('({},{},{}):\'{}\','.format(ctrl[0], 'CTRL' if ctrl[1] == md.CTRL else 'NOTE', ctrl[2], widget.inst.objectName()))
#        pairing.sort()
        for p in pairing:
            print p

    def save_map(self):
        if not any([True if len(d) else False for d in self.map_dict.values()]):
            return
        savemap = QtGui.QFileDialog.getSaveFileName(self, 'Save mapping to file', self.map_file if self.map_file else '', 'LaunchPad mappings (*.nlm)')
        if savemap:
            full_map = ['{']
            for template, mapping in self.map_dict.items():
                if len(mapping):
                    full_map.append('{}:{{'.format(template))
                    for ctrl, widget in self.map_dict[template].items():
                        full_map.append('({},{},{}):\'{}\','.format(ctrl[0], 'CTRL' if ctrl[1] == md.CTRL else 'NOTE', ctrl[2], (widget.inst.objectName(), widget.ext, widget.mode)))
                    full_map.append('},')
            full_map.append('}\n')
            with open(savemap, 'w') as fo:
                for line in full_map:
                    fo.write(line)
        
    def routing_setup(self):
        mapping_raw = ''
        try:
            with open(self.map_file, 'r') as cf:
                mapping_raw = cf.read().replace('\n', '')
#                for line in cf.readlines():
#                    mapping_raw += line
        except:
            self.map_file = default_map
            try:
                with open(self.map_file, 'r') as cf:
                    mapping_raw = cf.read().replace('\n', '')
#                    for line in cf.readlines():
#                        mapping_raw += line
            except:
                print 'Default mapping not found!'
        mapping_raw = mapping_raw.replace('CTRL', 'md.CTRL')
        mapping_raw = mapping_raw.replace('NOTE', 'md.NOTE')
        try:
            for k, v in eval(mapping_raw).items():
                self.map_dict[k] = {event:Widget(getattr(self, '{}'.format(widget)), ext, mode) for event, (widget, ext, mode) in v.items()}
        except Exception as e:
            print e

#        #TESTING start
#        temp_map_dict = {t:{} for t in range(16)}
#        for event, widget in [(c, w) for c, w in self.map_dict[0].items() if isinstance(w.inst, QtGui.QSlider)]:
#            temp_map_dict[0][event] = SignalClass(0, widget.inst, widget.ext, widget.mode, dest=1, patch=md.Pass(), text='prot', led=True, led_basevalue=Enabled, led_action=Pass)
#        widget_data = self.map_dict[0][(1, md.NOTE, 41)]
#        temp_map_dict[0][(1, md.NOTE, 41)] = SignalClass(0, widget_data.inst, widget_data.ext, widget_data.mode, dest=1, patch=md.Pass(), text='soka')
#        widget_data = self.map_dict[0][(1, md.CTRL, 49)]
#        temp_map_dict[0][(1, md.CTRL, 49)] = SignalClass(0, widget_data.inst, widget_data.ext, widget_data.mode, dest=1, patch=md.Pass(), text='soka')
#        self.template_dict = {0: 'Test'}
#        #TESTING end
        config_raw = ''
        try:
            with open(self.config, 'rb') as cf:
                config_raw = eval(cf.read().replace('\n', ''))
        except:
            print 'PD!'
        config = {}
        self.template_groups = [[] for i in range(16)]
        self.template_dict = [TemplateClass(self, i+1) for i in range(16)]
        try:
#            out_ports = config_raw.get('output')
            out_ports = []
            for t in config_raw.keys():
                if t == 'output':
                    out_ports = config_raw[t]
                    continue
                config[t] = {}
                for k, v in config_raw[t].items():
                    if k == 'id':
                        self.template_dict[t].name = str(v)
                        continue
                    elif k == 'groups':
                        for g in v:
                            groupbox = self.create_group(g[0], name=g[1], rgba=g[2] if len(g) == 3 else None, show=False)
                            self.template_groups[t].append(groupbox)
                        continue
                    config[t][getattr(self, '{}'.format(k))] = v
        except Exception as e:
            print e
        temp_map_dict = {}
        for template in range(16):
            current_config = {}
            config_dict = config.get(template, [])
            if not len(config_dict):
                temp_map_dict[template] = {}
                continue
            for event, (widget, ext, mode) in self.map_dict[template].items():
                if not widget in config_dict:
                    continue
                patch_data = config_dict[widget]
                ext = (0, 127) if ext==True else (ext[0], ext[1])
                dest = patch_data.get('dest', 1)
                patch = patch_data.get('patch')
                if not patch:
                    patch = md.Pass()
                else:
                    for rep in md_replace:
                        patch = patch.replace(rep, 'md.'+rep)
                    patch = eval(patch)
                text = patch_data.get('text')
                led = patch_data.get('led', True)
                led_basevalue = patch_data.get('led_basevalue', Enabled)
                led_action = patch_data.get('led_action', Pass)
                current_config[event] = SignalClass(template, widget, ext, mode, dest=dest, patch=patch, text=text, led=led, led_basevalue=led_basevalue, led_action=led_action)
            temp_map_dict[template] = current_config

        scenes = {}
        for template in range(16):
            if not len(temp_map_dict[template]):
                self.template_dict[template].enabled = False
                scenes[template+1] = md.Scene('{} template {} (empty)'.format(*template_str(template)), md.Discard())
                continue
            self.template_dict[template].widget_list = [False for w in self.widget_order]
            dest_list = {}
            for (chan, ctrl, value), signal in temp_map_dict[template].items():
                self.template_dict[template].set_widget_signal(signal)
                if signal.dest not in dest_list:
                    dest_list[signal.dest] = {chan: {ctrl: {value: signal}}}
                else:
                    if chan not in dest_list[signal.dest]:
                        dest_list[signal.dest][chan] = {ctrl: {value: signal}}
                    else:
                        if ctrl not in dest_list[signal.dest][chan]:
                            dest_list[signal.dest][chan][ctrl] = {value: signal}
                        else:
                            dest_list[signal.dest][chan][ctrl][value] = signal
            scene_dict = {}
            for dest, chan_dict in dest_list.items():
#            if len(dest_list) == 1:
                #chan_dict > dest_list[port]
#                chan_dict = dest_list.values()[0]
                chan_split_dict = {}
                for chan, ctrl_dict in chan_dict.items():
                    #TODO: FINISCI DI CORREGGERE, CAZZO!
                    if len(ctrl_dict) == 1:
                        if ctrl_dict.keys()[0] == md.CTRL:
                            scene = md.Split({md.CTRL: md.CtrlFilter((f for f in ctrl_dict.values()[0].keys())), md.NOTE: md.Discard()})
                        else:
                            scene = md.Split({md.NOTE: md.KeyFilter(notes=[f for f in ctrl_dict[md.NOTE].keys()]), md.CTRL: md.Discard()})
                    else:
                        scene = md.Split({md.CTRL: md.CtrlSplit({f:s.patch for f, s in ctrl_dict[md.CTRL].items()}), 
                                          md.NOTE: md.KeySplit({f:s.patch for f, s in ctrl_dict[md.NOTE].items()})})
                    if dest_list.keys()[0] != 1:
                         scene = md.Port(dest_list.keys()[0]) >> scene
                    chan_split_dict[chan] = scene
                if len(chan_split_dict) == 1:
                    map_chans = [event[0] for event in self.map_dict[template].keys()]
                    do_chan_split = False
                    for chan in chan_split_dict.keys():
                        if not chan in map_chans:
                            do_chan_split = True
                            break
                    if do_chan_split:
                        scene = md.ChannelSplit(chan_split_dict)
                    else:
                        scene = chan_split_dict.values()[0]
                else:
                    scene = md.ChannelSplit(chan_split_dict)
                scene_dict[dest] = scene
            if len(scene_dict) == 1:
                if scene_dict.keys()[0] == 1:
                    template_scene = scene_dict.values()[0]
                else:
                    template_scene = scene_dict.values()[0] >> md.Port(scene_dict.keys()[0])
            else:
                temp_patch_dict = {}
                for dest, patch in scene_dict.items():
                    temp_patch_dict[dest] = patch
                template_scene = [temp_patch_dict[dest] >> md.Port(dest) for dest in temp_patch_dict.keys()]
            template_id = self.template_dict[template].name
            scenes[template+1] = md.Scene('{} template {}'.format(*template_str(template)) if isinstance(template_id, int) else 'Template {}'.format(template_id), template_scene)
#        print scenes
        self.map_dict = temp_map_dict
        return scenes, out_ports


    def template_connect(self, mode='control'):
        if mode == 'editor':
            update_func = self.template_simple_update
        elif mode == 'mapping':
            update_func = self.template_manual_update
        else:
            update_func = self.template_manual_update_with_groups
        self.temp_type_group.setId(self.user_tmp_radio, 0)
        self.temp_type_group.setId(self.fact_tmp_radio, 1)
        self.user_tmp_radio.toggled.connect(update_func)
        self.fact_tmp_radio.toggled.connect(update_func)
        
        for b in range(8):
            btn = eval('self.template_btn_0{}'.format(b))
            btn.toggled.connect(update_func)
            self.temp_id_group.setId(btn, b)

    def template_manual_update(self, value):
        if value == False:
            return
        temp_id = self.temp_id_group.checkedId()
        type = self.temp_type_group.checkedId()
        self.template = temp_id+type*8
        self.template_send_request()
        self.template_label_update()

    def template_manual_update_with_groups(self, value):
        if value == False:
            return
        [groupbox.hide() for groupbox in self.template_groups[self.template]]
        self.template_manual_update(value)
        [groupbox.show() for groupbox in self.template_groups[self.template]]

    def template_send_request(self):
        sysex = [0xF0, 0x00, 0x20, 0x29, 0x02, 0x11, 0x77, self.template, 0xF7]
        event = md.event.SysExEvent(md.engine.out_ports()[-1], sysex)
        md.engine.output_event(event)

    def template_remote_set(self, template):
        if template == self.template:
            return
        [groupbox.hide() for groupbox in self.template_groups[self.template]]
        self.template = template
        [groupbox.show() for groupbox in self.template_groups[self.template]]
        if template >= 8:
            self.fact_tmp_radio.blockSignals(True)
            self.fact_tmp_radio.setChecked(True)
            self.fact_tmp_radio.blockSignals(False)
            template = template - 8
        else:
            self.user_tmp_radio.blockSignals(True)
            self.user_tmp_radio.setChecked(True)
            self.user_tmp_radio.blockSignals(False)
        template_btn = eval('self.template_btn_0{}'.format(template))
        template_btn.blockSignals(True)
        template_btn.setChecked(True)
        template_btn.blockSignals(False)
        self.template_label_update()

    def template_label_update(self):
        if self.mapping:
            widget_dict = {}
            for event, widget_data in self.map_dict[self.template].items():
                widget_dict[widget_data.inst] = (event, widget_data.ext, widget_data.mode)
            for widget in self.widget_order:
                event, ext, mode = widget_dict.get(widget, (None, None, None))
                if event:
                    channel, ctrl, data1 = event
                    widget.siblingLabel.setText('Ch{},{}{}'.format(channel, 'CC' if ctrl == md.CTRL else 'N', data1))
                    try:
                        widget.map_action.setText('Remap')
                        if isinstance(widget, QtGui.QPushButton):
                            widget.toggle_action.setChecked(True if mode==Toggle else False)
                            widget.setCheckable(True if mode==Toggle else False)
                    except:
                        pass
                else:
                    widget.siblingLabel.setText('')
                    try:
                        widget.map_action.setText('Map')
                        if isinstance(widget, QtGui.QPushButton):
                            widget.toggle_action.setChecked(False)
                            widget.setCheckable(False)
                    except:
                        pass
            return
        widget_dict = {signal.widget:signal for signal in self.map_dict[self.template].values()}
        for widget in self.widget_order:
            if widget in widget_dict:
                signal = widget_dict[widget]
                widget.setVisible(True)
                widget.siblingLabel.setVisible(True)
                widget.siblingLabel.setText(signal.text)
                if isinstance(widget, QtGui.QPushButton):
                    if signal.value == signal.ext[0]:
                        widget.setDown(False)
                    else:
                        if signal.mode == Toggle:
                            widget.setDown(True)
                        else:
                            widget.setDown(False)
                else:
                    widget.setValue(signal.value)
            else:
                widget.setVisible(False)
                widget.siblingLabel.setVisible(False)
        template_id = self.template_dict[self.template].name
        if isinstance(template_id, int):
            if self.template < 8:
                template_text = 'User template {}'.format(self.template)
            else:
                template_text = 'Factory template {}'.format(self.template)
        else:
            template_text = template_id
        template_empty = False if len(self.template_dict[self.template].widget_list) else True
        if template_empty:
#            template_text += ' (empty)'
            self.template_lbl.setEnabled(False)
        else:
            self.template_lbl.setEnabled(True)
        self.template_lbl.setText(template_text)

    def routing_start(self):
        self.map_group.setVisible(False)
        self.template_manual_update(True)
        if not self.template_dict[0].enabled:
            #TODO: NO! devi proseguire!
            return
        set_led(0, *[(i, 0) for i in range(48)])
        led_list = []
        for id, signal in enumerate(self.template_dict[0].widget_list):
            widget = self.widget_order[id]
            if not signal:
                widget.setVisible(False)
                widget.siblingLabel.setVisible(False)
                continue
            if signal.led:
                led_list.append((widget.siblingLed, signal.led_basevalue))
            if signal.text:
                widget.siblingLabel.setText(signal.text)
        set_led(0, *led_list)
        self.clear_template_leds()

    def midi_action(self, event):
        if event.type == md.CTRL:
            event_type = event.type
        else:
            event_type = md.NOTE
        widget_data = self.map_dict[self.template].get((event.channel, event_type, event.data1))
        if not widget_data:
            return
        widget_data.trigger(event.data2)
        widget = widget_data.widget
        ext = widget_data.ext
        mode = widget_data.mode
        if not isinstance(widget, QtGui.QPushButton):
            widget.setValue(event.data2)
        else:
            if ext == True:
                ext = (0, 127)
            if event.data2 == ext[1]:
                widget.setDown(True)
            elif event.data2 == ext[0]:
                widget.setDown(False)
        self.map_dict[self.template][(event.channel, event_type, event.data1)].value = event.data2


    def editor_start(self):
        self.map_group.setVisible(False)
        self.overlay_tooltip_list = []
        self.label_order = []
        for widget in self.widget_order:
            label = widget.siblingLabel
            label.siblingWidget = widget
            self.label_order.append(label)
        self.template_list = []
        self.template_groups = [[] for i in range(16)]
        self.map_dict = {}
        for t in range(16):
            self.template_list.append(None)
            self.map_dict[t] = {}
            for w in self.widget_order:
                self.map_dict[t][w] = None
#        print self.map_dict
        config_output = []
        if self.config:
            try:
                with open(self.config, 'rb') as cf:
                    config_raw = eval(cf.read().replace('\n', ''))
                    for k, v in config_raw.items():
                        if k == 'output':
                            config_output = v
                            continue
                        template_dict = config_raw[k]
                        for w, x in template_dict.items():
                            if w == 'id':
                                self.template_list[k] = x
                                continue
                            elif w == 'groups':
                                self.template_groups[k] = x
                                continue
                            self.map_dict[k][getattr(self, '{}'.format(w))] = x
            except Exception as e:
                print 'PD!'
                print e

        self.template_simple_update(startup=True)
#        base_template = self.template_list[0]
#        if base_template:
#            self.template_lbl.setText(base_template)
#        else:
#            self.template_lbl.setText('User template 1')

        self.output_widget = OutputWidget(self)
        self.output_widget.setGeometry(self.map_group.geometry())
        self.output_listview = self.output_widget.output_list
        output_action = QtGui.QAction('Edit', self.output_listview)
        output_action.triggered.connect(self.output_port_edit)
        self.output_listview.addAction(output_action)
        self.output_model = QtGui.QStandardItemModel(self.output_listview)
        self.output_listview.closeEditor = self.validate_output
        self.output_widget.button_box.button(QtGui.QDialogButtonBox.Save).clicked.connect(self.config_save)

        self.output_listview.setModel(self.output_model)
#        config_output = self.map_dict.get('output')
        if config_output and len(config_output):
            for output in config_output:
                if isinstance(output, str):
                    output_item = QtGui.QStandardItem(output)
                    output_item.port = None
                else:
                    output_item = QtGui.QStandardItem(output[0])
                    output_item.port = ', '.join(output[1:])
                    font = output_item.font()
                    font.setBold(True)
                    output_item.setFont(font)
                self.output_model.appendRow(output_item)
        else:
            output = QtGui.QStandardItem('Output')
            output.port = None
            self.output_model.appendRow(output)
        self.output_listview.setCurrentIndex(self.output_model.createIndex(0, 0))

        self.output_widget.remove_btn.setEnabled(False if self.output_model.rowCount() == 1 else True)
        self.output_widget.add_btn.clicked.connect(self.add_output)
        self.output_widget.remove_btn.clicked.connect(self.remove_output)
        self.output_widget.up_btn.clicked.connect(self.output_move)
        self.output_widget.down_btn.clicked.connect(self.output_move)
        self.output_widget.show_tooltip_chk.toggled.connect(self.show_overlay)

        
        self.editor_win = EditorWin(self)
        self.editor_win.labelChanged.connect(self.label_update)
        self.editor_win.show()
        for widget in self.widget_order:
            ext_action = QtGui.QAction('Edit controller', widget)
            ext_action.triggered.connect(self.editor_widget_edit)
            widget.addAction(ext_action)
            clear_action = QtGui.QAction('Clear controller', widget)
            clear_action.triggered.connect(self.editor_widget_clear)
            widget.addAction(clear_action)
            #TODO: not important, disable if not set
            if isinstance(widget, QtGui.QPushButton):
                toggle_action = QtGui.QAction('Toggle', widget)
                toggle_action.setCheckable(True)
                toggle_action.triggered.connect(self.editor_widget_toggle_set)
#                widget.addAction(toggle_action)
                widget.toggle_action = toggle_action
            else:
                widget.toggle_action = None
            [widget.siblingLabel.addAction(action) for action in widget.actions()]

        app = QtCore.QCoreApplication.instance()
        app.installEventFilter(self)
        self.ignored_events = [QtCore.QEvent.MouseButtonPress, 
                               QtCore.QEvent.MouseMove, 
                               QtCore.QEvent.Wheel, 
                               QtCore.QEvent.KeyPress, 
                               QtCore.QEvent.KeyRelease, 
                              ]
        self.eventFilter = self.editor_eventFilter
        self.rubber = None
        self.rubber_mode = None
        self.mouseMoveEvent = self.editor_mouseMoveEvent
        self.mouseReleaseEvent = self.editor_mouseReleaseEvent

        for widget in self.widget_order:
            widget_dict = self.map_dict[self.template][widget]
            widget.setToolTip(self.widget_tooltip(widget, self.map_dict[self.template][widget]))

    def show_overlay(self, value):
        if value:
            for widget, dict in self.map_dict[self.template].items():
                if dict is not None:
                    dest = dict.get('dest')
                    siblingLed = widget.siblingLed
                    led = dict.get('led', siblingLed)
                    if led == siblingLed:
                        led_text = 'default' if led is not None else '(No)'
                    else:
                        led_text = self.editor_win.ledlist_model.item(siblingLed).text()
                    led_action = dict.get('led_action')
                    self.overlay_tooltip_list.append(MyToolTip(widget, '> <b>{}</b><br>&#9788; {}'.format(self.output_model.item(dest-1).text() if dest is not None else self.output_model.item(0).text(), led_text)))
        else:
            for t in range(len(self.overlay_tooltip_list)):
                led = self.overlay_tooltip_list.pop(-1)
                led.deleteLater()

    def add_output(self):
        output = QtGui.QStandardItem()
        count = self.output_model.rowCount()
        basename = 'Output {}'
        namelist = [self.output_model.item(i, 0).text() for i in range(count)]
        while True:
            name = basename.format(count+1)
            if name not in namelist:
                break
            count += 1
            
        output.setText(name)
        output.port = None
        self.output_model.appendRow(output)
        self.output_widget.remove_btn.setEnabled(True)
        rowCount = self.output_model.rowCount()
        self.output_widget.output_group.setTitle('Outputs ({}/8)'.format(rowCount))
        if rowCount >= 8:
            self.output_widget.add_btn.setEnabled(False)
        self.outputChanged.emit()

    def validate_output(self, *args):
        QtGui.QListView.closeEditor(self.output_listview, *args)
        index = self.output_listview.currentIndex().row()
        item = self.output_model.item(index, 0)
        name = str_check(item.text())
        item.setText(name)
        item.port = None
        namelist = [self.output_model.item(i, 0).text() for i in range(self.output_model.rowCount()) if i != index]
        count = 2
        if name not in namelist:
            self.outputChanged.emit()
            return
        while True:
            new_name = '{} {}'.format(name, count)
            if new_name not in namelist:
                break
            count += 1
        item.setText(new_name)
        self.outputChanged.emit()

    def remove_output(self):
        self.output_model.takeRow(self.output_listview.currentIndex().row())[0]
        rowCount = self.output_model.rowCount()
        self.output_widget.output_group.setTitle('Outputs ({}/8)'.format(rowCount))
        if rowCount == 1:
            self.output_widget.remove_btn.setEnabled(False)
        if rowCount < 8:
            self.output_widget.add_btn.setEnabled(True)
        self.outputChanged.emit()

    def output_move(self):
        row = self.output_listview.currentIndex().row()
        if self.sender() == self.output_widget.up_btn:
            if row == 0:
                return
            delta = -1
        else:
            if row >= self.output_model.rowCount()-1:
                return
            delta = 1
        item = self.output_model.takeRow(row)[0]
        self.output_model.insertRow(row+delta, item)
        self.output_listview.setCurrentIndex(self.output_model.createIndex(row+delta, 0))
        self.outputChanged.emit()
#        for i in range(self.output_model.rowCount()):
#            print self.output_model.item(i, 0).text()

    def output_port_edit(self):
        def reset():
            input_dialog.done(-1)
        index = self.output_listview.currentIndex().row()
        item = self.output_model.item(index, 0)
        label_text = 'Enter the port name(s) "{}" will try to connect to.\n\nYou may use regular expressions, for example:\n"LinuxSampler:.*"'.format(item.text())
        input_dialog = QtGui.QDialog()
        layout = QtGui.QVBoxLayout(input_dialog)
        input_dialog.setWindowTitle('Set destination port(s)')
        input_dialog.setModal(True)
        input_label = QtGui.QLabel(label_text, input_dialog)
        input_edit = QtGui.QLineEdit(item.port)
        input_buttonbox = QtGui.QDialogButtonBox(input_dialog)
        input_buttonbox.setStandardButtons(QtGui.QDialogButtonBox.Reset|QtGui.QDialogButtonBox.Ok|QtGui.QDialogButtonBox.Cancel)
        input_buttonbox.button(QtGui.QDialogButtonBox.Ok).clicked.connect(input_dialog.accept)
        input_buttonbox.button(QtGui.QDialogButtonBox.Cancel).clicked.connect(input_dialog.reject)
        input_buttonbox.button(QtGui.QDialogButtonBox.Reset).clicked.connect(reset)
        layout.addWidget(input_label)
        layout.addWidget(input_edit)
        layout.addWidget(input_buttonbox)
        res = input_dialog.exec_()
        font = item.font()
        if res == 0:
            return
        if res == -1:
            font.setBold(False)
            item.port = None
        else:
            port = str(input_edit.text().toLatin1())
            if len(port.strip()):
                font.setBold(True)
                item.port = port.strip()
            else:
                font.setBold(False)
                item.port = None
        item.setFont(font)

    def label_update(self, widget, text):
        if text == True:
            widget.siblingLabel.setText('(set)')
        elif text == False:
            widget.siblingLabel.setText('')
        else:
            widget.siblingLabel.setText(elide_str(widget.siblingLabel, text))

    def editor_mouseMoveEvent(self, event):
        if not self.rubber:
            return
        pos = event.pos()
        max_x = self.label_knob_07.x() + self.label_knob_07.width()
        max_y = self.btn_15.y() + self.btn_15.height()
        if pos.x() >= max_x:
            pos.setX(max_x)
        elif pos.x() < 0:
            pos.setX(0)
        if pos.y() >= max_y:
            pos.setY(max_y)
        elif pos.y() < 0:
            pos.setY(0)
        self.rubber.resize(50, -50)
        x = min(self.rubber.startx, pos.x())
        y = min(self.rubber.starty, pos.y())
        w = max(self.rubber.startx, pos.x())-x
        h = max(self.rubber.starty, pos.y())-y
        self.rubber.setGeometry(QtCore.QRect(x, y, w, h))

    def editor_mouseReleaseEvent(self, event):
        if not self.rubber:
            return
        self.rubber.hide()
        selection = []
        for widget in self.widget_order[:48]:
            if self.rubber.geometry().intersects(widget.geometry()):
                selection.append(widget)
        if not len(selection):
            self.rubber = None
            return

        if self.rubber_mode == GroupMode:
            self.create_group((selection[0].grid_col, selection[0].grid_row, selection[-1].grid_col, selection[-1].grid_row), True)
        else:
            out_ports = [self.output_model.item(i).text() for i in range(self.output_model.rowCount())]
            port, res = QtGui.QInputDialog.getItem(self, 'Set port for multiple widgets', 'Select the default destination port for the selected widgets:', out_ports, 0, False)
            if res:
                dest = out_ports.index(port)
                for widget in selection:
                    widget_dict = self.map_dict[self.template][widget]
                    if widget_dict is None:
                        self.map_dict[self.template][widget] = {'dest': dest+1, 'enabled': False}
                    else:
                        self.map_dict[self.template][widget]['dest'] = dest+1
                    if self.editor_win.current_widget:
                        self.editor_win.dest_combo.setCurrentIndex(dest)
        self.rubber = None
        for child in self.centralWidget().children():
            if child in self.template_groups[self.template]:
                print child.title()

    def create_group(self, rect, interactive=False, name='Group', rgba=None, show=True):
        groupbox = QtGui.QGroupBox(name, self.centralWidget())
        groupbox.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        rename_action = QtGui.QAction('Rename group', groupbox)
        rename_action.triggered.connect(self.rename_group)
        groupbox.addAction(rename_action)
        color_action = QtGui.QAction('Set background color', groupbox)
        color_action.triggered.connect(self.color_group)
        groupbox.addAction(color_action)
        raise_action = QtGui.QAction('Raise group', groupbox)
        raise_action.triggered.connect(self.raise_group)
        groupbox.addAction(raise_action)
        lower_action = QtGui.QAction('Lower group', groupbox)
        lower_action.triggered.connect(self.lower_group)
        groupbox.addAction(lower_action)
        delete_action = QtGui.QAction('Delete group', groupbox)
        delete_action.triggered.connect(self.delete_group)
        groupbox.addAction(delete_action)
#        group_menu.addAction(rename_action)
#        group_menu.addAction(color_action)
        
        groupbox.extents = rect
        x, y, w, h = rect
        width = w-x+1
        top = 0
        height = 0
        for r in range(h+1):
            if r < y:
                top += row_heights[r]
            else:
                height += row_heights[r]
        groupbox.move(5+x*70, 10+top)
        groupbox.resize(width*70, height)
        if show:
            groupbox.show()
        else:
            groupbox.hide()
        groupbox.lower()
        if rgba:
            #TODO: valuta l'uso di background-clip: padding;
            groupbox.setStyleSheet('''QGroupBox {{ background-color: rgba({},{},{},{});
                                    background-clip: padding;
                                    border-radius:5px;
                                    border-right-width: 1px;
                                    border-right-color: white;
                                    border-right-style: solid;}}'''.format(*rgba))
            groupbox.colors = rgba
        else:
            groupbox.colors = None
        if not interactive:
            return groupbox
        label, res = QtGui.QInputDialog.getText(self, 'Group name', 'Enter name for this group', QtGui.QLineEdit.Normal, name)
        if res:
            groupbox.setTitle(label)
            self.template_groups[self.template].append(groupbox)
        else:
            groupbox.deleteLater()

    def rename_group(self):
        groupbox = self.sender().parent()
        label, res = QtGui.QInputDialog.getText(self, 'Group name', 'Enter name for this group', QtGui.QLineEdit.Normal, groupbox.title())
        if res:
            groupbox.setTitle(label)

    def delete_group(self):
        groupbox = self.sender().parent()
        self.template_groups[self.template].pop(self.template_groups[self.template].index(groupbox))
        groupbox.deleteLater()
        print self.template_groups[self.template]

    def color_group(self):
        groupbox = self.sender().parent()
        bgcolor = groupbox.palette().background().color()
        color = QtGui.QColorDialog.getColor(bgcolor, self, 'prot', QtGui.QColorDialog.ShowAlphaChannel)
        if QtGui.QColor.isValid(color):
            groupbox.setStyleSheet('''QGroupBox {{ background-color: rgba({},{},{},{});
                                    background-clip: padding;
                                    border-radius:5px;
                                    border-right-width: 1px;
                                    border-right-color: white;
                                    border-right-style: solid;}}'''.format(color.red(), color.green(), color.blue(), color.alpha()))
            groupbox.colors = (color.red(), color.green(), color.blue(), color.alpha())
        else:
            groupbox.setStyleSheet('')
            groupbox.colors = None

    def raise_group(self):
        groupbox = self.sender().parent()
        for id, group in enumerate(self.template_groups[self.template]):
            if group == groupbox:
                group_id = id
                continue
            group.stackUnder(groupbox)
        temp = self.template_groups[self.template].pop(group_id)
        self.template_groups[self.template].insert(0, temp)

    def lower_group(self):
        groupbox = self.sender().parent()
        last = self.template_groups[self.template][-1]
        if last == groupbox:
            return
        groupbox.stackUnder(last)
        temp = self.template_groups[self.template].pop(self.template_groups[self.template].index(groupbox))
        self.template_groups[self.template].append(temp)

    def editor_eventFilter(self, source, event):
        if source == self:
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() in [QtCore.Qt.LeftButton, QtCore.Qt.RightButton]:
                self.output_widget.show_tooltip_chk.setChecked(False)
                self.rubber = QtGui.QRubberBand(QtGui.QRubberBand.Rectangle, self)
                self.rubber.setGeometry(QtCore.QRect(event.pos(), QtCore.QSize()))
                self.rubber.startx = self.rubber.x()
                self.rubber.starty = self.rubber.y()
                self.rubber.show()
                if event.button() == QtCore.Qt.LeftButton:
                    self.rubber_mode = GroupMode
                else:
                    self.rubber_mode = DestMode
                return True
            elif event.type() == QtCore.QEvent.MouseMove:
                return False
            elif event.type() == QtCore.QEvent.MouseButtonRelease and self.rubber:
                return False
        if source in self.widget_order+self.label_order:
            if event.type() == QtCore.QEvent.MouseButtonRelease:
                self.output_widget.show_tooltip_chk.setChecked(False)
                if event.button() == QtCore.Qt.RightButton:
#                    print 'menu'
                    return QtGui.QMainWindow.eventFilter(self, source, event)
#                print 'set widget {}'.format(source.readable)
                if isinstance(source, QtGui.QLabel):
                    self.editor_win.widgetChanged.emit(source.siblingWidget)
                    self.editor_win.text_edit.setFocus()
                    self.editor_win.text_edit.selectAll()
                else:
                    self.editor_win.widgetChanged.emit(source)
                return True
            elif event.type() == QtCore.QEvent.MouseButtonDblClick:
                self.editor_win.show()
                self.editor_win.activateWindow()
                return True
            elif event.type() in self.ignored_events:
                return True
        if source == self.template_lbl and event.type() == QtCore.QEvent.MouseButtonDblClick and event.button() == QtCore.Qt.LeftButton:
            id, res = QtGui.QInputDialog.getText(self, 'Template Name', 'Enter template name', QtGui.QLineEdit.Normal, self.template_lbl.text())
            if res:
#                self.map_dict[self.template]['id'] = id
                self.template_list[self.template] = id
                self.template_lbl.setText(id)
        return QtGui.QMainWindow.eventFilter(self, source, event)

    def template_simple_update(self, toggle=None, startup=False):
        if toggle == False:
            return
        old_template = self.template
        temp_id = self.temp_id_group.checkedId()
        ttype = self.temp_type_group.checkedId()
        self.template = temp_id+ttype*8
        if not startup:
            [groupbox.hide() for groupbox in self.template_groups[old_template]]
            if self.editor_win.isVisible():
                self.editor_win.widget_save(old_template)
                self.editor_win.current_widget = None
                self.editor_win.clear_fields()
                self.editor_win.enable_chk.setEnabled(False)
                self.output_widget.show_tooltip_chk.setChecked(False)
            for widget in self.widget_order:
                widget_dict = self.map_dict[self.template][widget]
                widget.setToolTip(self.widget_tooltip(widget, self.map_dict[self.template][widget]))
        else:
            groups = self.template_groups[old_template]
            if groups:
                for gid, groupbox in enumerate(groups):
                    self.template_groups[old_template][gid] = self.create_group(groupbox[0], name=groupbox[1], rgba=groupbox[2] if len(groupbox) == 3 else None)

        template_id = self.template_list[self.template]
        if template_id:
            self.template_lbl.setText(template_id)
        else:
            self.template_lbl.setText('{} template {}'.format('User' if self.template < 8 else 'Factory', self.template))

        groups = self.template_groups[self.template]
        if groups:
            if isinstance(groups[0], QtGui.QGroupBox):
                [groupbox.show() for groupbox in self.template_groups[self.template]]
            else:
                for gid, groupbox in enumerate(groups):
                    self.template_groups[self.template][gid] = self.create_group(groupbox[0], name=groupbox[1], rgba=groupbox[2] if len(groupbox) == 3 else None)
        for widget in self.widget_order:
            if widget in self.map_dict[self.template]:
                widget_data = self.map_dict[self.template][widget]
                if widget_data == None or widget_data.get('enabled') == False:
                    widget.siblingLabel.setText('')
                    continue
                text = widget_data.get('text')
                if text:
                    widget.siblingLabel.setText(text)
                else:
                    text = widget_data.get('patch')
                    if text:
                        widget.siblingLabel.setText(elide_str(widget.siblingLabel, text))
                    else:
                        widget.siblingLabel.setText('(set)')

    def widget_tooltip(self, widget, widget_dict):
        if widget_dict is None:
            return '<b>{}</b><br>enabled: False'.format(widget.readable)
        enabled = widget_dict.get('enabled', True)
        dest = self.editor_win.output_model.item(widget_dict.get('dest', 1)-1).text()
        text = widget_dict.get('text', '(None)')
        led = widget_dict.get('led', True)
        if led == True:
            if widget.siblingLed is not None:
                led_item = self.editor_win.ledlist_model.item(widget.siblingLed+1)
#                led = widget.siblingLed
                led_text = '{} (default)'.format(self.editor_win.ledlist_model.item(widget.siblingLed+1).text())
            else:
                led_item = self.editor_win.ledlist_model.item(0)
#                led = None
                led_text = 'Disabled (default)'
        elif led == False:
            led_item = self.editor_win.ledlist_model.item(0)
#            led = None
            led_text = 'Disabled'
        else:
            led_item = self.editor_win.ledlist_model.item(led)
#            led = item.led
            led_text = led_item.text()
        led_id = led_item.led
        if led_id is not None and led != False:
            led_basevalue = widget_dict.get('led_basevalue')
            if led_basevalue is None or led_basevalue == Enabled:
                led_basevalue = rgb_from_hex(led_item.ledSet)
            elif led_basevalue == Disabled:
                led_basevalue = '#000'
            else:
                if led_id < 40:
                    led_basevalue = rgb_from_hex(led_basevalue)
                elif led_id < 44:
                    led_basevalue = rgb_from_hex(led_basevalue, mode='dev')
                else:
                    led_basevalue = rgb_from_hex(led_basevalue, mode='dir')
            led_extent = '<br>Colors: <span style="background-color: {}">&nbsp;&nbsp;&nbsp;</span> '.format(led_basevalue)

            led_action = widget_dict.get('led_action', Pass)
            if led_action == Pass:
                if isinstance(widget, QtGui.QPushButton):
                    if led_id < 40 or led_id >= 44:
                        led_extent += '<span style="background-color: #f00">&nbsp;&nbsp;&nbsp;</span>'
                    else:
                        led_extent += '<span style="background-color: #ff0">&nbsp;&nbsp;&nbsp;</span>'
                else:
                    led_extent += '<span style="background-color: #f00">&nbsp;&nbsp;&nbsp;</span> (by value)'
            elif led_action == Ignore:
                pass
            else:
                if isinstance(led_action, int):
                    led_extent += '<span style="background-color: #f00">&nbsp;&nbsp;&nbsp;</span>'.format(rgb_from_hex(led_action))
                else:
                    led_extent += 'Function: {}'.format(led_action)
        else:
            led_extent = ''
        if enabled:
            tooltip = '''<b>{}</b><br>
                         enabled: {}<br>
                         port: {}<br>
                         text: {}<br>
                         LED: {}
                         {}'''
        else:
            tooltip = '''<b>{}</b><br>
                         enabled: {}<br>
                         <span style='color: gray'
                         port: {}<br>
                         text: {}<br>
                         LED: {}
                         {}
                         </span>'''
#        print tooltip.format(widget.readable, enabled, dest, text, led_id)
        return tooltip.format(widget.readable, enabled, dest, text, led_text, led_extent)



    def editor_widget_edit(self, *args):
        sender_widget = self.sender().parent()
        self.editor_win.widgetChanged.emit(sender_widget)
        self.editor_win.show()

    def editor_widget_clear(self, *args):
        sender_widget = self.sender().parent()
        if isinstance(sender_widget, QtGui.QLabel):
            sender_widget = sender_widget.siblingWidget
        self.map_dict[self.template][sender_widget] = {'enabled': False}
        sender_widget.siblingLabel.setText('')
        if self.editor_win.current_widget and self.editor_win.current_widget.get('widget') == sender_widget:
            self.editor_win.current_widget = None
            self.editor_win.clear_fields()

    def editor_widget_toggle_set(self, *args):
        pass
#        sender_widget = self.sender().parent()

    def config_save(self):
        self.editor_win.widget_save(self.template)
        save_file = QtGui.QFileDialog.getSaveFileName(self, 'Save config to file', self.config if self.config else '', 'LaunchPad config (*.nlc)')
        if not save_file:
            return
        map_dict = OrderedDict()

        output_list = []
        for id in range(self.output_model.rowCount()):
            output_item = self.output_model.item(id)
            output_name = str(output_item.text())
            output_port = output_item.port
            if output_port is None:
                output_list.append(output_name)
            else:
                output_list.append(tuple([output_name] + [p.strip() for p in output_port.split(',')]))
        if not (len(output_list) == 1 and output_list[0] == 'Output'):
            map_dict['output'] = output_list

        for t in range(16):
            map_dict[t] = OrderedDict()
        for template in range(16):
            template_id = self.template_list[template]
            if template_id:
                map_dict[template]['id'] = template_id
            groups = self.template_groups[template]
            if len(groups):
                group_list = []
                for groupbox in groups:
                    if groupbox.colors:
                        group = (groupbox.extents, str(groupbox.title()), groupbox.colors)
                    else:
                        group = (groupbox.extents, str(groupbox.title()))
                    group_list.append(group)
                map_dict[template]['groups'] = group_list

            for widget in self.widget_order:
                widget_data = self.map_dict[template].get(widget)
                if widget_data is not None:
                    widget_data = copy(widget_data)
                else:
                    continue
                if widget_data is not None and widget_data.get('enabled', True):
                    for k, v in widget_data.items():
                        if k == 'widget':
                            widget_data.pop('widget')
                        elif k == 'enabled':
                            widget_data.pop('enabled')
                        elif k == 'dest':
                            if v == 1:
                                widget_data.pop('dest')
                            else:
                                widget_data['dest'] = v
                        elif k == 'led':
                            if v == True:
                                widget_data.pop('led')
                        elif k == 'text':
                            if not len(v):
                                widget_data.pop('text')
                        elif k == 'led_basevalue' and v == Enabled:
                            widget_data.pop('led_basevalue')
                        elif k == 'led_action' and v == Pass:
                            widget_data.pop('led_action')
                        elif k == 'patch' and (not len(v) or v == 'Pass()'):
                            widget_data.pop('patch')
                    map_dict[template][str(widget.objectName())] = widget_data
            if len(map_dict[template]) == 0:
                map_dict.pop(template)
        dict_str = '{\n'
        for main_k, main_v in map_dict.items():
            if isinstance(main_v, OrderedDict):
                dict_str += '{}: {{\n'.format(main_k)
                for k, v in main_v.items():
                    if isinstance(v, str):
                        dict_str += '\'{}\': \'{}\',\n'.format(str(k), str(v))
                    else:
                        dict_str += '\'{}\': {},\n'.format(str(k), str(v))
                dict_str += '},\n'
            else:
                dict_str += '\'{}\': {},\n'.format(main_k, main_v)
        dict_str += '}'
        print dict_str
#        return
        with open(save_file, 'w') as fo:
#            for line in dict_str.split():
                fo.write(dict_str)

    def closeEvent(self, event):
        if md.engine.active():
            self.router.quit()


def main():
    app = QtGui.QApplication(sys.argv)
    args = process_args()
    win = Win(mode=args.mode, map_file=args.mapfile, config=args.config)
    win.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

