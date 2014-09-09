#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim:ai:sw=4:ts=8:et:fileencoding=utf-8
#
# RPi VoltMeter v1.0
#
# Copyright (C) 2014 Tom Herbison MI0IOU
# Email tom@asliceofraspberrypi.co.uk
# Web <http://www.asliceofraspberrypi.co.uk>
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

# import GUI module
from tkinter import *

from Wobby.ADC import ADC as WobbyADC

# Class definition for RPiVoltMeter application
class RPiVoltMeter:

    # Build Graphical User Interface
    def __init__(self, master):
        frame = Frame(master, bd=10)
        frame.pack(fill=BOTH,expand=1)
        #display voltage
        self.voltage = DoubleVar()
        voltdisplay = Label(frame, bg='white', textvariable=self.voltage, width=18)
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

        # read voltage button
        b_m = Button(frame, text='Measure', padx=5, pady=9, command=self.vmread)
        b_m.pack(anchor=W)
        b_m.grid(row=1, column=1)

        # initialise the ADC
        self.adc = WobbyADC()
        self.adc.set_gain(1)
        self.adc.set_bitres(18)
        rb_ch1.invoke()


    # set the volt meter input channel
    def vmipchan(self):
        self.adc.set_ipchan(int(self.ipchan.get()))

    # take a volt meter reading
    def vmread(self):  
        self.voltage.set(self.adc.read())

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
