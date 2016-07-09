from PyQt4 import QtCore, QtGui
from const import str_allowed, dev_scale, dir_scale, md_replace, md_replace_pattern
import mididings as md
import re

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
    def Template(t):
        return
    def TemplateNext():
        return
    def TemplatePrev():
        return
    try:
        patch = md_replace_pattern.sub(lambda m: md_replace[re.escape(m.group(0))], patch)
        eval(patch)
        return True
    except:
        return False

def patch_parse(patch, event, template, out_ports):
    def Template(t):
        t = t-1
        if t < 0: t = 0
        if t > 15: t = 15
        return md.SysEx(out_ports+1, [0xF0, 0x00, 0x20, 0x29, 0x02, 0x11, 0x77, t, 0xF7])
    def TemplateNext():
        return Template(template+2 if template<15 else 0)
    def TemplatePrev():
        return Template(template if template>1 else 15)
    try:
        return eval(patch)
    except:
        return md.Pass()


