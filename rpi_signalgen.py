#!/usr/bin/python3
# vim:ai:sw=4:ts=8:et:fileencoding=ascii
#
# RPi SignalGen v1.0
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

# import GUI module
from tkinter import *

from  Wobby.DDS import DDS as WobbyDDS

# RPiSignalGen application
class RPiSignalGen():

    # Build Graphical User Interface
    def __init__(self, master):
        frame = Frame(master, bd=10)
        frame.pack(fill=BOTH,expand=1)

        # Control panel frame  
        fr_control = LabelFrame(frame, text='Control', labelanchor='n')
        fr_control.grid(row=1, column=0, columnspan=2)

        # Button to set and start signal generation
        self.b_set = b_set = Button(fr_control, text='Set', height=1, width=3,
                                activeforeground='red', command=self.set)
        b_set.grid(row=0, column=0)

        # Button to stop signal generation
        self.b_reset = b_reset = Button(fr_control, text='Reset', height=1, width=3,
                                activeforeground='red', command=self.reset)
        b_reset.grid(row=1, column=0)

        # Frequency panel frame
        fr_freq = fr_freq = LabelFrame(frame, text='Frequency (Hz)', labelanchor='n')
        fr_freq.grid(row=1, column=2, columnspan=2)

        # Frequency entry
        self.freq = StringVar()
        self.e_freq = Entry(fr_freq, textvariable=self.freq, width=13, justify=RIGHT)
        self.e_freq.grid(row=0, column=0)
        self.e_freq.insert(0,'1M')

        self.l_freqspacer = Label(fr_freq, text='--------------', width=13)
        self.l_freqspacer.grid(row=1, column=0)

        # frequency status
        self.freqstat = StringVar()
        self.l_freq = Label(fr_freq, width=13, )
        self.l_freq.grid(row=2, column=0)

        # initialise the DDS
        self.dds = WobbyDDS()
        # initialise the signalgen app
        self.b_reset.invoke()

    # Shamelessly plagiarised from mi0iou/RPi_Wobbulator
    # Function to convert freq f to Hz and return as int value
    #          e.g.: 10 MHz, 14.1m, 1k, 3.67 Mhz, 1.2 khz
    def _fconv(self,f):
            f = f.upper()
            if f.find("K") > 0:
                return (int(float(f[:f.find("K")]) * 1000))
            elif f.find("M") > 0:
                return (int(float(f[:f.find("M")]) * 1000000))
            else:  
                return (int(float(f)))

    # turn signal frequency off
    def reset(self):
        self.dds.reset()
        self.l_freq.config(fg='black', text=str(0)+' Hz')

    # set signal frequency & turn on
    def set(self):
        freq = self._fconv(self.freq.get())
        self.l_freq.config(fg='red', text=str(freq)+' Hz')
        self.dds.reset()
        self.dds.set_frequency(freq)


# Assign TK to root
root = Tk()
# Set main window title
root.wm_title('RPi SignalGen v1.0')
# Create instance of RPiSignalGen
app = RPiSignalGen(root)
# Wait for GUI input
root.mainloop()

