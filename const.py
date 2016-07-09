import string, re

class ReprConst(object):
    def __init__(self):
        self.name = None
    def get_name(self):
        return [k for k, v in globals().items() if v is self][0]
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

dev_scale = [0x00, 0x10, 0x11, 0x22, 0x23, 0x20, 0x33]
dir_scale = [0x00, 0x01, 0x21, 0x22, 0x32, 0x33]

led_devscale = [x for t in [[a for r in range(21)] for a in dev_scale[1:]] for x in t] + [dev_scale[-1], dev_scale[-1]]
led_dirscale = [x for t in [[a for r in range(25)] for a in dir_scale[1:]] for x in t] + [dir_scale[-1], dir_scale[-1], dir_scale[-1]]

led_scale = [48, 49, 50, 51, 35, 19, 2, 3]
led_fullscale = [x for t in [[a for r in range(16)] for a in led_scale] for x in t]

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
md_replace = dict((re.escape(k), v) for k,  v in md_replace.items())
md_replace_pattern = re.compile('|'.join(r'\b{}\b'.format(k) for k in md_replace.keys()))

patch_colors = (('darkred', 'red'), ('gray', 'black'))

Pass, Ignore, Value, Push, Toggle, Widget, Mode, Ext = (ReprConst() for i in range(8))
ToCtrl, ToNote, ToSysEx = (ReprConst() for i in range(3))
Disabled, Enabled, Triggered = (Const() for i in range(3))
GroupMode, DestMode = (Const() for i in range(2))
MapMode, EditMode, LiveMode = (Const() for i in range(3))
modedict = {'mapping': MapMode, 'editor': EditMode, 'live': LiveMode}

MAPCTRL = 0
