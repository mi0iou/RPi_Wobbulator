#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim:ai:sw=4:ts=8:et:fileencoding=utf-8
#
# RPi VoltMetercb v1.0
#
# Copyright (C) 2015 Gray Remlin 
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

# Example use of callback facility in one-shot mode provided by WobbyADC API 

# import GUI module
from tkinter import *

from Wobby.ADC import ADC as WobbyADC

# Class definition for RPiVoltMeter application
class RPiVoltMeter:

    def __init__(self, master):

        # Build Graphical User Interface
        frame = Frame(master, bd=10)
        frame.pack(fill=BOTH,expand=1)
        # voltage display
        self.voltage = DoubleVar()
        voltdisplay = Label(frame, bg='white', textvariable=self.voltage, width=18, anchor=W)
        voltdisplay.grid(row=0, column=0)
        voltlabel = Label(frame, text='Volts')
        voltlabel.grid(row=0, column=1)

        # input channel chooser
        self.ipchan = IntVar()
        cf = LabelFrame(frame, text='Channel', labelanchor='n')
        cf.grid(row=1, column=0)
        rb_ch1 = Radiobutton(cf, text='1', variable=self.ipchan, value=1,
                                                                command=self.vmipchan)
        rb_ch1.pack(anchor=W)

        rb_ch2 = Radiobutton(cf, text='2', variable=self.ipchan, value=2,
                                                                command=self.vmipchan)
        rb_ch2.pack(anchor=W)

        rb_ch3 = Radiobutton(cf, text='3', variable=self.ipchan, value=3,
                                                                command=self.vmipchan)
        rb_ch3.pack(anchor=W)
        rb_ch4 = Radiobutton(cf, text='4', variable=self.ipchan, value=4,
                                                                command=self.vmipchan)
        rb_ch4.pack(anchor=W)

        rb_ch1.grid(column=0, row=0)
        rb_ch2.grid(column=1, row=0)
        rb_ch3.grid(column=2, row=0)
        rb_ch4.grid(column=3, row=0)

        # start\stop control button
        self.b_m = Button(frame, text=' Start ', padx=5, pady=9, command=self.vmstart)
        self.b_m.pack(anchor=W)
        self.b_m.grid(row=1, column=1)

        # initialise the ADC
        self.adc = WobbyADC()
        self.adc.set_gain(1)
        self.adc.set_bitres(16)
        # synchronise GUI, initialise input channel
        rb_ch1.invoke()
        return

    # set the volt meter input channel
    def vmipchan(self):
        self.adc.set_ipchan(int(self.ipchan.get()))
        return

    # start sequential reads
    def vmstart(self):
        self.measure = True
        self.b_m.config(command = self.vmstop)
        self.b_m.config(text = ' Stop ', padx=6)
        # trigger a read event
        self.adc.read(self.show)
        return

    # stop sequential reads
    def vmstop(self):
        self.measure = False
        self.b_m.config(command = self.vmstart)
        self.b_m.config(text = ' Start ', padx=5)
        return

    # called with result of reading
    def show(self, v):
        # display the measured voltage
        self.voltage.set(v)
        if self.measure:
            # The ADC is in one-shot mode, trigger another read event
            # There is an element of re-entry here, this function was
            # called from the adc module which will now be called again
            # (re-entered) from here to initialise the next read....
            self.adc.read(self.show)
            # So RETURN ASAP to the adc module so it may return before it
            # re-calls here again resulting in recursive re-entry.
            return
        else:
            # cleardown
            self.voltage.set(0.0)
        return

    """
    # Not yet implemented in GUI

    # set the volt meter gain
    def vmgain(self):
        self.adc.setgain(int(self.gain.get()))

    # set the volt meter bit resolution
    def vmresolution(self):
        self.adc.setbitres(int(self.bitres.get()))

    # or alternatively

    # set the voltmeter samples per second
    def vmsps(self):
        self.adc.setsps(int(self.sps.get()))
    """
        
# Assign TK to root
root = Tk()
# Set main window title
root.wm_title('RPi VoltMeter')
# Create instance of class RPiVoltMeter
app = RPiVoltMeter(root)
# Start main loop and wait for input from GUI
root.mainloop()
app.adc.exit()
