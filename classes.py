import mididings as md
from PyQt4 import QtCore, QtGui
from const import *
from utils import *
from copy import copy
from itertools import cycle

class MyCycle(int, object):
    def __new__(self, values):
        return int.__new__(self, values[0])
    def __init__(self, values):
        self.values = values
        self.cycle = cycle(values)
        self._index_cycle = cycle(range(1, len(values))+[0])
        self.current = self.cycle.next()
        self._index = 0
    @property
    def index(self):
        return self._index
    def __repr__(self):
        return repr(self.current)
    def __add__(self, other):
        return self.current+other
    def __sub__(self, other):
        return self.current-other
    def __neg__(self):
        return -self.current
    def __rsub__(self, other):
        return other-self.current
    def __pos__(self):
        return self.current
    def __radd__(self, other):
        return other+self.current
    def next(self):
        self.current = self.cycle.next()
        self._index = self._index_cycle.next()
        return self.current
    def reset(self):
        self.cycle = cycle(self.values)
        self.current = self.cycle.next()
        self._index = self._index_cycle.next()
        return self.current


class SignalClass(object):
    def __init__(self, template, widget, ext=True, mode=Value, dest=Pass, patch=md.Pass(), range_mode=None, text=None, text_values=None, led=True, led_basevalue=Enabled, led_action=Pass):
        self.widget = widget
        self.inst = widget
        self.template = template
        self.id = widget.id
        self.ext = ext if isinstance(ext, tuple) else (0, 127)
        self.mode = mode
        self.value = self.ext[0]
        self.dest = dest
        self.patch = patch
        self.range_mode = range_mode
        self.label = widget.siblingLabel
        self.basetext = text if text else ''
        if not text_values and not '{}' in self.basetext:
            self.text = self.basetext.format(self.value)
            self.text_values = ['']
            self.trigger = self.base_trigger
        else:
            if text_values:
                self.text_values = text_values
            else:
#                print self.range_mode
#                if isinstance(self.range_mode, tuple):
#                    self.text_values = range(self.range_mode[0], self.range_mode[1]+1)
#                elif isinstance(self.range_mode, MyCycle):
#                    print 'staminchia: {}'.format(self.range_mode.values)
#                else:
                    self.text_values = range(128)
            self.text = self.basetext.format(self.text_values[0])
            self.trigger = self.interactive_trigger
        if led is True:
            if widget.siblingLed is not None:
                self.led = widget.siblingLed
            else:
                self.led = None
        elif isinstance(led, bool) and led == False:
            self.led = None
        else:
            self.led = led
            widget.siblingLed = led
        
#        self.led_basevalue = led_basevalue
        if self.led is not None:
            self.led_setup(led_basevalue)
        else:
            self.led_state = self.led_basevalue = 0
        self.led_assign(led_action)

    def __repr__(self):
        return 'Signal({w}, {p}, {l})'.format(w=self.widget.readable, p=self.patch, l=self.led)

    def led_setup(self, basevalue):
        if basevalue == Enabled:
            if self.led < 40:
                basevalue = 0x30
                triggervalue = 3
                self.led_scale = led_fullscale
            elif self.led < 44:
                basevalue = 0x10
                triggervalue = 0x33
                self.led_scale = led_devscale
            else:
                basevalue = 0x01
                triggervalue = 0x33
                self.led_scale = led_dirscale
            self.led_state = self.led_basevalue = basevalue
            self.led_triggervalue = triggervalue
        elif basevalue == Disabled:
            self.led_state = self.led_basevalue = 0
        else:
            self.led_state = self.led_basevalue = basevalue
            self.led_triggervalue = 0x33 if self.led >= 40 else 3
        self.widget.ledSet = self.ledSet = self.led_basevalue
        self.siblingLed = self.led

    def led_pass_action(self, value):
        set_led(self.template, (self.led, led_fullscale[value]))

    def led_push_action(self, value):
        set_led(self.template, (self.led, self.led_triggervalue if value==self.ext[1] else self.led_basevalue))

    def led_toggle_action(self, value):
        if value != self.ext[1]:
            return
        set_led(self.template, (self.led, self.led_cycle[self.cycle.index]))

    def led_ignore_action(self, event):
        pass

    def led_assign(self, action):
        if self.led is None:
            self.led_action = self.led_ignore_action
            return
        if action == Pass:
            if isinstance(self.widget, QtGui.QPushButton):
                self.led_action = self.led_push_action
            else:
                self.led_action = self.led_pass_action
        elif isinstance(action, MyCycle):
            self.cycle = action
            v_len = len(action.values)
            div = 128 / (v_len - 1)
            self.led_cycle = [self.led_basevalue] + [self.led_scale[div*(m+1)] for m in range(v_len-2)] + [self.led_scale[-1]]
            self.led_action = self.led_toggle_action
        elif isinstance(action, int):
            self.led_triggervalue = action
            if isinstance(self.widget, QtGui.QPushButton):
                self.led_action = self.led_push_action
            else:
                self.led_action = self.led_pass_action
        else:
            self.led_action = self.led_ignore_action

    def base_trigger(self, value):
        self.led_action(value)

    def interactive_trigger(self, value):
        self.led_action(value)
        try:
            self.text = self.basetext.format(self.text_values[value])
        except:
            self.text = self.basetext.format(self.text_values[-1])
        self.widget.siblingLabel.setText(self.text)


class TemplateClass(object):
    def __init__(self, main, id, name=None):
        self.main = main
        self.id = id
        self._name = name
        self.out_ports = None
        self.enabled = True
        self.widget_list = []
        self.current_widget = None

    @property
    def name(self):
        if self._name:
            return self._name
        if self.id >= 8:
            return 'Factory {}'.format(self.id-7)
        else:
            return 'User {}'.format(self.id+1)

    @name.setter
    def name(self, name):
        self._name = name

    def has_name(self):
        return True if self._name else False

    def set_widget_signal(self, signal):
        self.widget_list[signal.id] = signal

    def get_widget(self, id):
        return self.main.widget_order[id]

    def __repr__(self):
        return self.name


class Router(QtCore.QObject):
    template_change = QtCore.pyqtSignal(int)
    midi_signal = QtCore.pyqtSignal(object)
    mididings_exit = QtCore.pyqtSignal()

    def __init__(self, main, mapping=False, backend='alsa'):
        QtCore.QObject.__init__(self)
        self.main = main
        self.backend = backend
        self.already_set = False
        self.mapping = mapping
        if self.mapping:
            self.setup = self.setup_mapping
        else:
            self.setup = self.setup_control

    def setup_mapping(self):
        self.config = md.config(
            backend = self.backend,
            client_name='NoLaE',
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
            backend = self.backend,
            client_name='NoLaE',
            in_ports = [
                ('LC_input', 'Launch.*'), 
                        ],
            out_ports = self.out_ports + [('LC_output', 'Launch.*')],
            )
        self.already_set = True

    def mididings_run(self):
        if not self.already_set:
            self.setup()
        if self.mapping:
            md.run(md.Call(self.event_mapping))
        else:
            md.run(scenes=self.scenes, control=md.Call(self.event_call))
        self.mididings_exit.emit()

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
        if md.engine.active():
            md.engine.quit()
            try:
                while md.engine.active():
                    pass
            except:
                pass
#        QtCore.QThread.quit(self)

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
        self.setStyleSheet('background-color: rgba(210,210,210,210); border: 1px solid gray;')
        self.raise_()

class PianoKey(QtGui.QWidget):
    def __init__(self, parent, id):
        QtGui.QWidget.__init__(self, parent)
        self.id = id
        self.name = md.util.note_name(id)
        self.black = True if self.name[1]=='#' else False
        self.octave, self.note = divmod(id, 12)
        self.hover_color = QtCore.Qt.red
        if self.black:
            self.color = QtCore.Qt.black
            self.setMinimumSize(7, 24)
            self.setMaximumSize(7, 24)
            if (self.note & 1) == 1:
                self.move(self.octave*7*10+self.note/2*10+7, 0)
            else:
                self.move(self.octave*7*10+(self.note+1)/2*10+7, 0)
        else:
            if self.id < 21 or self.id > 108:
                self.color = QtCore.Qt.gray
            elif self.id < 36 or self.id > 96:
                self.color = QtGui.QColor(220, 220, 220)
            elif self.id == 60:
                self.color = QtGui.QColor(230, 230, 230)
            else:
                self.color = QtCore.Qt.white
            self.setMinimumSize(10, 48)
            self.setMaximumSize(10, 48)
            if (self.note & 1) == 0:
                self.move(self.octave*7*10+self.note/2*10, 0)
            else:
                self.move(self.octave*7*10+(self.note+1)/2*10, 0)
            self.lower()
        self._color = self.color
        self.current_color = self.color

    def showEvent(self, event):
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.draw_key(qp)
        qp.end()

    def draw_key(self, qp):
        qp.setPen(QtGui.QPen(QtCore.Qt.black, 0.5, QtCore.Qt.SolidLine))
        qp.setBrush(self.current_color)
        qp.drawRect(0, 0, self.width(), self.height())

    def mouseReleaseEvent(self, event):
        self.parent().done(self.id+1)

    def enterEvent(self, event):
        self.current_color = self.hover_color
        self.update()

    def leaveEvent(self, event):
        self.current_color = self.color
        self.update()

class Piano(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle('Note selector')
        self.keys = []
        self.highlight = None
        for i in range(128):
            key = PianoKey(self, i)
            self.keys.append(key)
        self.setMinimumHeight(key.height())
        self.setMinimumWidth(key.width()*75)

    def exec_(self, highlight=None):
        if self.highlight is not None:
            key = self.keys[self.highlight]
            key.current_color = key.color = key._color
            key.repaint()
            key.update()
        if highlight:
            self.highlight = highlight
            key = self.keys[self.highlight]
            key.current_color = key.color = QtGui.QColor(255, 150, 150)
            key.repaint()
            key.update()
        else:
            self.highlight = None
        return QtGui.QDialog.exec_(self)

class NoLedWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.color = QtGui.QColor(220, 220, 220)

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.draw_me(qp)
        qp.end()

    def draw_me(self, qp):
#        qp.setPen(QtGui.QPen(QtCore.Qt.black, 0.5, QtCore.Qt.SolidLine))
        qp.setBrush(self.color)
        qp.drawRect(2, 2, self.width(), self.height())


class LedWidget(QtGui.QWidget):
    def __init__(self, parent, id):
        QtGui.QWidget.__init__(self, parent)
        self.id = id
        self.setMinimumSize(10, 10)
        self.setMaximumSize(10, 10)
        self.color = QtCore.Qt.green
        self._color = self.current_color = self.color
        self.hover_color = QtCore.Qt.red

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.draw_led(qp)
        qp.end()

    def draw_led(self, qp):
        qp.setPen(QtGui.QPen(QtCore.Qt.black, 0.5, QtCore.Qt.SolidLine))
        qp.setBrush(self.current_color)
        qp.drawRect(2, 2, 6, 6)

    def mouseReleaseEvent(self, event):
        self.parent().done(self.id+1)

    def enterEvent(self, event):
        self.current_color = self.hover_color
        self.update()

    def leaveEvent(self, event):
        self.current_color = self.color
        self.update()


class LedGrid(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle('LED selector')
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)
        self.highlight = None
        self.led_list = []
        for i in range(24):
            led = LedWidget(self, i)
            self.grid.addWidget(led, i/8, divmod(i, 8)[1])
            self.led_list.append(led)
        spacer = QtGui.QWidget()
        spacer.setMinimumWidth(8)
        self.grid.addWidget(spacer, 0, 8)
        for i in range(16):
            led = LedWidget(self, i+24)
            self.grid.addWidget(led, i/8+7, divmod(i, 8)[1])
            self.led_list.append(led)
        for i in range(4):
            led = LedWidget(self, i+40)
            self.grid.addWidget(led, 3+i, 9, 1, 2, QtCore.Qt.AlignHCenter)
            self.led_list.append(led)
        for i in range(4):
            led = LedWidget(self, i+44)
            self.grid.addWidget(led, 1+i/2, divmod(i, 2)[1]+9)
            self.led_list.append(led)
        for i in range(8):
            noled = NoLedWidget(self)
            self.grid.addWidget(noled, 3, i, 4, 1)

    def exec_(self, highlight=None):
        if self.highlight is not None:
            led = self.led_list[self.highlight]
            led.current_color = led.color = led._color
            led.repaint()
            led.update()
        if highlight >= 0:
            self.highlight = highlight
            led = self.led_list[self.highlight]
            led.current_color = led.color = QtGui.QColor(255, 150, 150)
            led.repaint()
            led.update()
        else:
            self.highlight = None
        return QtGui.QDialog.exec_(self)


class SysExDialog(QtGui.QInputDialog):
    def __init__(self, parent):
        QtGui.QInputDialog.__init__(self, parent)
        self.setWindowTitle('Input SysEx')
        self.setLabelText('Enter the full SysEx string:')

    def event(self, event):
        if event.type() == QtCore.QEvent.WindowActivate:
            if not len(self.textValue()):
                self.get_clipboard()
        return QtGui.QInputDialog.event(self, event)

    def get_clipboard(self):
        cb = QtGui.QApplication.clipboard()
        sysex = str(cb.text())
        if len(sysex):
            try:
                sysex = eval(sysex)
                if isinstance(sysex, tuple) or isinstance(sysex, list):
                    sysex = ' '.join('{:02X}'.format(byte) for byte in sysex)
                else:
                    raise
            except:
                try:
                    for byte in sysex.split():
                        try:
                            int(byte, 16)
                        except:
                            raise
                    sysex = ' '.join('{:02X}'.format(int(byte, 16)) for byte in sysex.split())
                except:
                    sysex = ''
                if len(sysex):
                    if not sysex.startswith('F0 '):
                        sysex = 'F0 ' + sysex
                    if not sysex.endswith(' F7'):
                        sysex += ' F7'
            self.setTextValue(sysex)

    def exec_(self, sysex=None):
        if sysex is None:
            self.get_clipboard()
        else:
            self.setTextValue(sysex)
        res = QtGui.QInputDialog.exec_(self)
        if not res:
            return False
        try:
            sysex = []
            for byte in str(self.textValue()).split():
                sysex.append(int(byte, 16))
            return sysex
        except:
            return False





