import re
from math import pow, log, log10
from PyQt4 import QtCore, QtGui
#from const import str_allowed, dev_scale, dir_scale, md_replace, md_replace_pattern
from const import *
import mididings as md
from _mididings import Engine as mdEngineClass
from mididings import engine as mdEngine
from mididings.extra.osc import SendOSC

def MsgHandler(level, msg):
    print msg

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
    if template < 8:
        return ('User', template+1)
    else:
        return ('Factory', template-7)

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

def patch_validate(patch):
    def Macro(*args):
        try:
            [(int(w), v if isinstance(v, ReprConst) else int(v)) for w, v, m in args]
            return md.Pass()
        except:
            raise TypeError
    def Template(t):
        if not isinstance(t, int) or not 1<=t<=16:
            raise ValueError
        return md.Pass()
    def TemplateNext():
        return md.Pass()
    def TemplatePrev():
        return md.Pass()
    try:
        patch = md_replace_pattern.sub(lambda m: md_replace[re.escape(m.group(0))], patch)
        eval(patch)
        return True
    except:
        return False

def localEvent(event=None, midi_event=None):
    #event is ignored
    res = mdEngineClass.process_event(mdEngine._TheEngine(), midi_event)
    for cmd in res:
        mdEngineClass.output_event(mdEngine._TheEngine(), cmd)
