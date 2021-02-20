import string, re
from PyQt5 import QtCore

class ReprConst(object):
    def __init__(self, id=None):
        self.name = None
        self.id = id
    def get_name(self):
        return [k for k, v in list(globals().items()) if v is self][0]
#    def __int__(self):
#        return self.id
    def __str__(self):
        if not self.name:
            self.name = self.get_name()
        return self.name
    def __repr__(self):
        if not self.name:
            self.name = self.get_name()
        return self.name

class Const(object):
    pass

def value_assign_wrapper(id):
    def func(value, mode=None):
        return id, value, mode
    return func

for r, r_name in enumerate(['SendA', 'SendB', 'Pan', 'Fader', 'Focus', 'Control']):
    for c in range(8):
        globals()['{}_{}'.format(r_name, c+1)] = value_assign_wrapper(r*8+c)
Device, Mute, Solo, Record, SendUp, SendDown, TrackLeft, TrackRight = [value_assign_wrapper(id) for id in range(48, 56)]
Index, Reset, Prev, Next = (ReprConst() for i in range(4))
FullColors, DevColors, DirColors = (ReprConst(i) for i in range(3))
Press = 1
Release = 2
PressRelease = 3
UserRole = QtCore.Qt.UserRole
ScaleRole = UserRole + 1
LedRole = UserRole + 1
LedFlashRole = LedRole + 1
LedPixmapRole = LedFlashRole + 1
LedFlashPixmapRole = LedPixmapRole + 1

sysex_init_lc = bytearray([240, 0, 32, 41, 2, 17])

#led scales!
def get_fullscale(base, copy = True):
    copy = 4 if copy else 0
    scale = []
    div = 128//(len(base))
    for value in base:
        scale.extend([value+copy for x in range(div)])
    while len(scale) < 128:
        scale.append(base[-1])
    return scale

full_scale = [0x30, 0x31, 0x32, 0x33, 0x23, 0x13, 0x02, 0x03]
full_revscale = list(reversed(full_scale))
full_mirrorscale = [full_scale[0]] + full_scale + full_revscale[1:]
full_mirrorrevscale = [full_revscale[0]] + full_revscale + full_scale[1:]
full_volscale = [0x10, 0x10, 0x10, 0x20, 0x20, 0x20, 0x30, 0x30, 0x30, 0x30, 0x31, 0x32, 0x33, 0x23, 0x13, 0x03]

#led_devscale = [x for t in [[a for r in range(21)] for a in dev_scale[1:]] for x in t] + [dev_scale[-1], dev_scale[-1]]
led_full_scale = get_fullscale(full_scale)
led_full_revscale = get_fullscale(full_revscale)
led_full_mirrorscale = get_fullscale(full_mirrorscale)
led_full_mirrorrevscale = get_fullscale(full_mirrorrevscale)
led_full_volscale = get_fullscale(full_volscale)
led_full_scale_list = [led_full_scale, led_full_revscale, led_full_mirrorscale, led_full_mirrorrevscale, led_full_volscale]

dev_scale = [0x10, 0x11, 0x22, 0x23, 0x20, 0x33]
dev_revscale = list(reversed(dev_scale))
dev_mirrorscale = dev_scale + dev_revscale[1:]
dev_mirrorrevscale = dev_revscale + dev_scale[1:]
dev_volscale = [0x10, 0x10, 0x10, 0x22, 0x22, 0x23, 0x20, 0x33]

led_dev_scale = get_fullscale(dev_scale)
led_dev_revscale = get_fullscale(dev_revscale)
led_dev_mirrorscale = get_fullscale(dev_mirrorscale)
led_dev_mirrorrevscale = get_fullscale(dev_mirrorrevscale)
led_dev_volscale = get_fullscale(dev_volscale)
led_dev_scale_list = [led_dev_scale, led_dev_revscale, led_dev_mirrorscale, led_dev_mirrorrevscale, led_dev_volscale]

dev_scale_conv = {0x22: 0x13, 0x23: 0x21, 0x20: 0x32}
#for scale in [dev_scale, dev_revscale, dev_mirrorscale, dev_mirrorrevscale, dev_volscale]:
#    for i, value in enumerate(scale):
#        if value in dev_scale_conv.keys():
#            scale[i] = dev_scale_conv[value]

dir_scale = [0x01, 0x21, 0x22, 0x32, 0x33]
dir_revscale = list(reversed(dir_scale))
dir_mirrorscale = dir_scale + dir_revscale[1:]
dir_mirrorrevscale = dir_revscale + dir_scale[1:]
dir_volscale = [0x01, 0x01, 0x01, 0x21, 0x21, 0x22, 0x32, 0x33]

led_dir_scale = get_fullscale(dir_scale)
led_dir_revscale = get_fullscale(dir_revscale)
led_dir_mirrorscale = get_fullscale(dir_mirrorscale)
led_dir_mirrorrevscale = get_fullscale(dir_mirrorrevscale)
led_dir_volscale = get_fullscale(dir_volscale)
led_dir_scale_list = [led_dir_scale, led_dir_revscale, led_dir_mirrorscale, led_dir_mirrorrevscale, led_dir_volscale]

led_fallback_list = [0x10, 0x20, 0x30, 0x11, 0x21, 0x31, 0x32, 0x33, 0x22, 0x23, 0x13, 0x12, 0x01, 0x02, 0x03]
dev_factor = len(dev_scale)/float(len(led_fallback_list))
dir_factor = len(dir_scale)/float(len(led_fallback_list))
dev_fallback = {0: 0}
dir_fallback = {0: 0}
for i in range(len(led_fallback_list)):
    dev_fallback[led_fallback_list[i]] = dev_scale[int(i*dev_factor)]
    dir_fallback[led_fallback_list[i]] = dir_scale[int(i*dir_factor)]

dev_scale.insert(0, 0x00)
dir_scale.insert(0, 0x00)

led_scale_types_simple = {
                   FullColors: full_scale, 
                   DevColors: dev_scale[1:], 
                   DirColors: dir_scale[1:], 
                   }

led_scale_types_full = {
                        FullColors: led_full_scale_list, 
                        DevColors: led_dev_scale_list, 
                        DirColors: led_dir_scale_list, 
                        }

row_heights = {0: 80, 1: 80, 2: 80, 3: 160, 4: 40, 5: 40}
str_allowed = set(string.ascii_letters+string.digits+'.'+' ')

#TODO Split is missing, update function with regex
#md_replace = ('Ctrl', 'Port', 'Channel', 'Velocity', 
#           'Note', 'Pitchbend', 'Aftertouch', 'Program', 'Generator', 
#           'event.MidiEvent', 'event.SysExEvent', 'engine.output_event', 
#           'extra.Harmonize', 'LimitPolyphony', 'MakeMonophonic', 'LatchNotes', 'Panic', 
#           'Discard', 'Pass', 'Sanitize', 'Print', 'Process', 'Call', 
#           'EVENT_DATA1', 'EVENT_DATA2', 
#           )

md_base = '''Filter, PortFilter, ChannelFilter, KeyFilter, VelocityFilter, CtrlFilter, CtrlValueFilter, SysExFilter, 
                        Split, ChannelSplit, KeySplit, VelocitySplit, CtrlSplit, CtrlValueSplit, SysExSplit, 
                        Port, Channel, Transpose, Key, Velocity, VelocitySlope, VelocityLimit, CtrlMap, CtrlRange, CtrlCurve,
                        NoteOn, NoteOff, Ctrl, Pitchbend, Aftertouch, PolyAftertouch, Program, SysEx, Generator, 
                        Process, Call, System, SceneSwitch, SubSceneSwitch, Init, Exit, Output, 
                        Print, Pass, Discard, Sanitize, 
                        EVENT_CHANNEL, EVENT_CTRL, EVENT_DATA1, EVENT_DATA2, EVENT_NOTE, EVENT_PROGRAM, EVENT_VALUE, EVENT_VELOCITY'''
md_event = '''AftertouchEvent, CtrlEvent, MidiEvent, NoteOffEvent, NoteOnEvent, PitchbendEvent, PolyAftertouchEvent, ProgramEvent, SysExEvent'''
md_extra = '''Harmonize, LimitPolyphony, MakeMonophonic, LatchNotes, CtrlToSysEx, Panic'''
md_engine = '''current_scene, output_event, in_ports, out_ports, time'''
md_replace = {}
md_replace.update({k:'md.{}'.format(k) for k in md_base.replace(',', '').split()})
md_replace.update({k:'md.event.{}'.format(k) for k in md_event.replace(',', '').split()})
md_replace.update({k:'md.extra.{}'.format(k) for k in md_extra.replace(',', '').split()})
md_replace.update({k:'md.engine.{}'.format(k) for k in md_engine.replace(',', '').split()})
#md_replace['SendOSC'] = 'md.extra.osc.SendOSC'
md_replace = dict((re.escape(k), v) for k,  v in list(md_replace.items()))
md_replace_pattern = re.compile('|'.join(r'\b{}\b'.format(k) for k in list(md_replace.keys())))

patch_colors = (('darkred', 'red'), ('gray', 'black'))

Pass, Ignore, Value, Push, Toggle, Widget, Mode, Ext = (ReprConst() for i in range(8))
ToCtrl, ToNote, ToSysEx = (ReprConst() for i in range(3))
Disabled, Enabled, Triggered = (Const() for i in range(3))
GroupMode, DestMode = (Const() for i in range(2))
MapMode, EditMode, LiveMode = (Const() for i in range(3))
modedict = {'mapping': MapMode, 'editor': EditMode, 'live': LiveMode}

NumKeys = [getattr(QtCore.Qt, 'Key_{}'.format(i)) for i in range(10)]

MAPCTRL = 0
