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


_PROGRAM_ERROR_MESSAGE = 'A Program Error has occurred, please report this bug'

class ADCException(Exception):
    pass

class ADC:

    # Serial Number
    _sernum = 20140701

    # Version 1 Revision 0
    _vernum = 1.0

    # FIXME: report supported hardware
    """
    MCP3424 18-Bit, Multi-Channel Analog-to-Digital Converter
    with I2C Interface and On-Board Reference.
    """

    # Configuration Contol Byte Bit Mappings

    # PGA Gain Bits 0-1
    _mapgain = { 1:0, 2:1, 4:2, 8:3, }

    # Bit Resolution\Samples Per Second Bits 2-3
    # 12 bits : 240 SPS  : 4.16 nS
    # 14 bits : 60 SPS   : 16.66 nS
    # 16 bits : 15 SPS   : 66.66 nS
    # 18 bits : 3.75 SPS : 266.66 nS

    _mapbitres = { 12:0, 14:4, 16:8, 18:12, }
    _mapbitreswait = { 12:1, 14:12, 16:55, 18:237, }
    _mapbitresdiv = {12:1000.0, 14:4000.0, 16:16000.0, 18:64000.0, }

    _mapsps = { 240:0, 60:4, 15:8, 3.75:12, }
    _mapspswait = { 240:1, 60:12, 15:55, 3.75:237, }
    _mapspsdiv = {240:1000.0, 60:4000.0, 15:16000.0, 3.75:64000.0, }

    # MUX Input Channel Selection Bits 5-6
    _mapipchan = { 1:0, 2:32, 3:64, 4:96, }

    _mapcontconv = { 0:0, 1:16, }

    # Continuous Conversion Bit 4 
    _ADC_CC = 16
    # ADC READY Control Bit 7
    _ADC_RDY = 128

    # Default I2C bus of ADC chip
    _adc_smbus = 1
    # Default I2C address of ADC chip
    _adc_address = 0x68

    # Defaults for configuration options
    _adc_gain = 1
    _adc_bitres = 12
    _adc_sps = 0
    _adc_ipchan = 1
    # Default for Continuous vs One-Shot conversion
    _adc_contconv = 0

    # Combined options configuration flag
    _adc_config = 0 + 0 + 0 + 0

    # Delay in ms (related to BPS\SPS)
    _adc_delay = 1
    # Conversion divisor (related to BPS\SPS)
    _adc_div = 1000.0
    # Conversion functuion (related to BPS\SPS)
    _adc_convfn = ()

    # User provided callback
    _tk_master = None
    _callback = ()

    # ADC busy (conversion in progress) handle
    _adc_busyid = None


    def __init__(self, adc_smbus = None, adc_address = None):
        """Prepare to perform hardware access."""

        print("RPiWobbulator ADC API Library Module Version " + 
                                                        str(self._vernum))

        global time
        import time

        try:
            import smbus
        except ImportError:
            msg = "\nError during smbus module import, ensure\n" + \
                  "the python3-smbus package is installed..\n" + \
                  "   sudo apt-get install python3-smbus\n"
            print(msg)
            raise

        from Wobby.Lock import Lock as WobbyLock

        # obtain lock for ADC
        try:
            self._lock = WobbyLock('ADC')
        except:
            raise ADCException("Error obtaining ADC Wobby lock\n")

        # NOTE: Early 256MB Pis < Revision 0004 are I2C0, smbus.SMBus(0)
        # prepare smbus I2C1 bus

        if adc_smbus != None:
            self._adc_smbus = adc_smbus

        if adc_address != None:
            self._adc_address = adc_address

        self._bus = smbus.SMBus(self._adc_smbus)

        self._mapbitresfn = {12:self._read_12_14_16, 14:self._read_12_14_16,
                                            16:self._read_12_14_16, 18:self._read_18, }
        self._mapspsfn = {240:self._read_12_14_16, 60:self._read_12_14_16,
                                            15:self._read_12_14_16, 3.75:self._read_18, }

        # initialise to a sane state
        self._config_update()

        return

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
        # Either\Or, zero indicates the unused option
        if self._adc_bitres:
            self._adc_config = self._mapbitres[self._adc_bitres]
            self._adc_delay = self._mapbitreswait[self._adc_bitres]
            self._adc_div = self._mapbitresdiv[self._adc_bitres]
            self._adc_convfn = self._mapbitresfn[self._adc_bitres]
            if self._adc_sps:
                raise ADCException(_PROGRAM_ERROR_MESSAGE)
        elif self._adc_sps:
            self._adc_config = self._mapsps[self._adc_sps]
            self._adc_delay = self._mapspswait[self._adc_sps]
            self._adc_div = self._mapspsdiv[self._adc_sps]
            self._adc_convfn = self._mapspsfn[self._adc_sps]
            if self._adc_bitres:
                raise ADCException(_PROGRAM_ERROR_MESSAGE)
        else:
            raise ADCException(_PROGRAM_ERROR_MESSAGE)

        self._adc_config |= self._mapgain[self._adc_gain]
        self._adc_config |= self._mapcontconv[self._adc_contconv]
        self._adc_config |= self._mapipchan[self._adc_ipchan]
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
            # set bitres (or sps but not both)
            self._adc_sps = 0
            self._config_update()
        return

    def set_sps(self, sps):
        """
        Set the 'Samples per Second' to be used during ADC conversion.

        Valid argument values: 240, 60, 15, 3.75
        Return: nothing

        This is an alternative to specifying the 'Bit Resolution'.
        """
        if self._adc_sps != sps:
            if sps not in self._mapsps.keys():
                raise ValueError('Invalid argument:{} not in {}'.format(
                                                    sps, self._mapsps.keys()))
            self._adc_sps = sps
            # set sps (or bitres but not both)
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
        # Ensure the _ADC_RDY bit is NOT set
        self._adc_config = (adc_config & 0x7F)

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
                self._adc_div = self._mapbitresdiv[self._adc_bitres]
                self._adc_convfn = self._mapbitresfn[self._adc_bitres]
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
        return

    def _read_18(self):
        """
        Process 18 Bit conversion.

        Read 3 bytes and status byte, convert to volts.
        Return: float value
        """
        # be nice and sleep a while rather than spin continuously
        time.sleep(self._adc_delay/1000)
        s = 128
        while (s & 128):
            h, m, l ,s = self._bus.read_i2c_block_data(self._adc_address,
                                                                self._adc_config, 4)
        # shift bits to produce result
        v = ((h & 0b00000001) << 16) | (m << 8) | l
        # check if positive or negative number and invert if needed
        if (h > 128):
            v = ~(0x020000 - v)
        v = (v/self._adc_div)
        self._adc_busyid = None
        if self._callback:
            self._callback(v)
        return v

    def _read_12_14_16(self):
        """
        Process 16, 14, and 12 Bit conversion.

        Read 2 bytes and status byte, convert to volts.
        Return: float value
        """
        # be nice and sleep a while rather than spin continuously
        time.sleep(self._adc_delay/1000)
        s = 128
        while (s & 128):
            m ,l, s = self._bus.read_i2c_block_data(self._adc_address,
                                                                self._adc_config, 3)
        # shift bits to produce result
        v = (m << 8) | l
        # check if positive or negative number and invert if needed
        if (m > 128):
            v = ~(0x02000 - v)
        v = (v/self._adc_div)
        self._adc_busyid = None
        if self._callback:
            self._callback(v)
        return v

    def read_callback_cancel(self):
        """
        Cancel any scheduled callback.
        """
        if self._adc_busyid != None:
            self._adc_busyid = None
            self._callback = None
        return

    def read(self, callback = None):
        """
        Initiate a single reading from the ADC.

        Passed: nothing
        Return: float value

        Writes the pre-defined configuration byte to the ADC and blocks
        until the ADC has completed one conversion which is then read,
        converted to volts and returned.

        Passed: callback function
        Return:  nothing

        Writes the pre-defined configuration byte to the ADC and spawns
        a new thread and returns. The new thread blocks until the ADC
        has completed one conversion which is then read, converted to
        volts and returned via callback.
        """
        if self._adc_busyid == None:
            # immediately flag as 'busy' to prevent re-entry
            self._adc_busyid = -1
            # start the conversion
            self._bus.write_i2c_block_data(self._adc_address,
                                            (self._adc_config | self._ADC_RDY), [])

            if callback:

                import threading

                class NewThread(threading.Thread):

                    _fn = ()

                    def __init__(self, fn):
                        #Setup object
                        threading.Thread.__init__(self)
                        self._fn = fn
                        return

                    def run(self):
                        #Run object
                        self._fn()
                        return

                self._callback = callback
                process = NewThread(self._adc_convfn)
                process.daemon = True
                process.start()
                return
            else:
                # No callback, block & spin for the conversion
                return self._adc_convfn()

        else:
            raise ADCException("Busy")
        return

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
            raise ADCException('ADC not in continuous conversion mode.')
        return

    def exit(self):
        """
        Shut down the hardware and free all resources.
        """
        self.read_callback_cancel()
        self._lock.release()
        print("RPiWobbulator ADC API Library Module exiting")
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

        return

if __name__ == '__main__':
    main()

