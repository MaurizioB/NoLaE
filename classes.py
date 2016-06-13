import mididings as md
from PyQt4 import QtCore, QtGui
from const import *
from utils import *
from copy import copy


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

    def __repr__(self):
        if isinstance(self.name, int):
            if self.id >= 8:
                return 'Factory {}'.format(self.id-7)
            else:
                return 'User {}'.format(self.id+1)
        return self.name


class Router(QtCore.QThread):
    template_change = QtCore.pyqtSignal(int)
    midi_signal = QtCore.pyqtSignal(object)

    def __init__(self, main, mapping=False, backend='alsa'):
        QtCore.QThread.__init__(self)
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
            backend = self.backend,
            client_name='LCGate',
            in_ports = [
                ('LC_input', 'Launch.*'), 
                        ],
            out_ports = self.out_ports + [('LC_output', 'Launch.*')],
            )
        self.already_set = True

    def run(self):
        print 'mididings thread started'
        if not self.already_set:
            self.setup()
        if self.mapping:
            md.run(md.Call(self.event_mapping))
        else:
            md.run(scenes=self.scenes, control=md.Call(self.event_call))
        print 'mididing thread ended (?)'

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
            while md.engine.active():
                pass
        print 'mididings engine is now: {}'.format('active' if md.engine.active() else 'not active')
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
