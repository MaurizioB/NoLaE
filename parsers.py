#from mididings import (Filter, PortFilter, ChannelFilter, KeyFilter, VelocityFilter, CtrlFilter, CtrlValueFilter, SysExFilter, 
#                        Split, ChannelSplit, KeySplit, VelocitySplit, CtrlSplit, CtrlValueSplit, SysExSplit, 
#                        Port, Channel, Transpose, Key, Velocity, VelocitySlope, VelocityLimit, CtrlMap, CtrlRange, CtrlCurve,
#                        NoteOn, NoteOff, Ctrl, Pitchbend, Aftertouch, PolyAftertouch, Program, SysEx, Generator, 
#                        Process, Call, System, SceneSwitch, SubSceneSwitch, Init, Exit, Output, 
#                        Print, Pass, Discard, Sanitize, 
#                        EVENT_CHANNEL, EVENT_CTRL, EVENT_DATA1, EVENT_DATA2, EVENT_NOTE, EVENT_PROGRAM, EVENT_VALUE, EVENT_VELOCITY
#                        )
#from mididings.event import *
#from mididings.extra import Harmonize, LimitPolyphony, MakeMonophonic, LatchNotes, CtrlToSysEx, Panic

def patch_validate(patch):
    from mididings import (Filter, PortFilter, ChannelFilter, KeyFilter, VelocityFilter, CtrlFilter, CtrlValueFilter, SysExFilter, 
                        Split, ChannelSplit, KeySplit, VelocitySplit, CtrlSplit, CtrlValueSplit, SysExSplit, 
                        Port, Channel, Transpose, Key, Velocity, VelocitySlope, VelocityLimit, CtrlMap, CtrlRange, CtrlCurve,
                        NoteOn, NoteOff, Ctrl, Pitchbend, Aftertouch, PolyAftertouch, Program, SysEx, Generator, 
                        Process, Call, System, SceneSwitch, SubSceneSwitch, Init, Exit, Output, 
                        Print, Pass, Discard, Sanitize, 
                        EVENT_CHANNEL, EVENT_CTRL, EVENT_DATA1, EVENT_DATA2, EVENT_NOTE, EVENT_PROGRAM, EVENT_VALUE, EVENT_VELOCITY
                        )
    from mididings.event import AftertouchEvent, CtrlEvent, MidiEvent, NoteOffEvent, NoteOnEvent, PitchbendEvent, PolyAftertouchEvent, ProgramEvent, SysExEvent
    from mididings.extra import Harmonize, LimitPolyphony, MakeMonophonic, LatchNotes, CtrlToSysEx, Panic
    def Template(t):
        return
    def TemplateNext():
        return
    def TemplatePrev():
        return
    try:
        eval(patch)
        return True
    except:
        return False

def patch_parse(patch, event, template, out_ports):
    from mididings import (Filter, PortFilter, ChannelFilter, KeyFilter, VelocityFilter, CtrlFilter, CtrlValueFilter, SysExFilter, 
                        Split, ChannelSplit, KeySplit, VelocitySplit, CtrlSplit, CtrlValueSplit, SysExSplit, 
                        Port, Channel, Transpose, Key, Velocity, VelocitySlope, VelocityLimit, CtrlMap, CtrlRange, CtrlCurve,
                        NoteOn, NoteOff, Ctrl, Pitchbend, Aftertouch, PolyAftertouch, Program, SysEx, Generator, 
                        Process, Call, System, SceneSwitch, SubSceneSwitch, Init, Exit, Output, 
                        Print, Pass, Discard, Sanitize, 
                        EVENT_CHANNEL, EVENT_CTRL, EVENT_DATA1, EVENT_DATA2, EVENT_NOTE, EVENT_PROGRAM, EVENT_VALUE, EVENT_VELOCITY
                        )
    from mididings.event import AftertouchEvent, CtrlEvent, MidiEvent, NoteOffEvent, NoteOnEvent, PitchbendEvent, PolyAftertouchEvent, ProgramEvent, SysExEvent
    from mididings.extra import Harmonize, LimitPolyphony, MakeMonophonic, LatchNotes, CtrlToSysEx, Panic
    def Template(t):
        t = t-1
        if t < 0: t = 0
        if t > 15: t = 15
        return SysEx(out_ports+1, [0xF0, 0x00, 0x20, 0x29, 0x02, 0x11, 0x77, t, 0xF7])
    def TemplateNext():
        return Template(template+2 if template<15 else 0)
    def TemplatePrev():
        return Template(template if template>1 else 15)
#    patch = patch.replace('TemplateNext()', Template(template+1 if template<15 else 0))
#    patch = patch.replace('TemplatePrev()', Template(template-1 if template>1 else 15))
#    patch = patch.replace('Template(')
    try:
        return eval(patch)
    except:
        return Pass()




























































































