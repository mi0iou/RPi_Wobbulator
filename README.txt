RPI Wobulator

A wobbulator (or sweep generator) is a piece of test equipment which
is used in conjunction with an Oscilloscope to measure the frequency
response characteristics of a circuit. It uses a “ramp” or “sawtooth”
function generator connected to a Voltage Controlled Oscillator (VCO)
to produce an output sweep over a defined range of frequencies. The
response characteristics of the circuit under test can then be
displayed on an Oscilloscope. A wobbulator is a useful tool for
aligning the intermediate frequency (IF) stages of superhet receivers,
but can also be used to measure the frequency response characteristics
of RF filters and other circuits.

The RPI Wobbulator software implements the functionality of a
conventional wobbulator by using a Raspberry Pi, a Direct Digital
Synthesiser (DDS) module and an Analogue to Digital Converter (ADC)
module. The Raspberry Pi’s General Purpose Input Output (GPIO)
interface is programmed to control the DDS module to generate the
frequency sweep and to communicate with the ADC module to measure the
response of the circuit under test. The Graphical User Interface (GUI)
allows the user to choose the parameters for the frequency sweep and
also displays the results.

For full details please visit:

<http://www.asliceofraspberrypi.co.uk>

UPDATE v1.1

The RPI Wobbulator hardware has been developed and revised to use an
onboard ADC chip instead of a separate ADC modules. This has reduced
the number of input channels available from 8 to 4.The software has been
revised accordingly.

An additional user selectable "Bias" feature has been added to the GUI
which allows the user to choose whether or not to compensate for any bias
on the output signal from the detector stage.

UPDATE v2.0

Edits by Tony Abbey for >10 speed-up and continuous looping until STOP button pressed.
ADC now runs at 60 SPS and 14 bits in one-shot mode
Also added initialisation of frequency scan value

UPDATE v2.1

Code was modified to clear the display between each cycle of the frequency sweep,
thus emulating the behaviour of a conventional wobbulator more closely. This
should make the software more useful when it is used to adjust tunable filters.
Other minor changes included deleting of debugging code used to display status
of various variables on the console window during execution. Default frequency
sweep paramaters were also changed.

