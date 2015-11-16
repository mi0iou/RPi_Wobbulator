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
    with Analogue Devices(tm) AD9850\AD9851 Direct Digital Synthesizer.
"""

# import GPIO module
import RPi.GPIO as GPIO

from Wobby.Lock import Lock as WobbyLock

# Define GPIO pins

# DDS Word Load Clock
_DDS_W_CLK = 15
# DDS Frequency Update
_DDS_FQ_UD = 16
# DDS Data Serial Load Bit
_DDS_DATA = 18
# Master Reset
_DDS_RESET = 22

class DDSException(Exception):
    pass

class DDS:

    # Serial Number
    _sernum = 20140707

    # Version 0 Revision 6
    _vernum = 0.6

    # FIXME: specify supported hardware
    # EIModule ADS9850 Signal Generator Module http://www.eimodule.com
    # ???????? ADS9851 Signal Generator Module

    # AD9851 DDS clock multiplier
    # Default to disabled\no multiplier (AD9850 DDS)
    _dds_mult = 0

    # AD985X System Clock in Hz (Xtal Reference Clock * Multiplier)
    # Default to 125MHz xtal, no clock multiplier (AD9850 DDS)
    _dds_sys_clk = 125000000

    # program doubleword = frequency * (2^32 / system clock)
    _dds_k_factor = (4294967296 / _dds_sys_clk)

    # built-in initialisation method
    def __init__(self):

        print("RPiWobbulator DDS API Library Module Version " +
                                                        str(self._vernum))

        # obtain lock for DDS
        self._lock = WobbyLock('DDS')

        # setup GPIO
        print("Using installed GPIO version " + str(GPIO.VERSION))

        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)

        # setup IO bits & initialize to zero
        dds_gpio = [_DDS_W_CLK, _DDS_FQ_UD, _DDS_DATA, _DDS_RESET]
        GPIO.setup(dds_gpio, GPIO.OUT, initial = GPIO.LOW)

        # Ensure DDS in sane state and put to sleep
        self.reset()
        self.powerdown()

        # Default to AD9850 DDS (125MHz xtal, no multiplier)
        self.set_sysclk(125000000, 0)

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
        GPIO.output(pin, GPIO.HIGH)
        GPIO.output(pin, GPIO.LOW)
        return

    def _writeb(self, data):
        """
        Write a byte to the AD985X DDS serially.

        Internal Method.
        """
        for i in range (0, 8):
            GPIO.output(_DDS_DATA, data & 0x01)
            self._pulse_high(_DDS_W_CLK)
            data = data >> 1
        return

    def set_wave(self, freq = 0, phase = 0):
        """
        Program the AD985X DDS to output the specified frequency.
        """
        freq = int(freq * self._dds_k_factor)
        for b in range (0, 4):
            self._writeb(freq & 0xFF)
            freq = freq >> 8
        phase = (phase << 3) & 0xF8
        # AD9850 NOTE: the two least significant bits MUST ALWAYS be zero
        # AD9851 set the reference clock multiplier, bit 0 (30MHz x 6)
        phase = phase | self._dds_mult
        self._writeb(phase)
        self._pulse_high(_DDS_FQ_UD)
        return

    def set_sysclk(self, refclk = 125000000, mult = 0):
        """
        Calculate\store AD985X System Clock, Multiplier flag & related parameters.
        """
        self._dds_mult = mult
        if self._dds_mult == 0:
            self._dds_sys_clk = refclk
        elif self._dds_mult == 1:
            self._dds_sys_clk = refclk * 6
        else:
            self.exit()
            raise DDSException("Parameter 2 (multiplier flag) out of range")

        self._dds_k_factor = (4294967296 / self._dds_sys_clk)
        return

    def maxfreq(self):
        """
        Return maximum frequency capability (square wave output).
        """
        return int(self._dds_sys_clk / 2)

    def powerdown(self):
        """
        Power down the AD985X.
        """
        for b in range (0, 4):
            self._writeb(0)
        self._writeb(0x04)
        self._pulse_high(_DDS_FQ_UD)
        return

    def reset(self):
        """
        Reset the AD985X DDS registers (disables the output waveform).
        """
        self._pulse_high(_DDS_RESET)
        self._pulse_high(_DDS_W_CLK)
        self._pulse_high(_DDS_FQ_UD)
        return

    def exit(self):
        """
        Shut down the hardware and free all resources.

        Ensure this function is always invoked at program exit under all conditions.
        """
        self.reset()
        self.powerdown()
        GPIO.cleanup()
        self._lock.release()
        print("RPiWobbulator DDS API Library Module exiting")
        return

def main():
    """
    Execute the built-in API test suite
    
    Command line arguments supported:

    -h/--help           list all options
    -v/--verbose        run tests in verbose mode with output to stdout
    -s/--summary        Module documentation summary
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

