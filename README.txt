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

UPDATE v2.2

Edits by Tony Abbey for optional screen clear feature after every sweep and incorporation
of code suggested by Fred LaPlante for a "scope-like" trace. Implementation of "Fast"
option to run the ADC chip at full speed and 12 Bit resolution. Code was also modified
so that display "Grid" is on by default when the software is run.

UPDATE v2.3
Frequency and Volt labels added by Fred LaPlante

UPDATE v2.4
X and Y Scales added by Tony Abbey

UPDATE v2.42
Improved screen clarity by Richard Smith

UPDATE v2.50
Sweep settings saved in a paramater file by Fred LaPlante

UPDATE v2.51
Performance tweaks by Tony Abbey

UPDATE v2.52
Menus added by Fred LaPlante

UPDATE v2.53
K(Hz) and M(Hz) conversion added by Dick Bronsdijk

UPDATE v2.54
Display corrections and code cleanup by Dick Bronsdijk

UPDATE v2.55
Display tweaks and cleanup by Tony Abbey

UPDATE v2.56
Vertical text on Y scale and related tweaks by Tony Abbey

UPDATE v2.57
All paramaters now saved and restiored by Dick Bronsdijk

UPDATE v2.58
User description panel added by Fred LaPlante

UPDATE v2.59
Single sweep button added by Dick Bronsdijk

UPDATE v2.60
Added dBm button to change yscale to dBm by Tony Abbey.
This requires subtracting the offset - now an average of 2 readings to make it as
accurate as possible. Tried making this automatic in the dB code, but line doesnt
work so is commented out - click on manually.
Changed getadcreading to include the changechannel function so one call triggers adc
and gets reading. Also changes Ydivs to 25 for a sensible scale in dB.
Scale is based on 20mV/dB and a minimum level of -75dBm.

UPDATE v2.61
Bias option automatically selected when dBm scale is selected

UPDATE v2.62
Previous change of Ydivs to 25 when DBm selected disabled because it caused grid display issues

UPDATE v2.63
Y scale automatically updates when dBm option is selected

UPDATE v2.64
Recent changes consolidated and code tidied up

UPDATE v2.65
Scaling changes to represent ADC range better and remove some old change comments - Tony (afa)

UPDATE v2.66
Auto linear scale for ch 1, and optional lin/log for ch 2 - Tony

UPDATE v2.70
"Fast" option removed and replaced with set of 4 radio buttons which allow the user to set the ADC
at 3.75SPS 18Bit, 15SPS 16Bit, 60SPS 14Bit or 240SPS 12Bit - Tom


