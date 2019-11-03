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
    print(msg)

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

def set_led(template=0, *raw_led_list):
    sysex_string = [0xF0, 0x00, 0x20, 0x29, 0x02, 0x11, 0x78, template]
    led_list = []
    for id, value in raw_led_list:
        if value > 63:
            flash = (value >> 6) - 1
            value &= 63
            led_list.append((id, value|4, id, flash))
        else:
            led_list.append((id, value|4))
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

def get_led_type(id):
    if id < 0:
        return None
    if id < 40:
        return FullColors
    if id < 44:
        return DevColors
    return DirColors

def get_pixmap(red=0, green=0):
    pixmap = QtGui.QPixmap(8, 8)
    color = QtGui.QColor()
    color.setRgb(red, green, 0)
    pixmap.fill(color)
    return pixmap

def get_dev_pixmap():
    pass

def scale_full_pixmap(scale):
    pixmap = QtGui.QPixmap(64, 16)
    col_width = 64/len(scale)
    painter = QtGui.QPainter(pixmap)
    for i, color in enumerate(scale):
        red = color & 3
        green = color >> 4
        brush = QtGui.QBrush(QtGui.QColor(red*85, green*85, 0))
        painter.fillRect(QtCore.QRectF(i*col_width, 0, col_width, 16), brush)
    return pixmap

def scale_dev_pixmap(scale):
    pixmap = QtGui.QPixmap(64, 16)
    col_width = 64./len(scale)
    painter = QtGui.QPainter(pixmap)
    for i, color in enumerate(scale):
        if color in dev_scale_conv:
            color = dev_scale_conv[color]
        red = color & 3
        green = color >> 4
        mix = red+green
        brush = QtGui.QBrush(QtGui.QColor(mix*42, mix*42, 0))
        painter.fillRect(QtCore.QRectF(i*col_width, 0, col_width, 16), brush)
    return pixmap

def scale_dir_pixmap(scale):
    pixmap = QtGui.QPixmap(64, 16)
    col_width = 64./len(scale)
    painter = QtGui.QPainter(pixmap)
    for i, color in enumerate(scale):
        red = color & 3
        green = color >> 4
        mix = red+green
        brush = QtGui.QBrush(QtGui.QColor(mix*42, 0, 0))
        painter.fillRect(QtCore.QRectF(i*col_width, 0, col_width, 16), brush)
    return pixmap

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

def findIndex(model, value, role=UserRole):
    rows = model.rowCount()
    for c in range(model.columnCount()):
        for r in range(rows):
            item = model.item(c, r)
            if item.data(role).toPyObject() == value:
                return model.indexFromItem(item)
    return None











