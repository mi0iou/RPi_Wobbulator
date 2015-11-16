# RPiWobbulator ADC Module
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
API Library Module for accessing the MI0IOU RPi Wobbulator board ADC.
These Methods interface to the following device hardware:

*   MCP3424 18-Bit, Multi-Channel Analog-to-Digital Converter,
    with I2C Interface and On-Board Reference.
"""

#import quick2wire i2c module
import quick2wire.i2c as i2c

from Wobby.Lock import Lock as WobbyLock

_PROGRAM_ERROR_MESSAGE = 'A Program Error has occurred, please report this bug'

class ADC:

    # Serial Number
    _sernum = 20140701

    # Version 0 Revision 5
    _vernum = 0.5

    # FIXME: report supported hardware
    """
    MCP3424 18-Bit, Multi-Channel Analog-to-Digital Converter
    with I2C Interface and On-Board Reference.
    """

    # Configuration Contol Byte Bit Mappings

    # PGA Gain Bits 0-1
    """
    # FIXME: use me or loose me
    _ADC_GAIN_1 = 0
    _ADC_GAIN_2 = 1
    _ADC_GAIN_4 = 2
    _ADC_GAIN_8 = 3
    """
    _mapgain = { 1:0, 2:1, 4:2, 8:3, }


    # Bit Resolution\Samples Per Second Bits 2-3
    # 12 bits : 240 SPS  : 4.16 nS
    # 14 bits : 60 SPS   : 16.66 nS
    # 16 bits : 15 SPS   : 66.66 nS
    # 18 bits : 3.75 SPS : 266.66 nS

    """
    # FIXME: use me or loose me
    _ADC_BITRES_12 = 0
    _ADC_BITRES_14 = 4
    _ADC_BITRES_16 = 8
    _ADC_BITRES_18 = 12
    """
    _mapbitres = { 12:0, 14:4, 16:8, 18:12, }
    _mapbitreswait = { 12:1, 14:12, 16:55, 18:237, }

    """
    # FIXME: use me or loose me
    _ADC_SPS_240 = 0
    _ADC_SPS_60 = 4
    _ADC_SPS_15 = 8
    _ADC_SPS_3_75 = 12
    """
    _mapsps = { 240:0, 60:4, 15:8, 3.75:12, }
    _mapspswait = { 240:1, 60:12, 15:55, 3.75:237, }

    # Continuous Conversion Bit 4 
    _ADC_CC = 16
    _mapcontconv = { 0:0, 1:16, }

    # MUX Input Channel Selection Bits 5-6
    """
    # FIXME: use me or loose me
    _ADC_IPCHAN_1 = 0
    _ADC_IPCHAN_2 = 32
    _ADC_IPCHAN_3 = 64
    _ADC_IPCHAN_4 = 96
    """
    _mapipchan = { 1:0, 2:32, 3:64, 4:96, }

    # ADC READY Control Bit 7
    _ADC_RDY = 128


    # Parameter Storage (set to defaults)
    
    # I2C address of ADC chip
    _adc_address = 0x68

    _adc_gain = 1
    
    _adc_bitres = 18

    _adc_sps = 0

    _adc_contconv = 0
    
    _adc_ipchan = 1

    _adc_config = 0 + 12 + 0 + 0 + 128

    _adc_delay = 235

    _callback = ()

    _callback_id = None

    _master = None

    def __init__(self, master = None):
        """Prepare to perform hardware access."""

        print("RPiWobbulator ADC API Library Module Version " + 
                                                        str(self._vernum))

        self._master = master

        # obtain lock for ADC
        self._lock = WobbyLock('ADC')

        # prepare i2c bus
        self._bus = i2c.I2CMaster()

    def version(self):
        """
        Returns the Module API Version & Revision number for identification.

        Return: float value
        """
        return self._vernum

    def _config_update(self):
        """
        Update the configuration byte to be used during ADC conversion.

        Return: nothing

        This is an internal method, used to convert and combine the separate
        conversion parameters into the configuration byte value.
        """
        gain = self._mapgain[self._adc_gain]
        # Either\Or, zero indicates the unused option
        if self._adc_bitres:
            sps_bitres = self._mapbitres[self._adc_bitres]
            if self._adc_sps:
                raise Exception(_PROGRAM_ERROR_MESSAGE)
        elif self._adc_sps:
            sps_bitres = self._mapsps[self._adc_sps]
            if self._adc_bitres:
                raise Exception(_PROGRAM_ERROR_MESSAGE)
        else:
            raise Exception(_PROGRAM_ERROR_MESSAGE)

        contconv = self._mapcontconv[self._adc_contconv]
        ipchan = self._mapipchan[self._adc_ipchan]
        self._adc_config = gain + sps_bitres + contconv + ipchan + self._ADC_RDY
        return

    def set_gain(self, gain):
        """
        Set the 'Amplifier Gain' to be used during ADC conversion.

        Valid argument values: 1, 2, 4, 8
        Return: nothing
        """
        if self._adc_gain != gain:
            if gain not in self._mapgain.keys():
                raise ValueError('Invalid argument:{} not in {}'.format(
                                                gain, self._mapgain.keys()))
            self._adc_gain = gain
            self._config_update()
        return

    def set_bitres(self, bitres):
        """
        Set the 'Bit Resolution' to be used during ADC conversion.

        Valid argument values: 12, 14, 16, 18
        Return: nothing

        This is an alternative to specifying the 'Samples per Second'.
        """
        if self._adc_bitres != bitres:
            if bitres not in self._mapbitres.keys():
                raise ValueError('Invalid argument:{} not in {}'.format(
                                            bitres, self._mapbitres.keys()))
            self._adc_bitres = bitres
            self._adc_delay = self._mapbitreswait[self._adc_bitres]
            self._adc_sps = 0
            self._config_update()
        return

    def set_sps(self, sps):
        """
        Set the 'Samples per Second' to be used during ADC conversion.

        Valid argument values: 3.75, 15, 60, 240
        Return: nothing

        This is an alternative to specifying the 'Bit Resolution'.
        """
        if self._adc_sps != sps:
            if sps not in self._mapsps.keys():
                raise ValueError('Invalid argument:{} not in {}'.format(
                                                    sps, self._mapsps.keys()))
            self._adc_sps = sps
            self._adc_delay = self._mapspswait[self._adc_sps]
            self._adc_bitres = 0
            self._config_update()
        return

    def set_contconv(self, contconv):
        """
        Set or Clear the 'continuous flag'to be used during ADC conversion.
        If clear, on a 'read' the ADC will perform one conversion and stop, if
        set, the ADC repeatedly performs conversions until explicitly stopped.

        Valid argument values: 0, or !0
        Return: nothing
        """
        if contconv:
            if self._adc_contconv != 1:
                self._adc_contconv = 1
                self._config_update()
        else:
            if self._adc_contconv != 0:
                self._adc_contconv = 0
                self._config_update()
        return

    def set_ipchan(self, ipchan):
        """
        Set the 'Input Channel' to be used during ADC conversion.
       
        Valid argument values: 1, 2, 3, 4
        Return: nothing
        """
        if self._adc_ipchan != ipchan:
            if ipchan not in self._mapipchan.keys():
                raise ValueError('Invalid argument:{} not in {}'.format(
                                            ipchan, self._mapipchan.keys()))
            self._adc_ipchan = ipchan
            self._config_update()
        return

    def get_config(self):
        """
        Directly read the ADC local configuration byte variable.

        Return: Byte value
        """
        return self._adc_config
        
    def set_config(self, adc_config):
        """
        Directly write the ADC local configuration byte variable.
        
        Valid argument values: 1 Byte

        This Method deconstructs the configuration byte and sets the related
        local variable configuration parameters accordingly. This ensures that
        later calling of a set_XXX() Method does not generate crud.
        """
        self._adc_config = (adc_config & 0xFF)

        # gain bits 0-1
        gain = (adc_config & 0x03)
        for key, val in self._mapgain.items():
            if val == gain:
                self._adc_gain = key
                break

        # bits resolution\samples per second bits 2-3
        bitres = (adc_config & 0x0C)
        # set bitres (or sps but not both)
        self._adc_sps = 0
        for key, val in self._mapbitres.items():
            if val == bitres:
                self._adc_bitres = key
                self._adc_delay = self._mapbitreswait[self._adc_bitres]
                break

        # continuous conversion flag bit 4
        contconv = (adc_config & 0x010)
        for key, val in self._mapcontconv.items():
            if val == contconv:
                self._adc_contconv = key
                break

        # input channet bits 5-6
        ipchan = (adc_config & 0x060)
        for key, val in self._mapipchan.items():
            if val == ipchan:
                self._adc_ipchan = key
                break

        # RDY flag bit 7
        # (adc_config & self._ADC_RDY)
        # nothing to be done
        return

    def raw_write(self, adc_data):
        """
        Directly write a byte into the ADC register.

        Return: nothing

        Use of this Method is strongly discouraged as it could cause
        side-effects, potentially resulting in a lock-up.
        """
        self._bus.transaction(i2c.writing_bytes(self._adc_address, adc_data))
        return

    def raw_read(self, reads):
        """
        Directly read byte(s) from the ADC register.

        Argument: number of bytes to read
        Return: byte(s) read

        Use of this Method is strongly discouraged as it could cause
        side-effects, potentially resulting in a lock-up.
        """
        return self._bus.transaction(i2c.reading(self._adc_address, reads))[0]

    def _read(self):
        """
        Take a single reading from the ADC.

        Return: float value

        Writes the local configuration byte to the ADC and then blocks until
        the ADC has completed one conversion which is then read and returned.
        """
        self._bus.transaction(i2c.writing_bytes(self._adc_address,
                                                            self._adc_config))
        if (self._adc_bitres == 18):
            h, m, l ,s = self._bus.transaction(i2c.reading(
                                                    self._adc_address, 4))[0]
            while (s & 128):
                h, m, l, s  = self._bus.transaction(i2c.reading(
                                                    self._adc_address, 4))[0]
            # shift bits to produce result
            t = ((h & 0b00000001) << 16) | (m << 8) | l
            # check if positive or negative number and invert if needed
            if (h > 128):
                t = ~(0x020000 - t)
            return (t/64000.0)
        else:
            m, l ,s = self._bus.transaction(i2c.reading(
                                                    self._adc_address, 3))[0]
            while (s & 128):
                m, l, s  = self._bus.transaction(i2c.reading(
                                                    self._adc_address, 3))[0]
            # shift bits to produce result
            t = (m << 8) | l
            # check if positive or negative number and invert if needed
            if (m > 128):
                t = ~(0x02000 - t)
            if (self._adc_bitres == 16):
                return (t/16000.0)
            if (self._adc_bitres == 14):
                return (t/4000.0)
            if (self._adc_bitres == 12):
                return (t/1000.0)

    def _read_bytes4(self):
        """
        Read 4 bytes (18 Bit resolution conversion and status byte).

        Return: integer value
        """
        h, m, l ,s = self._bus.transaction(i2c.reading(
                                                self._adc_address, 4))[0]
        while (s & 128):
            h, m, l, s  = self._bus.transaction(i2c.reading(
                                                self._adc_address, 4))[0]
        # shift bits to produce result
        v = ((h & 0b00000001) << 16) | (m << 8) | l
        # check if positive or negative number and invert if needed
        if (h > 128):
            v = ~(0x020000 - v)
        return v

    def _read_bytes3(self):
        """
        Read 3 bytes (16, 14, 12 Bit resolution conversion and status byte).

        Return: integer value
        """
        m, l ,s = self._bus.transaction(i2c.reading(
                                                self._adc_address, 3))[0]
        while (s & 128):
            m, l, s  = self._bus.transaction(i2c.reading(
                                                self._adc_address, 3))[0]
        # shift bits to produce result
        v = (m << 8) | l
        # check if positive or negative number and invert if needed
        if (m > 128):
            v = ~(0x02000 - v)
        return v

    def _read_18(self):
        """
        Convert 18 Bit resolution conversion to volts.

        Return: float value
        """
        v = (self._read_bytes4()/64000)
        if self._callback:
            self._callback(v)
        self._callback_id = None
        return v

    def _read_16(self):
        """
        Convert 16 Bit resolution conversion to volts.

        Return: float value
        """
        v = (self._read_bytes3()/16000)
        if self._callback:
            self._callback(v)
        self._callback_id = None
        return v

    def _read_14(self):
        """
        Convert 14 Bit resolution conversion to volts.

        Return: float value
        """
        v = (self._read_bytes3()/4000)
        if self._callback:
            self._callback(v)
        self._callback_id = None
        return v

    def _read_12(self):
        """
        Convert 12 Bit resolution conversion to volts.

        Return: float value
        """
        v = (self._read_bytes3()/1000)
        if self._callback:
            self._callback(v)
        self._callback_id = None
        return v

    def read_callback_cancel(self):
        """
        Cancel any scheduled callback.
        """
        if self._callback_id != None:
            if self._callback_id != -1:
                self._master.after_cancel(self._callback_id)
            self._callback_id = None

    def read(self, callback = None):
        """
        Initiate a single reading from the ADC.

        Passed nothing:
        Return: float value
        Writes the pre-defined configuration byte to the ADC and then blocks
        until the ADC has completed one conversion which is then read,
        converted to volts and returned.

        Passed handler function:
        Return:  nothing
        Writes the pre-defined configuration byte to the ADC and then arranges
        for callback after an appropriate delay and returns. After the delay
        expires the callback occurs, one conversion is read, converted to volts
        and passed to the specified handler function.
        """
        if self._callback_id == None:
            # immediately flag as 'busy'
            self._callback_id = -1
            # get bitres now in case it is changed after write
            bitres = self._adc_bitres
            self._bus.transaction(i2c.writing_bytes(self._adc_address,
                                                            self._adc_config))
            self._callback = callback
            if callback:
                # use the User's callback
                if (bitres == 18):
                    self._callback_id = self._master.after(self._adc_delay, self._read_18)
                elif (bitres == 16):
                    self._callback_id = self._master.after(self._adc_delay, self._read_16)
                elif (bitres == 14):
                    self._callback_id = self._master.after(self._adc_delay, self._read_14)
                elif (bitres == 12):
                    self._callback_id = self._master.after(self._adc_delay, self._read_12)
                else:
                    raise Exception(_PROGRAM_ERROR_MESSAGE)
                return
            else:
                # no callback, block & spin
                if (bitres == 18):
                    return self._read_18()
                elif (bitres == 16):
                    return self._read_16()
                elif (bitres == 14):
                    return self._read_14()
                elif (bitres == 12):
                    return self._read_12()
                else:
                    raise Exception(_PROGRAM_ERROR_MESSAGE)
        else:
            raise Exception("Busy")

    # remove prefix underscore (and this comment) when complete,
    # should also provide a callback method.
    def _read_next(self):
        """
        Collect the next reading from the ADC when programmed in
        continuous conversion mode.
        """
        if _adc_contconv:
            pass 
        else:
            raise Exception('ADC not in continuous conversion mode.')

    def exit(self):
        """
        Shut down the hardware and free all resources.
        """
        self.read_callback_cancel()
        self._lock.release()

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

