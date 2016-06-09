# NoLaE (Novation LaunchControl Editor)
A Linux filter/mapper for Novation LaunchControl


NoLaE is a tool that acts as a filter for Novation LaunchControl XL controllers.
There is no editor for LaunchControl on Linux and, as far as I can tell, if you
don't have a Windows or OSX computer, virtualization won't work with it.

It can work with (possibly) any existing mapping already set on the LC, and,
much more important, it allows you to set custom midi actions for every
controller.

NoLaE uses [mididings](http://das.nasophon.de/mididings/) to interface between
LC and your MIDI devices. Mididings is a powerful MIDI router and processor
based on Python.

Note: at this moment, NoLaE supports only the LaunchControl XL, not the
"standard" one, since I don't own it. If you have it, feel free to contact me
and I might be able to add support for it in the future: the protocol is the
same, so it's enough to know how the controls and leds are mapped.

## Features
- Create up to 16 templates (accessible through the Templates button on LC);
- Configure custom output ports and redirect the output for each controller;
- Set custom LED colors and actions for each controller;
- Graphically group mapped controllers to easily recognize them;

## Requirements
- Python 2.7
- [mididings](http://das.nasophon.de/mididings/)
- Jack Audio Connection Kit (optional, but recommended)

## Usage
NoLaE needs two files to work, a mapping file (*.nlm) and a config one (*.nlc).

### Mapping
The mapping file is necessary to let NoLaE understand to which controller any
incoming MIDI message is assigned to. There is a default.nlm included, which
should be based on the LC factory default.

If you are sure that you never edited the LC using the official editor from
Novation, you should be fine with it, read on if you want to know how to ensure
that it works as expected.

To check the existing default mapping:

    ./launchcontrol.py -M

To edit/check an existing mapping:

    ./launchcontrol.py -Mm _mapfile.nlm_

To start a new mapping use this command:

    ./launchcontrol.py -Mn

The NoLaE window will appear in "mapping mode". If you started NoLaE without an
existing mapping you will see that every controller is "empty".
By now you might use the "automap" function, just press the "Start/Stop" toggle
button on the Mapping panel in the lower right of the window. You will see that
the first knob LED on the LC will start blinking, just rotate it and NoLaE will
assign it; after that the next knob will blink, rotate it and go on.

Once you have set all controllers and buttons, NoLaE will automatically switch
to the next template, if you don't want that, just uncheck the "Continuous"
box.

At any time, you can see the actual result of an already set controller on the
NoLaE window, if you find out that you missed a controller (or moved a wrong
one by mistake), just toggle the "Start/Stop" button, right click on the
controller/button you want to reset and select "Remap". Alternatively, you can
clear the mapping by choosing "Clear". If you press again "Start/Stop" the
mapping will begin from the next not mapped controller.

It is possible to change the current template by selecting it from the NoLaE
buttons in the upper right corner, or using the normal template switching
function on the LC.

When you are done with the mapping, remember to save it.

### Config
To start NoLaE in editor mode, run this command:

    ./launchcontrol.py -E

To use an existing configuration file:

    ./launchcontrol.py -Ec _configfile.nlc_

NoLaE will start, showing an editor window, that has to be used to set the
controllers, enable/disable them, configure the LEDs, etc.

NoLaE has always at least one output port, you can edit the ports using the
panel on the lower right of the window.

The ports can be renamed by double-clicking them. Additionally, you can set
a default input port it will try to connect to on startup. Multiple ports
can be set using commas, the format is ALSA/JACK standard (_device_:_port_)
but regular expressions can be used:
- ```128:2```
- ```LinuxSampler:.*, Amsynth.*```

By default, NoLaE will ignore **every** message received from LC. This is by
choice, to avoid sending unwanted messages to any output device NoLaE is
connected to.

To set a controller just click on it and configure it using the editor window.

The "Destination Port" is one of the outputs set before.

The "Text" will be displayed in the label under the controller (or on the
button); if no text is set, the editor will show a "(set)" text just to let
you know that the controller is enabled.

The "LED" combobox allows you to select to which LED the controller is linked
to, you can use the default one (which is automatically selected) or assign it
to any other led you want.

The "Base color" allows you to choose which color the LED will have on startup.
The values refer to the Novation coloring system. Of course, you can disable
the startup value by selecting the first item (0x00)

The "Action" combo lets you choose what will happen when the controller is
triggered.

The "Pass" action means that NoLaE will use the default "triggered" value, 
which is full red for channels buttons (the last two rows of buttons) and
directional buttons (on the right of the knobs), full yellow for the 4 device
buttons (on the right of the faders); for the knobs you will have shades from
green to red according to the value of the knob (0 is green, 127 is red).

The "Patch" box is used to input standard mididings commands. By default, every
enabled controller has a "Pass" patch, which means that any value received by
the LC for that controller will be transmitted to the selected output port.
You can input almost any mididings patch in there, but remember that they will
work just for the selected Ctrl/Note event received from the selected
controller.

For example, to filter a Ctrl and let pass just values from 30 to 50, you can
type this:

    CtrlValueFilter(30, 50)

To route the incoming MIDI event to the first and second output ports at once,
use this (using this will ignore the "Destination Port" value):

    [Port(1), Port(2)]

Remember that port values start from 1, and you are not allowed to set a port
number greater than the number of existing output ports.

To see the list of available filter and modifiers and learn how they work,
visit the [mididings documentation page](http://dsacre.github.io/mididings/doc/index.html)

There are some ready-to-use utilities that can be selected from the "Templates"
dropdown menu. More will be added in the future.
The patch editor has a simple syntax-check system, and will **try** to guess if
the entered patch is valid or not.

To change the output ports of multiple controllers at once, drag your mouse
while holding the right button pressed to select them, a dialog window will ask
you to which port you want to set them.

The small "eye" button will show at a glimpse the output port and assigned LED
of every enabled controller for the current template.

Groupboxes can be used to graphically group controllers, just drag your mouse
while holding the left button pressed to create a new group, a dialog box will
ask you the name for it. The right click menu for the group will allow you to
rename it, delete it, change its background color or raise/lower it if it
intersects with another group.

Each template can be renamed by double-clicking it.

Once you have finished, just save your configuration file.

### Playing
Well, you are done! :)

To start NoLaE, run:

    ./launchcontrol.py -c _configfile.nlc_

If you have a custom map file, use this:

    ./launchcontrol.py -m _mapfile.nlm_ -c _configfile.nlc_

NoLaE will start up, showing only the enabled controller set in the
configuration file, and will try to connect its output ports to the devices you
set (if you configured any).


##Known issues
NoLaE is still in development, so it **has** bugs. Please, carefully test your
configuration before using it in live performances!
- Default values in the editor window do not always set
- If an output port is removed in the editor and a controller was set to it,
NoLaE will probably crash while saving
- The patch syntax checking system is not very reliable, you could type any
"valid" python expression
- LED default values in the editor window don't always match the actual ones
- Assigning 2 controllers to the same LED will overwrite its value.
