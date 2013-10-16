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

