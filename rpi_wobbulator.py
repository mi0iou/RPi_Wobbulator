#!/usr/bin/python3
# vim:ai:sw=4:ts=8:et:fileencoding=ascii
#
# Based on RPi Wobbulator v2.7.1
#
# Copyright (C) 2013-2014 Tom Herbison MI0IOU
# Email tom@asliceofraspberrypi.co.uk
# Web <http://www.asliceofraspberrypi.co.uk>

# Special thanks to Tony Abbey for his efforts developing v2 of the software...
# Edits by Tony Abbey for 10 speed up and continuous looping until STOP button
# ADC now runs at either 60 sps 14 bits or 240 SPS and 12 bits in one-shot mode
# to prevent glitches. Also added initialisation of frequency scan values,
# "Fast" option, optional screen clear every sweep plus code suggested by
# Fred LaPlante for a "scope-like" trace
# Also Fred for horizontal frequency scale, and Tony for vertical scale
# Now programmable display size and scales, stored in parameter file by Fred
# MHz, kHz i/p etc by Dick Bronsdijk
# Display tweaks by various and Tony added vertical text on Y scale
# v2.6.0 Addition of Y scale in dB and bias average of 2 readings - Tony
# v2.6.1 Bias option automatically selected when using dB scale - Tom
# v2.6.2 Grid Display issues corrected - Tom
# v2.6.3 dBm button now updates the Y scale - Tony
# v2.6.4 Recent changes consolidated and code tidied up - Tom
# v2.6.5 Scaling changes to represent ADC range better and remove some old change comments - Tony (afa)
# v2.6.6 Auto linear scale for ch 1, and optional lin/log for ch 2 - Tony
# v2.7.0 ADC may now be set at 3.75SPS 18Bit, 15SPS 16Bit, 60SPS 14Bit or 240SPS 12Bit - Tom (tgh)
# v2.7.1 scale of dBm scale changed. DBm option removed and dBm scale only shown when using Channel 2,
#        Volt scale show for other channels. Bias option removed and bias compensation applied to
#        channel 2, no bias compensation applied to other channels. Code tidied up - Tom (tgh)

# Please see "README.txt" for a description of this software
# and for details of the version change log

# If you wish to make changes to this software and would like your
# changes to be incorporated into a future release please visit,
# <https://github.com/mi0iou/RPi_Wobbulator> and 'fork' the repository

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time

# import GUI module
from tkinter import *

import tempfile
import subprocess
import os

# ---- get user preferences or set defaults ----
# for param file persistence, import faster cPickle if available
try:
    import cPickle as pickle
except:
    import pickle

version = '2.7.1-Y'

params = {}

def default_parameters():
    print('Loading default parameters')
    params['version'] = version
    params['chrtHt'] = 500
    params['chrtWid'] = 500
    params['xDivs'] = 10
    params['yDivs'] = 10
    params['canvFg'] = 'black'
    params['canvBg'] = '#008484'
    params['fBegin'] = 0
    params['fEnd'] = 35000000
    params['fIntvl'] = 100000
    params['vgain'] = 1
    params['vchan'] = 1
    params['colour'] = 'red'
    params['ms'] = 0
    params['rec'] = 0
    params['cc'] = 0
    params['cls'] = 0
    params['grid'] = 1
    params['bits'] = 18

# user parameters
paramFN = 'wobParam.pkl'
try:
    paramFile = open(paramFN,"rb")
except IOError:
    default_parameters()
else:
    try:
        params = pickle.load(paramFile)
    except EOFError:
        default_parameters()
    paramFile.close()
try:
    if params['version'] != version:
        raise
except:
    default_parameters()
# print (params)

# ---- end of user param support ----

# ---- for app menus and associated displays ----
from tkinter import messagebox
from tkinter import colorchooser
from tkinter import filedialog
# ---- end of menu support ----

from Wobby.ADC import ADC as WobbyADC
from Wobby.DDS import DDS as WobbyDDS


# Class definition for WobbyPi application
class WobbyPi():

    adc = WobbyADC()
    dds = WobbyDDS()

    buf_data = {}
    line_buffer = {}

    # immutable variables
    # these may not change during a sweep
    _emit_startfreq = 0
    _emit_stopfreq = 0
    _emit_stepfreq = 0
    _emit_spanfreq = 0
    _emit_ipchan = 0
    _emit_gain = 0
    _emit_colour = ''

    # postscript will change the font but keep the pixelsize
    text_font = ('clean','8')

    sweep_start_reqd = True

    #options_option = {0:[IntVar, 'Gr', 1, 0, self.grid, self.graticule_update],
    #                  1:[IntVar, 'Cls', 1, 0, self.cls, ()],
    #                    }

    _ipchan_option = {0:1, 1:2, 2:3, 3:4}
    _gain_option = {0:1, 1:2, 2:4, 3:8}
    _bitres_option = {0:18, 1:16, 2:14, 3:12}
    _colour_option = {0:'red', 1:'magenta', 2:'yellow', 3:'green', 4:'blue'}

    _colour_button = {}
    _colour_iterator = ()
    _colour_cycle = ''

    _sweep_iterator = ()

    _callback_id = 0

    # Build Graphical User Interface
    def __init__(self, master, params):

        optiontkfonts = ['TkCaptionFont', 'TkSmallCaptionFont', 'TkTooltipFont',
                                'TkFixedFont', 'TkHeadingFont', 'TkMenuFont',
                                'TkIconFont', 'TkTextFont', 'TkDefaultFont']

        for opt in optiontkfonts:
            root.tk.call('font', 'configure', opt, '-family', self.text_font[0],
                                                    '-size', self.text_font[1])

        frame = Frame(master, bd=10)
        frame.pack(fill=BOTH,expand=1)

        # setup working parameters
        # system values
        self.mrgnLeft = 56
        self.mrgnRight = 20
        self.mrgnTop = 30
        self.mrgnBotm = 30

        # user values
        self.canvFg = params['canvFg']
        self.canvBg = params['canvBg']
        self.chrtHt = int(params['chrtHt'])
        self.chrtWid = int(params['chrtWid'])
        self.xDivs = params['xDivs']
        self.yDivs = params['yDivs']
        self.fBegin = params['fBegin']
        self.fEnd = params['fEnd']
        self.fIntvl = params['fIntvl']

        # setup canvas to display results
        global canvas
        self.canvHt = self.mrgnTop + self.chrtHt + self.mrgnBotm
        self.canvWid = self.mrgnLeft + self.chrtWid + self.mrgnRight
        canvas = Canvas(frame, width = self.canvWid, height = self.canvHt,
                                                            bg = self.canvBg)
        canvas.grid(row = 0, column = 0, columnspan = 6, rowspan = 7)

        # Input channel
        fr_ipchan = LabelFrame(frame, text = 'Input', labelanchor = 'n')
        fr_ipchan.grid(row = 0, column = 6)

        self.ipchan = IntVar()
        for key, ipchan in self._ipchan_option.items():
            txt = str(key + 1)
            rb = Radiobutton(fr_ipchan, text = txt, value = key,
                                                variable = self.ipchan,
                                                command = self.ipchan_update)
            rb.grid(row = key, sticky = 'w')
            if int(params['vchan']) == key + 1:
                rb.select()

        # Input gain
        fr_gain = LabelFrame(frame, text = 'Gain', labelanchor = 'n')
        fr_gain.grid(row = 1, column = 6)

        self.gainval = IntVar()
        for key, gain in self._gain_option.items():
            txt = 'x ' + str(gain)
            rb = Radiobutton(fr_gain, text = txt, value = key,
                                                variable = self.gainval,
                                                command = self.gain_update)
            rb.grid(row = key, sticky = 'w')
            if int(params['vgain']) == gain:
                rb.select()

        # Bit resolution 18Bit, 16Bit, 14Bit, 12Bit
        fr_bitres = LabelFrame(frame, text = 'BPS', labelanchor = 'n')
        fr_bitres.grid(row = 2, column = 6)

        self.bitval = IntVar()
        for key, bitres in self._bitres_option.items():
            txt = str(bitres)
            rb = Radiobutton(fr_bitres, text = txt, value = key,
                                                variable = self.bitval,
                                                command = self.bitres_update)
            rb.grid(row = key, sticky = 'w')
            if int(params['bits']) == bitres:
                rb.select()

        # Colour of trace
        fr_colour = LabelFrame(frame, text = 'Colour', labelanchor = 'n')
        fr_colour.grid(row = 3, column = 6)

        # FIXME use value = key
        self.colour = StringVar()
        # rb.invoke() below is dependant on self.colcyc
        self.colcyc = IntVar()
        for key, colour in self._colour_option.items():
            txt = '[' + colour[0].upper() + ']'
            rb = Radiobutton(fr_colour, fg = colour, text = txt, value = colour,
                                                variable = self.colour,
                                                command = self.colour_update)
            rb.grid(row = key + 1, sticky = 'w')
            key_rb = [key, rb]
            self._colour_button[key] = rb
            if params['colour'] == colour:
                rb.invoke()

        # Options
        fr_cb = LabelFrame(frame, text = 'Opts', labelanchor = 'n')
        fr_cb.grid(row = 4, column = 6)

        # enable\disable graticule display
        self.graticule = IntVar()
        cb_graticule = Checkbutton(fr_cb, text = "Gr", onvalue = 1, offvalue = 0,
                                            variable = self.graticule,
                                            command = self.graticule_update)

        # enable\disable clear screen before sweep
        self.cls = IntVar()
        cb_clear = Checkbutton(fr_cb, text = 'Cls', onvalue = 1, offvalue = 0,
                                                        variable = self.cls)

        # enable\disable record data
        self.record = IntVar()
        cb_record = Checkbutton(fr_cb, text = 'Rec', onvalue = 1, offvalue = 0,
                                                variable = self.record,
                                                command = self.record_update)

        # enable\disable memory store (for trace persistence)
        self.memstore = IntVar()
        cb_memstore = Checkbutton(fr_cb, text = 'MS', onvalue = 1, offvalue = 0,
                                                variable = self.memstore,
                                                command = self.memstore_update)

        # enable\disable colour cycling of trace
        cb_colcyc = Checkbutton(fr_cb, text = 'CC', onvalue = 1, offvalue = 0,
                                                   variable = self.colcyc,
                                                   command = self.colour_update)

        cb_graticule.grid(row = 0, column = 0, sticky = 'w')
        cb_clear.grid(row = 1, column = 0, sticky = 'w')
        cb_record.grid(row = 2, column = 0, sticky = 'w')
        cb_memstore.grid(row = 3, column = 0, sticky = 'w')
        cb_colcyc.grid(row = 4, column = 0, sticky = 'w')

        if int(params['grid']) == 1:
            cb_graticule.select()
        if int(params['cls']) == 1:
            cb_clear.select()
        if int(params['rec']) == 1:
            cb_record.select()
        if int(params['ms']) == 1:
            cb_memstore.select()
        if int(params['cc']) == 1:
            cb_colcyc.select()

        # user description space
        fr_desc = Label(frame, text = 'Desc.')
        fr_desc.grid(row = 7, column = 0, columnspan = 1)

        self.desc = StringVar()
        e_desc = Entry(frame, width = 66, textvariable = self.desc)
        e_desc.grid(row = 7, column = 1, columnspan = 4)
        e_desc.bind('<Key-Return>', self.desc_change)
        e_desc.insert(0, 'Mouse-Left-Click exactly on the sweep trace')
        self.desc_change(None)

        # frequency entries
        fr_freq = LabelFrame(frame, text = 'Frequency (Hz)', labelanchor = 'n')
        fr_freq.grid(row = 8, column = 0, columnspan = 4)

        # start frequency for sweep
        fr_startf = Label(fr_freq, text = 'Start:')
        fr_startf.grid(row = 0, column = 0)
        self.fstart = StringVar()
        e_startf = Entry(fr_freq, textvariable = self.fstart, width = 8, )
        e_startf.grid(row = 0, column = 1)
        e_startf.insert(0, self.fBegin)
        e_startf.bind('<Key-Return>', self.freq_change)

        # stop frequency for sweep
        self.fstop = StringVar()
        fr_stopf = Label(fr_freq, text = ' Stop:')
        fr_stopf.grid(row = 0, column = 2)
        e_stopf = Entry(fr_freq, textvariable = self.fstop, width = 8)
        e_stopf.grid(row = 0, column = 3)
        e_stopf.insert(0, self.fEnd)
        e_stopf.bind('<Key-Return>', self.freq_change)

        # increment for sweep
        fr_stepf = Label(fr_freq, text = ' Step:')
        fr_stepf.grid(row = 0, column = 4)
        self.fstep = StringVar()
        e_stepf = Entry(fr_freq, textvariable=self.fstep, width = 8)
        e_stepf.grid(row = 0, column = 5)
        e_stepf.insert(0, self.fIntvl)
        e_stepf.bind('<Key-Return>', self.freq_change)

        # control panel frame
        fr_control = LabelFrame(frame, text = 'Control', labelanchor = 'n')
        fr_control.grid(row = 8, column = 4, columnspan = 2)

        # Button to reset settings
        self.b_reset = Button(fr_control, text = 'Reset', height = 1, width = 3,
                                                    activeforeground = 'red',
                                                        command = self.reset)
        # Button to start a single sweep
        self.b_sweep = Button(fr_control, text = 'Sweep', height = 1, width = 3,
                                                    activeforeground='red',
                                                    command=self.single_sweep)
        # Button to control actions
        self.b_action = Button(fr_control, text = 'Cycle', height = 1, width = 3,
                                                    activeforeground = 'red',
                                                    command = self.cycle_sweep)
        # Button to save data
        self.b_save = Button(fr_control, text = 'Save', height = 1, width = 3,
                                    activeforeground = 'red', state = DISABLED,
                                                    command = self.save_canvas)

        self.b_reset.grid(row = 0, column = 0)
        self.b_sweep.grid(row = 0, column = 1)
        self.b_action.grid(row = 0, column = 2)
        self.b_save.grid(row = 0, column = 3)
        canvas.update_idletasks()

    def desc_change(self, event):
        """ Update the canvas with the description """
        canvas.delete('desc')
        xpos = self.mrgnLeft + (self.chrtWid / 2)
        ypos = self.mrgnTop / 2
        canvas.create_text(xpos, ypos, fill = self.canvFg, anchor = CENTER,
                                        text = self.desc.get(), tag = 'desc')

    def freq_change(self, event):
        self.sweep_start_reqd = True
        """ Potentially - fill step field with suitable value ? """
        start = self.fconv(self.fstart.get())
        stop = self.fconv(self.fstop.get())
        span = stop - start
        step = int(span / self.chrtWid)
        # one pixel per step
        print('Suggested Step:{} chrtWid:{}'.format(step, self.chrtWid))

    def makemenu(self, win):
        global root
        top = Menu(win)
        win.config(menu = top)    # set its menu option
        m_file = Menu(top, tearoff = 0)
        top.add_cascade(label = 'File', menu = m_file, underline = 0)
        m_file.add_command(label = 'Load', command = self.file_load,
                                        underline = 0, accelerator = 'Ctrl+L')
        m_file.add_command(label = 'Save', command = self.file_save,
                                        underline = 0, accelerator = 'Ctrl+S')
        m_file.add_command(label = 'Exit', command = self.exit,
                                        underline = 1, accelerator = 'Ctrl+Q')
        opt = Menu(top, tearoff = 0)
        top.add_cascade(label = 'Options', menu = opt, underline = 0)
        opt.add_command(label = 'Background', command = self.getBackgroundColor,
                                                                underline = 0)
        opt.add_command(label = 'Foreground', command = self.getForegroundColor,
                                                                underline = 0)
        opt.add_separator()
        opt.add_command(label = 'Chart Width', command = self.getChartWidth,
                                                                underline = 6)
        opt.add_command(label = 'Chart Height', command = self.getChartHeight,
                                                                underline = 6)
        opt.add_separator()
        opt.add_command(label = 'X-divisions', command = self.getXdivisions,
                                                                underline = 0)
        opt.add_command(label = 'Y-divisions', command = self.getYdivisions,
                                                                underline = 0)
        help = Menu(top, tearoff = 0)
        top.add_cascade(label = 'Help', menu = help, underline = 0)
        help.add_command(label = 'Controls', command = self.showHelp,
                                                                underline = 0)
        help.add_command(label = 'About Wobbulator', command = self.showAbout,
                                                                underline = 0)

    def not_done(self):
        messagebox.showerror('Not implemented', 'Not yet available')

    def showHelp(self):
        helpmsg = "\
\nInput: [ 1 2 3 4 ]\n\
- select the active input channel\n\
\nGain: [ x1 x2 x4 x8 ]\n\
- select input gain amplification\n\
\nBPS: [ 18 16 14 12 ]\n\
- bits per sample\n\
\nColour: [ R M Y G B ]\n\
- colour used to display trace\n\
  Red Magenta Green Yellow Blue\n\
\nOptions:\n\
[Gr]  - Graticule display\n\
[Cls] - Clear display at sweep start\n\
[Rec] - Record sweeps for saving\n\
[MS]  - Memory Store display\n\
[CC]  - Colour Cycle after sweep\n\
"
        messagebox.showinfo('Help', helpmsg)

    def showAbout(self):
        aboutmsg = "\
   RPi Wobbulator " + version + "\n\
\n\
   Copyright (C) 2013-2014\n\
     Tom Herbison MI0IOU\n\
\n\
                   Email:\n\
tom@asliceofraspberrypi.co.uk\n\
\n\
                   HTTP:\n\
www.asliceofraspberrypi.co.uk\n\
"
        messagebox.showinfo('About RPi Wobbulator', aboutmsg)

    def getForegroundColor(self):
        fgColor = colorchooser.askcolor(params['canvFg'],
                                            title = 'Foreground Color')
        if fgColor[1] != 'None':
            params['canvFg'] = fgColor[1]
            self.canvFg = fgColor[1]

    def getBackgroundColor(self):
        bgColor = colorchooser.askcolor(params['canvBg'],
                                            title = 'Background Color')
        if bgColor[1] != 'None':
            params['canvBg'] = bgColor[1]
            self.canvBg = bgColor[1]

    def getChartWidth(self):
        chrtWid = simpledialog.askinteger('Chart Width', '300 to 1000',
                                            initialvalue = params['chrtWid'],
                                            minvalue = 300, maxvalue = 1000)
        if chrtWid != 'None':
            params['chrtWid'] = chrtWid
            self.chrtWid = chrtWid

    def getChartHeight(self):
        chrtHt = simpledialog.askinteger('Chart Height', '300 to 1000',
                                            initialvalue = params['chrtHt'],
                                            minvalue = 300, maxvalue = 1000)
        if chrtHt != 'None':
            params['chrtHt'] = chrtHt
            self.chrtHt = chrtHt

    def getXdivisions(self):
        xDivs = simpledialog.askinteger('X-divisions', '10-50',
                                            initialvalue = params['xDivs'],
                                            minvalue = 10, maxvalue = 50)
        if xDivs != 'None':
            params['xDivs'] = xDivs
            self.xDivs = xDivs

    def getYdivisions(self):
        yDivs = simpledialog.askinteger('Y-divisions', '10-50',
                                            initialvalue = params['yDivs'],
                                            minvalue = 10, maxvalue = 50)
        if yDivs != 'None':
            params['yDivs'] = yDivs
            self.yDivs = yDivs

    def file_load(self):
        filename = filedialog.askopenfilename()
        if filename:
            fname, fext = os.path.splitext(filename)
            try:
                dumpFile = open(filename, "rb")
            except IOError:
                messagebox.showerror('File Error', '!$*!%')
                return
            try:
                dumpData = pickle.load(dumpFile)
            except EOFError:
                messagebox.showerror('File Error', 'File is empty!')
                dumpFile.close()
                return
            except IOError:
                dumpFile.close()
            for key in dumpData:
                print(str(key) + ' ' + str(dumpData[key]))

    def file_save(self):
        filename = filedialog.asksaveasfilename()
        if filename:
            fname, fext = os.path.splitext(filename)
            if not fext:
                fext = 'wtf' # wobbulator trace file

        #try:
            # determine file contents to save by filename extension
        #except EOFError:
        #    pass
        #except IOError:
        #    pass
        #except:
        #    pass
        # FIXME: not enough try
        dataFile = open(filename, "wb")
        pickle.dump(self.buf_data, dataFile)
        dataFile.close()

    def initialise(self):
        """ Initialise variables, buffers, and state """
        # Synchronise Hardware & GUI state\appearance
        self.ipchan_update()
        self.gain_update()
        self.bitres_update()
        self.clearscreen()
        self.memstore_reset()
        self.colour_sync()
        self.sweep_start_reqd = True
        # FIXME: better to invoke self.reset() and
        # strip duplicated actions from this section ?

    # clear the screen
    def clearscreen(self):
        """ reclaim and re-draw canvas area """
        canvas.delete('plot')
        self.memstore_reset()
        self.label_yscale()
        self.label_xscale()
        self.graticule_update()
        self.desc_change(None)
        canvas.update_idletasks()

    # display graticule
    def graticule_update(self):
        """ reclaim and re-draw graticule or label border """
        canvas.delete('graticule')
        if self.graticule.get():
            # coarse division vertical lines
            ystart = self.mrgnTop
            yend = self.mrgnTop + self.chrtHt
            xstep = int(self.chrtWid / self.xDivs)
            for x in range(self.mrgnLeft, self.mrgnLeft + self.chrtWid + 1, xstep):
                canvas.create_line(x, ystart, x, yend, fill = self.canvFg,
                                                            tag = 'graticule')
            # coarse division horizontal lines
            xstart = self.mrgnLeft
            xend = self.mrgnLeft + self.chrtWid
            ystep = int(self.chrtHt/self.yDivs)
            for y in range(self.mrgnTop, self.mrgnTop + self.chrtHt + 1, ystep):
                canvas.create_line(xstart, y, xend, y, fill = self.canvFg,
                                                            tag = 'graticule')

            # fine divisions along x and y centre lines only
            # fine division horizontal lines along vertical axis
            x = self.mrgnLeft + int(self.chrtWid / 2)
            xstart = x - 4
            xend = x + 5
            ystep = int(ystep / 5)
            for y in range(self.mrgnTop + ystep,
                                self.mrgnTop + self.chrtHt + 1 - ystep, ystep):
                canvas.create_line(xstart, y, xend, y, fill = self.canvFg,
                                                            tag = 'graticule')

            # fine division vertical lines along horizontal axis
            y = self.mrgnTop + int(self.chrtHt / 2)
            ystart = y - 4
            yend = y + 5
            xstep = int(xstep / 5)
            for x in range(self.mrgnLeft + xstep,
                            self.mrgnLeft + self.chrtWid + 1 - xstep, xstep):
                canvas.create_line(x, ystart, x, yend, fill = self.canvFg,
                                                            tag = 'graticule')
        else:
            # border the scale labels
            canvas.create_line(self.mrgnLeft, self.mrgnTop, self.mrgnLeft,
                                        self.mrgnTop + self.chrtHt,
                                        fill = self.canvFg, tag = 'graticule')

            y = self.chrtHt + self.mrgnTop
            canvas.create_line(self.mrgnLeft, y, self.mrgnLeft + self.chrtWid,
                                    y, fill = self.canvFg, tag = 'graticule')
        canvas.update_idletasks()

    def ipchan_update(self):
        """ input channel change, effect and adjust y-scale labels """
        ipchan = self._ipchan_option[self.ipchan.get()]
        self.adc.set_ipchan(ipchan)
        self.label_yscale()
        self.sweep_start_reqd = True

    def gain_update(self):
        """ gain change, effect and adjust y-scale labels """
        gain = self._gain_option[self.gainval.get()]
        self.adc.set_gain(gain)
        self.label_yscale()
        self.sweep_start_reqd = True

    def bitres_update(self):
        """ bit resolution change, effect """
        bitres = self._bitres_option[self.bitval.get()]
        self.adc.set_bitres(bitres)

    def colour_update(self):
        """ colour\cycling change, synchronise colour cycling """
        self.colour_sync()

    def record_update(self):
        """ record sweep state change, placeholder """
        self.not_done()

    def memstore_update(self):
        """ memory store state change """
        if not self.memstore.get() and self.memstore_valid == True:
            self.memstore_reset()
            canvas.delete("plot")
            # reclaiming plot tags may remove wanted trace
            # not reclaiming plot tags may leave unwanted trace
            # lose : lose

    def fconv(self,f):
        """
        convert frequency f to Hz and return as int value
        e.g.: 10 MHz, 14.1m, 1k, 3.67 Mhz, 1.2 khz
        """
        try:
            f = f.upper()
            if f.find("K") > 0:
                return (int(float(f[:f.find("K")]) * 1000))
            elif f.find("M") > 0:
                return (int(float(f[:f.find("M")]) * 1000000))
            else:
                return (int(float(f)))
        except ValueError:
            return 0

    # FIXME do this the python way & ditch this 'C' function
    # close but not quite, sometimes strips off one too many zero's
    def lblfmt(self, val):
        lbl = str('{0:02.3f}'.format(val)).rstrip('0')
        if lbl[len(lbl) - 1] == '.':
            lbl = lbl + '0'
        return lbl

    def label_xscale(self):
        """ reclaim and display x-axis labels """
        startF = float(self.fconv(self.fstart.get()))
        stopF = float(self.fconv(self.fstop.get()))
        if stopF > 1000000:
            f0 = round(startF / 1000000.0, 6)
            fN = round(stopF / 1000000.0, 6)
            fDesc = 'x 1000000 (MHz)'
        elif stopF > 1000:
            f0 = round(startF / 1000.0, 6)
            fN = round(stopF / 1000.0, 6)
            fDesc = 'x 1000 (kHz)'
        else:
            f0 = round(startF / 1.0, 6)
            fN = round(stopF / 1.0, 6)
            fDesc = 'x 1 (Hz)'

        canvas.delete('hlabel')

        fStep = (fN - f0) / self.xDivs
        xpos = (self.mrgnLeft / 2) + 28
        ypos = self.mrgnTop + self.chrtHt + 8
        while f0 < fN:
            stry = self.lblfmt(f0)
            canvas.create_text(xpos, ypos, fill = self.canvFg,
                                                text = stry, tag = 'hlabel')
            f0 = round(f0 + fStep, 6)
            xpos = xpos + (self.chrtWid / self.xDivs)
        stry = self.lblfmt(fN)
        canvas.create_text(xpos, ypos, fill = self.canvFg,
                                                text = stry, tag = 'hlabel')
        # display the horizontal axis label
        xpos = (((self.mrgnLeft + self.chrtWid + self.mrgnRight) - len(fDesc))
                                                                    / 2) + 26
        canvas.create_text(xpos, ypos + 15, fill = self.canvFg,
                                                text = fDesc, tag = 'hlabel')
        canvas.update_idletasks()

    # display vertical axis labels
    def label_yscale(self):
        """ reclaim and display y-axis labels """
        gain = self._gain_option[self.gainval.get()]
        ipchan = self._ipchan_option[self.ipchan.get()]
        if ipchan == 2:
            # Channel 2 (log) is selected
            startV = float(-75)
            stopV = float(-25)
            vN = startV + 50 / gain
            vDesc = 'dBm'
        else:
            # Assume linear scale
            startV = float(0)
            stopV = float(2.0)
            vN = stopV / gain
            vDesc = 'Volts'

        canvas.delete('vlabel')

        vStep = (vN - startV) / self.yDivs
        xpos = self.mrgnLeft - 25
        ypos = self.mrgnTop
        while vN > startV:
            stry = self.lblfmt(vN)
            canvas.create_text( xpos, ypos, fill = self.canvFg,
                                                text = stry, tag = 'vlabel')
            vN = vN - vStep
            ypos = ypos + (self.chrtHt / self.yDivs)
        stry = self.lblfmt(startV)
        canvas.create_text(xpos, ypos, fill = self.canvFg,
                                                text = stry, tag = 'vlabel')
        # write the vertical label
        xpos = self.mrgnLeft - 48
        ypos = int((self.chrtHt - len(vDesc)) / 2) + self.mrgnTop
        canvas.create_text(xpos, ypos, fill = self.canvFg,
                                    text = "\n".join(vDesc), tag = 'vlabel')
        canvas.update_idletasks()

    def sweep_start(self):
        """ perform frequency sweep """

        # start\stop\stepfreq could be made 'enter key' bind dependant all
        # setting 'sweep_start_reqd' when changed, simplifying code here.
        # Do we wish to force 'Enter'ing on the User ?
        startfreq = self.fconv(self.fstart.get())
        stopfreq = self.fconv(self.fstop.get())
        stepfreq = self.fconv(self.fstep.get())
        ipchan = self._ipchan_option[self.ipchan.get()]
        gain = self._gain_option[self.gainval.get()]
        self._emit_colour = self._colour_cycle

        #  If a sweep dependant value has changed
        if (self.sweep_start_reqd or (self._emit_startfreq != startfreq) or
                                        (self._emit_stopfreq != stopfreq) or
                                            (self._emit_stepfreq != stepfreq)):
            if (startfreq > stopfreq) or (stepfreq < 1):
                self.invalid_sweep()
                return
            self._emit_span = (stopfreq-startfreq)
            self._emit_startfreq = startfreq
            self._emit_stopfreq = stopfreq
            self._emit_stepfreq = stepfreq
            self._emit_gain = gain
            self._emit_ipchan = ipchan
            self.clearscreen()
            self.sweep_start_reqd = False
            if self.record.get():
                # save a trace sweep header
                # Need to handle the case of multiple traces
                ddu = {'fstart' : startfreq, 'fstop' : stopfreq,
                                                        'fstep' : step}
                self.buf_data.update(ddu)
                ddu = {'Input' : ipchan}
                self.buf_data.update(ddu)
                ddu = {'Gain' : gain}
                self.buf_data.update(ddu)
                ddu = {'colour' : colour}
                self.buf_data.update(ddu)

                # FIXME: some of the below may change during sweep
                bitres = self._bitres_option[self.bitval.get()]
                ddu = {'BPS' : bitres}
                self.buf_data.update(ddu)
                ddu = {'Desc' : self.desc}
                self.buf_data.update(ddu)
        elif self.cls.get():
            self.clearscreen()

        # scale and bias are dependant on input channel
        if ipchan == 2:
            # signal for the DDS to reset
            self.dds.reset()
            # calculate bias from input when no frequency being output
            plotbias = ((self.adc.read() + self.adc.read()) / 2)
            plotscale = 1
        else:
            plotbias = 0
            plotscale = 2

        # graticule offset for x-coordinate start point
        self.xstart = self.mrgnLeft

        # y = int(self.chrtHt + self.mrgnTopr
        #             - ((reading - plotbias) * self.chrtHt/plotscale))
        """ simplify y-coordinate calulation for use inside the loop """
        # y2 = self.chrtHt/plotscale
        # y3 = self.chrtHt + self.mrgnTop
        # y = int(y3 - ((reading - plotbias) * y2))
        # re-express
        # y = int(y3 - ((reading * y2) - (plotbias * y2)))
        # y4 = (plotbias * y2)
        # y = int(y3 - ((reading * y2) - y4))
        # re-express
        # y = int((y3 + y4) - (reading * y2))
        # y1 = (y3 + y4)
        # simplified equivalence
        # y = int(y1 - (reading * y2))
        self.y2 = (self.chrtHt / plotscale)
        self.y1 = (self.chrtHt + self.mrgnTop + (plotbias * self.y2))

        """ simplify x-coordinate calulation for use inside the loop """
        # x = int((chrtWid * ((frequency - startfreq) / span)) + mrgnLeft)
        # re-express
        # x = int((chrtWid * ((frequency / span) - (startfreq/ span))) + mrgnLeft)
        # re-express
        # x = int(((chrtWid * (frequency / span)) - (chrtWid * (startfreq / span))) + mrgnLeft)
        # re-express
        # x = int((chrtWid * (frequency / span)) - ((chrtWid * (startfreq / span)) - mrgnLeft))
        # re-express
        # x2 = ((chrtWid * (startfreq / span)) - mrgnLeft)
        # x = int((chrtWid * (frequency / span)) - x2)
        # re-express
        # x = int(((chrtWid / span) * frequency) - x2)
        # x1 = (chrtWid / span)
        # simplified equivalence
        # x = int((x1 * frequency) - x2)
        self.x2 = ((self.chrtWid * (startfreq / self._emit_span))
                                                            - self.mrgnLeft)
        self.x1 = (self.chrtWid / self._emit_span)

        # Reset immediately before setting frequency
        self.dds.reset()
        # program the DDS to output the required frequency
        self.dds.set_frequency(startfreq)
        # compensate for errors in first readings related to a
        # significant frequency jump and low bit resolution by
        # throwing away a quantity inversely proportional to
        # the bit resolution key value i.e. 0:18, 1:16, 2:14, 3:12
        _magic = self.bitval.get() + 2
        for n in range(_magic * _magic):
            # 18>4 16>9 14>16 12>25
            self.adc.read()
        # take voltage reading
        reading = self.adc.read()
        # for y-coordinate start point
        self.ystart = self.y1 - (reading * self.y2)
        # Initialise the frequency generator
        # If stepfreq is not a divisor of span then stopfreq
        # will be exceeded by some proportion of stepfreq.
        # Handle any overstep in sweep_continue.
        self._sweep_iterator = self.sweep_iterate(startfreq + stepfreq,
                                            stopfreq + stepfreq, stepfreq)
        self.sweep_continue()

    def sweep_continue(self):
        """ time-share with GUI by returning after one plot """

        if self.sweep_start_reqd:
            # GUI changes flagged a sweep_start is required
            self._callback_id = root.after(1, self.sweep_start)
            return

        try:
            frequency = next(self._sweep_iterator)
        except StopIteration:
            # should never happen, prove it
            assert False
            self.sweep_end()
        else:
            # correct any overstep
            if frequency > self._emit_stopfreq:
                frequency = self._emit_stopfreq

            # Reset immediately before setting frequency
            self.dds.reset()
            # program the DDS to output the required frequency
            self.dds.set_frequency(frequency)
            # take a reading at the required frequency
            reading = self.adc.read()

            #if not self.memstore.get() and self.memstore_valid:
            if not self.memstore.get():
                # memory store disabled
                if frequency in self.line_buffer:
                    # erase the part trace
                    try:
                        lineID = self.line_buffer[frequency]
                        canvas.delete(lineID)
                    except:
                        raise ProgramError('Program error')

            # optionally record trace sweep data for later saving to file
            # FIXME: this should be immutable during a sweep
            if self.record.get():
                ddu = { frequency : reading }
                self.buf_data.update(ddu)
                #print('Record:{}'.format(ddu))

            # calculate x co-ordinate from the reading
            xend = int((self.x1 * frequency) - self.x2)
            # calculate y co-ordinate from the reading
            yend = int(self.y1 - (reading * self.y2))

            # restrict plotting range to within graticule display area, any
            # out-of-bounds plotting will also show up on any saved images
            if (self.ystart > self.mrgnTop) and (yend < self.mrgnTop):
                # plotting up the display, clamp the end
                yend = self.mrgnTop
            elif (self.ystart < self.mrgnTop) and (yend > self.mrgnTop):
                # plotting down the display, clamp the start
                self.ystart = self.mrgnTop

            # plot the trace line
            if (self.ystart > self.mrgnTop) or (yend > self.mrgnTop):
                # both ends are in range, one may have been clamped
                lineID = canvas.create_line(self.xstart, self.ystart,
                    xend, yend, fill = self._emit_colour, tag = 'plot')

                # record the trace handle for later individual removal
                self.line_buffer.update({frequency : lineID})

                canvas.update_idletasks()

            self.xstart = xend
            self.ystart = yend

            if frequency < self._emit_stopfreq:
                self._callback_id = root.after(1, self.sweep_continue)
            else:
                self.sweep_end()

    def sweep_end(self):
        # completed a full sweep

        canvas.tag_bind('plot', "<1>", self.mouse_leftdown)
        canvas.tag_bind('plot', "<B1-ButtonRelease>", self.mouse_leftup)

        if not (self.memstore.get() or self.cls.get()):
            # memort store disabled, flag for trace erasure
            self.memstore_valid = True

        if self.colcyc.get():
            # cycle to next colour
            self.colour_next()

        if self.record.get():
            # completed pass with record enabled
            self.record_valid = True

        # FIXME: flush recorded 'buf_data' data as a set to file
        # ready for next sweep.
        # The next sweep will use the same 'frequency' key values
        # and would otherwise overwrite the data.
        # Alternatively save data as multiples of 'plot sets'

        if self.oneflag:
            # single sweep completed
            self.single_stop()
        else:
            # schedule a fresh sweep
            self._callback_id = root.after(1, self.sweep_start)

    def sweep_iterate(self, start, finish, step):
        for freq in range(start, finish, step):
            yield freq

    def single_stop(self):
        self.b_sweep['text'] = 'Sweep'
        self.b_sweep['command'] = self.single_sweep
        self.b_action.config(state = NORMAL)
        self.b_save.config(state = NORMAL)
        #tstop = time.time()
        #print(str(int(tstop) - int(tstart)))

    def cycle_stop(self):
        self.b_action['text'] = 'Cycle'
        self.b_action['command'] = self.cycle_sweep
        self.b_sweep.config(state = NORMAL)
        # change cycling to single sweep
        self.oneflag = True
        self.b_sweep['text'] = 'Abort'
        self.b_sweep['command'] = self.abort_sweep
        self.b_action.config(state = DISABLED)

    def single_sweep(self):
        """ start single sweep """
        #tstart = time.time()
        self.oneflag = True
        self.b_sweep['text'] = 'Abort'
        self.b_sweep['command'] = self.abort_sweep
        self.b_action.config(state = DISABLED)
        self.b_save.config(state = DISABLED)
        self.sweep_start()

    def cycle_sweep(self):
        """ start cyclic sweeps """
        self.oneflag = False
        self.b_action['text'] = 'Stop'
        self.b_action['command'] = self.cycle_stop
        self.b_sweep.config(state = DISABLED)
        self.b_save.config(state = DISABLED)
        self.sweep_start()

    def reset(self):
        """ reset everything """
        root.after_cancel(self._callback_id)
        self.dds.reset()
        self.sweep_start_reqd = True
        self.clearscreen()
        self.record_valid = False
        self.buf_data.clear()
        self.memstore_reset()
        self.b_action['text'] = 'Cycle'
        self.b_action['command'] = self.cycle_sweep
        self.b_sweep.config(state = NORMAL)
        self.b_sweep['text'] = 'Sweep'
        self.b_sweep['command'] = self.single_sweep
        self.b_action.config(state = NORMAL)
        self.b_save.config(state = DISABLED)

    def abort_sweep(self):
        self.reset()

    def invalid_sweep(self):
        """ stop and reset the runtime variables """
        root.after_cancel(self._callback_id)
        self.dds.reset()
        #self.oneflag = False
        self.b_action['text'] = 'Cycle'
        self.b_action['command'] = self.cycle_sweep
        self.b_sweep.config(state = NORMAL)
        self.b_sweep['text'] = 'Sweep'
        self.b_sweep['command'] = self.single_sweep
        self.b_action.config(state = NORMAL)

    def mouse_leftdown(self, event):
        # calculate frequency from the x co-ordinate
        # x2 = ((chrtWid * (startfreq / span)) - mrgnLeft)
        # x1 = (chrtWid / span)
        # x = int((x1 * frequency) - x2)
        # frequency = (x + x2) / x1
        f = int((event.x + self.x2) / self.x1)
        # calculate voltage reading from the y co-ordinate
        # self.y2 = (self.chrtHt / plotscale)
        # self.y1 = (self.chrtHt + self.mrgnTop + (plotbias * self.y2))
        # y = int(self.y1 - (reading * self.y2))
        # voltage = (y1 - y) / y2
        v = ((self.y1 - event.y) / self.y2) / self._emit_gain
        vhstr = 'Volts:{}\nHertz:{}'.format(v, f)
        # FIXME: automate font colour to contrast canvBg
        canvas.create_text(event.x, event.y - 15, anchor = CENTER,
                                    fill = 'white', font = self.text_font,
                                            text = vhstr, tag = 'vhtext')

    def mouse_leftup(self, event):
        canvas.delete('vhtext')

    def colour_iterate(self):
        """ generator for colour options """
        for key, colour in self._colour_option.items():
            self._colour_cycle = colour
            yield key

    def colour_cycle(self):
        """ Return the next key in the colour cycle. """
        while True:
            try:
                key = next(self._colour_iterator)
                break
            except StopIteration:
                # hit the end, restart afresh at the beginning
                self._colour_iterator = self.colour_iterate()
            except TypeError:
                # _colour_iterator is invalid
                self._colour_iterator = self.colour_iterate()
                # we should self.colour_sync()
        return key

    def colour_sync(self):
        """ Syncronise the colour cycle to the User selected colour. """
        while self._colour_cycle != self.colour.get():
            self.colour_cycle()

    def colour_next(self):
        """ Set the active colour to the next colour in the cycle. """
        key = self.colour_cycle()
        # Be careful, select() not invoke()
        self._colour_button[key].select()

    def memstore_reset(self):
        """
        Wipe the memory store and flag as invalid.

        Any references to previous trace sweep data is erased.
        NOTE: the trace plot is not removed from the canvas.
        """
        self.memstore_valid = False
        self.line_buffer.clear()

    # FIXME: not enough try's
    def save_canvas(self):
        self.b_action.config(state = DISABLED)
        self.b_sweep.config(state = DISABLED)
        self.b_reset.config(state = DISABLED)
        self.b_save.config(state = DISABLED)
        filename = filedialog.asksaveasfilename()
        if filename:
            fname, fext = os.path.splitext(filename)
            if fext == '.pdf':
                ftemp = tempfile.NamedTemporaryFile()
                canvas.postscript(file = ftemp.name, colormode = 'color')
                ftemp.seek(0)
                if self.reformat_ps(ftemp.name):
                    ftemp.seek(0)
                    try:
                        process = subprocess.Popen(['/usr/bin/ps2pdf',
                                                        ftemp.name, filename])
                    except OSError:
                        ftemp.close()
                        messagebox.showerror('Conversion Error',
                                        'please check "ps2pdf" is installed')
                    else:
                        process.wait()
                        ftemp.close()
                else:
                    ftemp.close()
            elif fext == '.ps':
                fn_ps = fname + '.ps'
                canvas.postscript(file = fn_ps, colormode = 'color')
                self.reformat_ps(fn_ps)
            else:
                messagebox.showerror('Bad file extension',
                                            'Please specify ".ps" or ".pdf"')

        self.b_action.config(state = NORMAL)
        self.b_sweep.config(state = NORMAL)
        self.b_reset.config(state = NORMAL)
        self.b_save.config(state = NORMAL)

    def reformat_ps(self, fn_ps):
        """
        enlargen the postscript pixelsize

        The canvas.postscript documentation related to the definition
        of fonts is vague at best. Until fonts can be controlled by
        the correct method, live with whatever font type ghostscript
        chooses to use, but change the font size to make it readable.
        """
        pixelsize = self.text_font[1]
        args = [ '/bin/sed', '-i']
        args.extend([ '-e', 's/findfont ' + pixelsize + '/findfont 12/g'])
        args.extend([fn_ps])
        try:
            process = subprocess.Popen(args)
        except OSError:
            messagebox.showerror('Undefined Error', 'an error ocurred')
            return False
        else:
            process.wait()
        return True

    def exit(self):
        """ tidy up and exit """
        #FIXME: this needs refinement re RPi.GPIO library
        # should RPi.GPIO be handled here by WobbyPi or in
        # the ADC & DDS libraries as it is now ?
        # if dds.exit() shuts down RPi.GPIO it is no longer
        # available to adc.exit().
        self.dds.exit()
        self.adc.exit()
        root.destroy()
        
        
# Assign TK to root
root = Tk()
# Set main window title and menubar
root.wm_title('RPi Wobbulator ' + version)
# Create instance of class WobbyPi
app = WobbyPi(root, params)
app.makemenu(root)
app.initialise()
# Start main loop and wait for input from GUI
root.mainloop()

# When program stops, save user parameters
paramFile = open(paramFN, "wb")
params['version'] = version
params['chrtHt'] = app.chrtHt
params['chrtWid'] = app.chrtWid
params['xDivs'] = app.xDivs
params['yDivs'] = app.yDivs
params['canvFg'] = app.canvFg
params['canvBg'] = app.canvBg
params['fBegin'] = str(app.fstart.get())
params['fEnd'] = str(app.fstop.get())
params['fIntvl'] = str(app.fstep.get())
params['vgain'] = str(app._gain_option[app.gainval.get()])
params['vchan'] = str(app._ipchan_option[app.ipchan.get()])
params['colour'] = app.colour.get()
params['cc'] = str(app.colcyc.get())
params['ms'] = str(app.memstore.get())
params['rec'] = str(app.record.get())
params['cls'] = str(app.cls.get())
params['grid'] = str(app.graticule.get())
params['bits'] = str(app._bitres_option[app.bitval.get()])
params = pickle.dump(params, paramFile)
paramFile.close()

