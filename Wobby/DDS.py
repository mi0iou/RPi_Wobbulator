# RPiWobbulator DDS Module
# -*- coding: utf-8 -*-
# vim:ai:sw=4:ts=8:et:fileencoding=utf-8
#
# Copyright (C) 2014 Tom Herbison MI0IOU
# Email tom@asliceofraspberrypi.co.uk
# Web <http://www.asliceofraspberrypi.co.uk>
#
# Copyright (C) 2014 Gray Remlin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""
API Library Module for accessing the MI0IOU RPi Wobbulator board DDS.
These Methods interface to the following device hardware:

*   EIModule (http://www.eimodule.com) Signal Generator Module populated
    with Analogue Devices(tm) AD9850 Direct Digital Synthesizer.
"""

# import GPIO module
import RPi.GPIO as GPIO

from Wobby.lock import Lock as WobbyLock

# Define GPIO pins

# DDS Word Load Clock
_DDS_W_CLK = 15
# DDS Frequency Update
_DDS_FQ_UD = 16
# DDS Data Serial Load Bit
_DDS_DATA = 18
# Master Reset
_DDS_RESET = 22

# DDS crystal oscillator frequency in HZ (assumes 125MHz xtal)
_DDS_XTAL_CLK = 125000000

# program doubleword = frequency * (2^32 / xtal clock)
_DDS_K_FACTOR = (4294967296 / _DDS_XTAL_CLK)

class DDS:

    # Serial Number
    _sernum = 20140707

    # Version 0 Revision 4
    _vernum = 0.4

    # FIXME: specify supported hardware
    # EIModule ADS9850 Signal Generator Module http://www.eimodule.com

    # built-in initialisation method
    def __init__(self):

        print("RPiWobbulator DDS API Library Module Version " +
                                                        str(self._vernum))

        # obtain lock for DDS
        self._lock = WobbyLock('DDS')

        # setup GPIO
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)

        # setup IO bits & initialize to zero
        GPIO.setup(_DDS_W_CLK, GPIO.OUT)
        GPIO.output(_DDS_W_CLK, False)
        GPIO.setup(_DDS_FQ_UD, GPIO.OUT)
        GPIO.output(_DDS_FQ_UD, False)
        GPIO.setup(_DDS_DATA, GPIO.OUT)
        GPIO.output(_DDS_DATA, False)
        GPIO.setup(_DDS_RESET, GPIO.OUT)
        GPIO.output(_DDS_RESET, False)

        self._pulse_high(_DDS_RESET)
        self._pulse_high(_DDS_W_CLK)
        self._pulse_high(_DDS_FQ_UD)

    def version(self):
        """
        Returns the Module API Version & Revision number for identification.
        """
        return self._vernum

    def _pulse_high(self, pin):
        """
        Raise and Lower the defined GPIO pin.

        Internal Method.
        """
        GPIO.output(pin, True)
        GPIO.output(pin, False)
        return

    def _writeb(self, data):
        """
        Write a byte to the AD9850 DDS serially.

        Internal Method.
        """
        for i in range (0, 8):
            GPIO.output(_DDS_DATA, data & 0x01)
            self._pulse_high(_DDS_W_CLK)
            data = data >> 1
        return

    def set_wave(self, freq = 0, phase = 0):
        """
        Program the AD9850 DDS to output the specified wave.
        """
        freq = int(freq * _DDS_K_FACTOR)
        for b in range (0, 4):
            self._writeb(freq & 0xFF)
            freq = freq >> 8
        phase = (phase << 3) & 0xF8
        self._writeb(phase)
        self._pulse_high(_DDS_FQ_UD)
        return

    def powerdown(self):
        """
        Power down the AD9850.
        """
        for b in range (0, 4):
            self._writeb(0)
        self._writeb(0x04)
        self._pulse_high(_DDS_FQ_UD)
        return

    def reset(self):
        """
        Reset the AD9850 DDS registers (disables the output waveform).
        """
        self._pulse_high(_DDS_RESET)
        self._pulse_high(_DDS_W_CLK)
        self._pulse_high(_DDS_FQ_UD)
        return

    def exit(self):
        """
        Shut down the hardware and free all resources.
        """
        self.reset()
        self.powerdown()
        self._lock.release()
        return

def main():
    """
    Execute the built-in API test suite
    
    Command line arguments supported:

    -h/--help           list all options
    -v/--verbose        run tests in verbose mode with output to stdout
    -s/--summary            Module documentation summary
    """
    import os
    import sys
    import tempfile
    import getopt

    _TEMPDIR = os.path.abspath(tempfile.gettempdir())

    verbose = 0

    def usage(code, msg=''):
        if msg:
            print(msg)
        else:
            help(__name__)
        sys.exit(code)

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                    'hvsx', ['help', 'verbose', 'summary'])
    except getopt.GetoptError as err:
        usage(2, err)

    for o, a in opts:
        if o in ('-h', '--help'):
            usage(0)
        elif o in ('-v', '--verbose'):
            verbose += 1
        elif o in ('-s', '--summary'):
            print(__doc__)
        else:
            assert False, "Program Error: unhandled option"

if __name__ == '__main__':
    main()

