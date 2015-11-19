#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim:ai:sw=4:ts=8:et:fileencoding=utf-8
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
import math

# import GUI module
from tkinter import *
from tkinter import messagebox
from tkinter import colorchooser
from tkinter import filedialog
from tkinter import simpledialog

from copy import deepcopy

import tempfile
import subprocess
import os


# ---- get user preferences or set defaults ----
# for param file persistence, import faster cPickle if available
try:
    import cPickle as pickle
except:
    import pickle

version = '2.7-004'

params = {}

def default_parameters():
    print('Loading default settings')
    params['version'] = version
    params['chrtHt1'] = 480
    params['chrtHt2'] = 480
    params['chrtWid'] = 500
    params['xDivs'] = 10
    params['yDivs1'] = 10
    params['yDivs2'] = 12
    params['canvFg'] = 'black'
    params['canvBg'] = '#00a4a4'
    params['fBegin'] = 0
    params['fEnd'] = 30000000
    params['fIntvl'] = 60000
    params['vgain'] = 1
    params['vchan'] = 1
    params['colour'] = 'red'
    params['ms'] = 0
    params['as'] = 0
    params['rec'] = 0
    params['cc'] = 0
    params['cls'] = 0
    params['grid'] = 1
    params['bits'] = 16
    params['ddsclk'] = 125000000
    params['ddsmul'] = 0

paramFN = 'wobbypi.pkl'
try:
    paramFile = open(paramFN,"rb")
except IOError:
    default_parameters()
else:
    try:
        params = pickle.load(paramFile)
    except EOFError:
        print('Parameter File Error: Corrupted')
        default_parameters()
    finally:
        paramFile.close()

    """
    try:
        if params['version'] != version:
            raise
    except:
        default_parameters()
    """
    if params['version'] != version:
        print('Parameter File Error: Incorrect Version')
        default_parameters()

# print (params)


# Class definition for WobbyPi application
class WobbyPi():

    trace_state = {}
    trace_set = {}
    trace_list = []

    marker_list = []
    marker_redraw_list = []

    line_buffer = {}
    line_list = []

    undo_list = []

    # ghostscript will change the font family but keep the pixelsize
    text_font = ('clean','8')

    #options_option = {0:[IntVar, 'Gr', 1, 0, self.grid, self.graticule_update],
    #                  1:[IntVar, 'Cls', 1, 0, self.cls, ()],
    #                    }

    _ipchan_option = {0:1, 1:2, 2:3, 3:4}
    _gain_option = {0:1, 1:2, 2:4, 3:8}
    _bitres_option = {0:12, 1:14, 2:16, 3:18}
    _colour_option = {0:'red', 1:'yellow', 2:'magenta', 3:'green', 4:'blue'}

    _colour_button = {}
    _colour_iterator = ()
    _colour_cycle = ''

    _sweep_iterator = ()

    _callback_id = 0

    _imm_startfreq = 0
    _imm_stopfreq = 0
    _imm_stepfreq = 0
    _imm_ipchan = 0
    _imm_gain = 0
    _imm_colour = 0
    _imm_bitres = 0

    # Build Graphical User Interface
    def __init__(self, master, params):

        if _has_wobbulator:
            from Wobby.ADC import ADC as WobbyADC
            self.adc = WobbyADC()
            from Wobby.DDS import DDS as WobbyDDS
            self.dds = WobbyDDS()

        optiontkfonts = ['TkCaptionFont', 'TkSmallCaptionFont', 'TkTooltipFont',
                                'TkFixedFont', 'TkHeadingFont', 'TkMenuFont',
                                'TkIconFont', 'TkTextFont', 'TkDefaultFont']

        for opt in optiontkfonts:
            root.tk.call('font', 'configure', opt, '-family', self.text_font[0],
                                                    '-size', self.text_font[1])

        frame = Frame(master, bd=10)
        frame.pack(fill=BOTH,expand=1)

        # system values
        self.mrgnLeft = 56
        self.mrgnRight = 20
        self.mrgnTop = 30
        self.mrgnBotm = 35

        # user values
        self.canvFg = params['canvFg']
        self.canvBg = params['canvBg']
        self.chrtHt1 = int(params['chrtHt1'])
        self.chrtHt2 = int(params['chrtHt2'])
        self.chrtWid = int(params['chrtWid'])
        self.xDivs = params['xDivs']
        self.yDivs1 = params['yDivs1']
        self.yDivs2 = params['yDivs2']
        self.fBegin = params['fBegin']
        self.fEnd = params['fEnd']
        self.fIntvl = params['fIntvl']
        self.ddsclkfreq = params['ddsclk']
        self.ddsclkmul = params['ddsmul']

        # trivial design changes
        # C2 + C3 1nF <> 100nF [drop channel 2 input 3dB corner frequency to 30kHz]
        # C9 <> add 1M Ohm parallel resistor [improve channel 1 decay slew rate]
        # IC1 Pin4 <> add 100nF to ground [improve sampling & reduce noise injection]
        # R12 <> replaced with shorting link [improve square wave output]
        # R5 removed <> output impedance [device under test is the load]
        # other potential design changes
        # VR1, R4, C5, C7, D1, D2, R4  <> replace voltage doubler circuitry for
        # peak voltage detector [improve channel 1 sensitivity and dynamic range]
        # R6 <> increase output drive [increased DUT dynamic range]

        # Working Parameters Setup
        # The Wobbulator AD8307 LogAmp has a dynamic range of 92dB, extending
        # from -75dBm to +17dBm when used without an input matching network.
        # So the 'Intercept' (0 Volt output) is at -75 dBm.
        self.dBm_offset = -75

        # The following parameter values are inter-dependant on each other
        # and on the fixed offset value.

        # The Wobbulator provides a 3.3V supply to the AD8307 LogAmp.
        # This limits the AD8307 LogAmp maximum output to approx 2.0v.
        # The Wobbulator AD8307 LogAmp output directly drives the
        # MCP3424 ADC which has an input voltage ceiling of 2.0V.

        # The Wobbulator AD8307 LogAmp is non-linear for outputs below 0.5V.
        # This could be resolved in software by creating a 'compensation table'
        # but currently isn't.
        # The Wobbulator AD8307 LogAmp has no power supply decoupling, no
        # output decoupling, no screening, and no input filtering. The result
        # is a very high noise floor, limiting the useful minimum input.
        # This noise level can exceed -50dBm.
        # Selected a bias value (not less than 0.5V) for a -50dBm start.
        # VdBm_bias = abs(dBm_start - dBm_offset) * VdBm
        self.VdBm_bias = 0.5

        # The Wobbulator AD8307 LogAmp has a 50 Ohm 0805 SMD across the
        # input which can handle an estimated input of 0.1W, which is a
        # maximum input of 20 dBm.

        # The Wobbulator AD8307 LogAmp is provided with a 3.3V supply.
        # With an unbalanced input the largest signal that can be handled by
        # the AD8307 LogAmp when operating from a 3V supply is +10dBm (sine
        # amplitude of ±1 V) +16dBm could have been handled using a 5V supply.
        # The Wobbulator AD9850 DDS Module has a maximum output of
        # approximately -8 dBm when supplied with 3.3v.
        # Selected a end scale of +10dBm giving 60dB range for a -50dBm start.
        dBm_end = 10

        # The Wobbulator AD8307 LogAmp Slope 'Volts per dBm' is calibrated
        # by VR2, the approxmate adjustment range is from 11mV to 22mV.
        # Selected 20mV.
        self.VdBm = 0.02

        #self.VdBm_bias = abs(self.dBm_start - self.dBm_offset) * self.VdBm

        self.dBm_start = round(self.volts_dBm(self.VdBm_bias), 6)
        self.dBm_range = abs(self.dBm_start - dBm_end)
        # Simplify:  dBm_scale = dBm_range / (1 / VdBm)
        self.dBm_scale = self.dBm_range * self.VdBm

        self.dBm_validate()

        # setup canvas to display results
        global canvas
        self.canvHt = self.mrgnTop + max(self.chrtHt1, self.chrtHt2) + self.mrgnBotm
        self.canvWid = self.mrgnLeft + self.chrtWid + self.mrgnRight
        canvas = Canvas(frame, width = self.canvWid, height = self.canvHt,
                                                            bg = self.canvBg)
        canvas.grid(row = 0, column = 0, columnspan = 6, rowspan = 7)

        # Input channel
        fr_ipchan = LabelFrame(frame, text = 'Input', labelanchor = 'n')
        fr_ipchan.grid(row = 0, column = 6)

        self.ipchan = IntVar()
        for key, ipchan in self._ipchan_option.items():
            txt = str(ipchan)
            rb = Radiobutton(fr_ipchan, text = txt, value = ipchan,
                                                variable = self.ipchan,
                                                command = self.ipchan_update)
            rb.grid(row = key, sticky = 'w')
            if int(params['vchan']) == ipchan:
                rb.select()
            if not _has_wobbulator:
                rb.configure(state = 'disabled')

        # Input gain
        fr_gain = LabelFrame(frame, text = 'Gain', labelanchor = 'n')
        fr_gain.grid(row = 1, column = 6)

        self.gain = IntVar()
        for key, gain in self._gain_option.items():
            txt = 'x ' + str(gain)
            rb = Radiobutton(fr_gain, text = txt, value = gain,
                                                variable = self.gain,
                                                command = self.gain_update)
            rb.grid(row = key, sticky = 'w')
            if int(params['vgain']) == gain:
                rb.select()
            if not _has_wobbulator:
                rb.configure(state = 'disabled')

        # Bit resolution 18Bit, 16Bit, 14Bit, 12Bit
        fr_bitres = LabelFrame(frame, text = 'BPS', labelanchor = 'n')
        fr_bitres.grid(row = 2, column = 6)

        self.bitres = IntVar()
        for key, bitres in self._bitres_option.items():
            txt = str(bitres)
            rb = Radiobutton(fr_bitres, text = txt, value = bitres,
                                                variable = self.bitres,
                                                command = self.bitres_update)
            rb.grid(row = key, sticky = 'w')
            if int(params['bits']) == bitres:
                rb.select()
            if not _has_wobbulator:
                rb.configure(state = 'disabled')

        # Colour of trace
        fr_colour = LabelFrame(frame, text = 'Colour', labelanchor = 'n')
        fr_colour.grid(row = 3, column = 6)

        self.colour = StringVar()
        # rb.invoke() below is dependant on self.colcyc
        self.colcyc = IntVar()
        for key, colour in self._colour_option.items():
            txt = '[' + colour[0].upper() + ']'
            rb = Radiobutton(fr_colour, fg = colour, text = txt, value = colour,
                                                variable = self.colour,
                                                command = self.colour_update)
            rb.grid(row = key, sticky = 'w')
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

        # enable\disable auto-step
        self.autostep = IntVar()
        cb_autostep = Checkbutton(fr_cb, text = 'AS', onvalue = 1, offvalue = 0,
                                                variable = self.autostep,
                                                command = self.autostep_update)

        # enable\disable colour cycling of trace
        cb_colcyc = Checkbutton(fr_cb, text = 'CC', onvalue = 1, offvalue = 0,
                                                   variable = self.colcyc,
                                                   command = self.colour_update)

        cb_graticule.grid(row = 0, column = 0, sticky = 'w')
        cb_clear.grid(row = 1, column = 0, sticky = 'w')
        cb_record.grid(row = 2, column = 0, sticky = 'w')
        cb_memstore.grid(row = 3, column = 0, sticky = 'w')
        cb_autostep.grid(row = 4, column = 0, sticky = 'w')
        cb_colcyc.grid(row = 5, column = 0, sticky = 'w')

        if int(params['grid']) == 1:
            cb_graticule.select()
        if int(params['cls']) == 1:
            cb_clear.select()
        if int(params['rec']) == 1:
            cb_record.select()
        if int(params['ms']) == 1:
            cb_memstore.select()
        if int(params['as']) == 1:
            cb_autostep.select()
        if int(params['cc']) == 1:
            cb_colcyc.select()

        # user description space
        fr_desc = Label(frame, text = 'Desc.')
        fr_desc.grid(row = 7, column = 0, columnspan = 1)

        self.desc = StringVar()
        e_desc = Entry(frame, width = 66, textvariable = self.desc)
        e_desc.grid(row = 7, column = 1, columnspan = 4)
        e_desc.bind('<Key-Return>', self.desc_update)
        e_desc.insert(0, 'Mouse (Left-Click)\(Right-Click-Hold-And-Move) on sweep trace')
        self.desc_update()

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
        e_startf.bind('<Key-Return>', self.freq_update)

        # stop frequency for sweep
        self.fstop = StringVar()
        fr_stopf = Label(fr_freq, text = ' Stop:')
        fr_stopf.grid(row = 0, column = 2)
        e_stopf = Entry(fr_freq, textvariable = self.fstop, width = 8)
        e_stopf.grid(row = 0, column = 3)
        e_stopf.insert(0, self.fEnd)
        e_stopf.bind('<Key-Return>', self.freq_update)

        # increment for sweep
        fr_stepf = Label(fr_freq, text = ' Step:')
        fr_stepf.grid(row = 0, column = 4)
        self.fstep = StringVar()
        self.e_stepf = Entry(fr_freq, textvariable=self.fstep, width = 8)
        self.e_stepf.grid(row = 0, column = 5)
        self.e_stepf.insert(0, self.fIntvl)
        self.e_stepf.bind('<Key-Return>', self.step_update)

        # control panel frame
        fr_control = LabelFrame(frame, text = 'Control', labelanchor = 'n')
        fr_control.grid(row = 8, column = 4, columnspan = 3)

        # Button to reset settings
        self.b_reset = Button(fr_control, text = 'Reset', height = 1, width = 3,
                                                    activeforeground = 'red',
                                                    command = self.reset_sweep)
        # Button to start a single sweep
        self.b_sweep = Button(fr_control, text = 'Sweep', height = 1, width = 3,
                                                    activeforeground='red',
                                                    command=self.single_sweep)
        # Button to start multiple sweeps
        self.b_action = Button(fr_control, text = 'Cycle', height = 1, width = 3,
                                                    activeforeground = 'red',
                                                    command = self.cycle_sweep)
        # Button to undo
        self.b_undo = Button(fr_control, text = 'Undo', height = 1, width = 3,
                                    activeforeground = 'red', state = DISABLED,
                                                    command = self.undo)

        # Button to save image
        self.b_save = Button(fr_control, text = 'Save', height = 1, width = 3,
                                    activeforeground = 'red', state = DISABLED,
                                                    command = self.save_canvas)

        self.b_reset.grid(row = 0, column = 0)
        self.b_sweep.grid(row = 0, column = 1)
        self.b_action.grid(row = 0, column = 2)
        self.b_undo.grid(row = 0, column = 3)
        self.b_save.grid(row = 0, column = 4)

        if not _has_wobbulator:
            self.b_action.configure(state = 'disabled')
            self.b_sweep.configure(state = 'disabled')
            self.b_reset.configure(state = 'disabled')
            self.e_stepf.configure(state = 'disabled')
            e_stopf.configure(state = 'disabled')
            e_startf.configure(state = 'disabled')
            cb_autostep.configure(state = 'disabled')

        canvas.update_idletasks()

        self._colour_mld_bind = {0:self.mld_red, 1:self.mld_yellow,
                        2:self.mld_magenta, 3:self.mld_green, 4:self.mld_blue}
        self._colour_mrd_bind = {0:self.mrd_red, 1:self.mrd_yellow,
                        2:self.mrd_magenta, 3:self.mrd_green, 4:self.mrd_blue}

    def makemenu(self, win):
        global root
        top = Menu(win)
        win.config(menu = top)    # set its menu option
        self.m_file = m_file = Menu(top, tearoff = 0)
        top.add_cascade(label = 'File', menu = m_file, underline = 0)
        m_file.add_command(label = 'Load', command = self.file_load,
                                        underline = 0, accelerator = 'Ctrl+L')
        m_file.add_command(label = 'Save', command = self.file_save,
                                        underline = 0, accelerator = 'Ctrl+S')
        m_file.add_command(label = 'Export', command = self.file_export,
                                        underline = 0, accelerator = 'Ctrl+E')
        m_file.add_command(label = 'Exit', command = self.exit,
                                        underline = 1, accelerator = 'Ctrl+Q')
        opt = Menu(top, tearoff = 0)
        top.add_cascade(label = 'Settings', menu = opt, underline = 0)
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
        opt.add_separator()
        opt.add_command(label = 'Calibrate dBm', command = self.calibrate,
                                                                underline = 0)
        opt.add_command(label = 'Hardware Config', command = self.hwconfig,
                                                                underline = 0)
        opt.add_separator()
        opt.add_command(label = 'Save settings', command = self.save_params,
                                                                underline = 0)

        help = Menu(top, tearoff = 0)
        top.add_cascade(label = 'Help', menu = help, underline = 0)
        help.add_command(label = 'Controls', command = self.showHelp,
                                                                underline = 0)
        help.add_command(label = 'About Wobbulator', command = self.showAbout,
                                                                underline = 0)
        m_file.entryconfig(1, state = DISABLED)
        m_file.entryconfig(2, state = DISABLED)
        if not _has_wobbulator:
            opt.entryconfig(9, state = DISABLED)
            opt.entryconfig(10, state = DISABLED)
        # Calibration doesn't work, disable for now
        opt.entryconfig(9, state = DISABLED)
        return

    def initialise(self):
        """ Initialise variables, buffers, and state """
        # Synchronise Hardware & GUI state\appearance
        if _has_wobbulator:
            self.ipchan_update()
            self.gain_update()
            self.bitres_update()
            self.dds.set_sysclk(self.ddsclkfreq, self.ddsclkmul)
        else:
            self.b_action.config(state = DISABLED)
            self.b_sweep.config(state = DISABLED)
            self.b_reset.config(state = DISABLED)
            self.reflect_save_state(False)
            # FIXME: unsatisfactory duplication here
            if self.ipchan.get() == 2:
                self.chrtHt = self.chrtHt2
                self.yDivs = self.yDivs2
            else:
                self.chrtHt = self.chrtHt1
                self.yDivs = self.yDivs1
            self.set_subDivs()
        self.fresh_canvas()
        self.colour_sync()
        self.sweep_start_reqd = True
        self.memstore_reset()
        # <MouseWheel> = <Button-4> and <Button-5>#

        for key, val in self._colour_mld_bind.items():
            tag = 'p_' + self._colour_option[key]
            canvas.tag_bind(tag, "<1>", val)
            canvas.tag_bind(tag, "<B1-ButtonRelease>", self.mlu_common)
        for key, val in self._colour_mrd_bind.items():
            tag = 'p_' + self._colour_option[key]
            canvas.tag_bind(tag, "<3>", val)
            canvas.tag_bind(tag, "<B3-Motion>", self.mrd_movement)
            canvas.tag_bind(tag, "<B3-ButtonRelease>", self.mru_common)
        return

    def dBm_validate(self):
        # FIXME: finish me
        msg = ""
        if self.VdBm <= 0.01 or self.VdBm >= 0.023:
            msg = 'ERROR: Out of range (VdBm {})'.format(self.VdBm)
        if self.dBm_start < -65:
            msg += 'ERROR: Out of range (dBm_start {})'.format(self.dBm_start)
        if self.dBm_start + self.dBm_range > 10:
            msg += 'ERROR: Out of range (dBm_start {}, dBm_range {})'.format(
                                                self.dBm_start, self.dBm_range)
        if self.VdBm_bias <= 0.2:
            msg = 'ERROR: Out of range (VdBm_bias {})'.format(self.VdBm_bias)
        if self.dBm_offset != -75:
            msg = 'ERROR: Out of range (dBm_offset {})'.format(self.dBm_offset)
        if msg:
            print(msg)
            sys.exit()

        #msg = 'VdBm {}, dBm_scale {}, dBm_start {}, dBm_range {}'.format(
        #            self.VdBm, self.dBm_scale, self.dBm_start, self.dBm_range)
        #print(msg)

    def roundup(self, dividend, divisor):
        if dividend % divisor != 0:
            dividend += divisor - dividend % divisor
        return dividend

    def gcd(self, x, y):
        """ Euclidean Algorithm to find the greatest common divisor """
        while y:
            x, y = y, x % y
        return x

    def not_done(self):
        messagebox.showerror('Not implemented', 'Not yet available')
        return

    def showHelp(self):
        helpmsg = "\
\nInput: [ 1 2 3 4 ]\n\
- select the active input channel\n\
\nGain: [ x1 x2 x4 x8 ]\n\
- select input gain amplification\n\
\nBPS: [ 18 16 14 12 ]\n\
- bits per sample\n\
\nColour: [ R Y M G B ]\n\
- colour used to display trace\n\
  Red Yellow Magenta Green Blue\n\
\nOptions:\n\
[Gr]  - Graticule display\n\
[Cls] - Clear display at sweep start\n\
[Rec] - Record sweep trace data\n\
[MS]  - Memory Store display\n\
[AS]  - Auto-Step completion\n\
[CC]  - Colour Cycle after sweep\n\
"
        messagebox.showinfo('Help', helpmsg)
        return

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
        return

    def getForegroundColor(self):
        fgColor = colorchooser.askcolor(params['canvFg'],
                                            title = 'Foreground Color')
        if fgColor[1] != 'None':
            # params['canvFg'] = fgColor[1]
            self.canvFg = fgColor[1]
        return

    def getBackgroundColor(self):
        bgColor = colorchooser.askcolor(params['canvBg'],
                                            title = 'Background Color')
        if bgColor[1] != 'None':
            # params['canvBg'] = bgColor[1]
            self.canvBg = bgColor[1]
            canvas.configure(background=self.canvBg)
        return

    def getChartWidth(self):
        chrtWid = simpledialog.askinteger('Chart Width', '300 to 1000',
                                            initialvalue = params['chrtWid'],
                                            minvalue = 300, maxvalue = 1000)
        if chrtWid != 'None':
            # params['chrtWid'] = chrtWid
            self.chrtWid = chrtWid
        # FIXME: duplication
        self.canvHt = self.mrgnTop + max(self.chrtHt1, self.chrtHt2) + self.mrgnBotm
        self.canvWid = self.mrgnLeft + self.chrtWid + self.mrgnRight
        canvas.config(width = self.canvWid, height = self.canvHt)
        self.reset_common()
        return

    def getChartHeight(self):
        """
        if self.ipchan.get() == 2:
            chrtHt = simpledialog.askinteger('Chart Height', '300 to 1000',
                                            initialvalue = params['chrtHt2'],
                                            minvalue = 300, maxvalue = 1000)
            if chrtHt != 'None':
                # params['chrtHt2'] = chrtHt
                self.chrtHt2 = chrtHt
        else:
            chrtHt = simpledialog.askinteger('Chart Height', '300 to 1000',
                                            initialvalue = params['chrtHt1'],
                                            minvalue = 300, maxvalue = 1000)
            if chrtHt != 'None':
                # params['chrtHt1'] = chrtHt
                self.chrtHt1 = chrtHt
        """
        chrtHt = self.chrtHt
        yDivs = self.yDivs
        while True:
            k = self.yDivs * self.subDivs
            k = self.gcd(self.chrtHt, self.yDivs)
            chrtHt = simpledialog.askinteger('Chart Height', 'multiples of {}'.format(k),
                                        initialvalue = self.chrtHt,
                                        minvalue = 300, maxvalue = 1000)
            if chrtHt == 'NoneType':
                #chrtHt = self.chrtHt
                return

            yDivs = simpledialog.askinteger('Y-divisions', '6-60',
                                    initialvalue = self.yDivs,
                                    minvalue = 6, maxvalue = 60)
            if yDivs == 'NoneType':
                #yDivs = self.yDivs
                return

            if chrtHt % yDivs == 0:
                break;

        if self.ipchan.get() == 2:
            self.chrtHt2 = chrtHt
            self.yDivs2 = yDivs
        else:
            self.chrtHt1 = chrtHt
            self.yDivs1 = yDivs
        self.set_subDivs()
        self.chrtHt = chrtHt
        self.yDivs = yDivs
        # FIXME: duplication
        self.canvHt = self.mrgnTop + max(self.chrtHt1, self.chrtHt2) + self.mrgnBotm
        self.canvWid = self.mrgnLeft + self.chrtWid + self.mrgnRight
        canvas.config(width = self.canvWid, height = self.canvHt)
        self.reset_common()
        return

    def getXdivisions(self):
        xDivs = simpledialog.askinteger('X-divisions', '10-50',
                                            initialvalue = params['xDivs'],
                                            minvalue = 10, maxvalue = 50)
        if xDivs != 'None':
            # params['xDivs'] = xDivs
            self.xDivs = xDivs
        return

    def getYdivisions(self):
        if self.ipchan.get() == 2:
            yDivs = simpledialog.askinteger('Y-divisions', '6-60',
                                            initialvalue = params['yDivs2'],
                                            minvalue = 6, maxvalue = 60)
            if yDivs != 'None':
                # params['yDivs2'] = yDivs
                self.yDivs2 = yDivs
        else:
            yDivs = simpledialog.askinteger('Y-divisions', '10-50',
                                            initialvalue = params['yDivs1'],
                                            minvalue = 10, maxvalue = 50)
            if yDivs != 'None':
                # params['yDivs1'] = yDivs
                self.yDivs1 = yDivs
        return

    def hwconfig(self):
        #msg = 'Not Yet Implemented'
        #messagebox.showinfo('Wobbulator Configuration', msg)
        ddsclkfreq = simpledialog.askinteger('DDS', 'Xtal Freq (Hz)',
                                        initialvalue = params['ddsclk'],
                                        minvalue = 0, maxvalue = 125000000)
        if ddsclkfreq != 'None':
            self.ddsclkfreq = ddsclkfreq

        ddsclkmul = simpledialog.askinteger('DDS', 'Clock x 6 multiplier (0 or 1)',
                                        initialvalue = params['ddsmul'],
                                        minvalue = 0, maxvalue = 1)
        if ddsclkmul != 'None':
            self.ddsclkmul = ddsclkmul

        if _has_wobbulator:
            self.dds.set_sysclk(self.ddsclkfreq, self.ddsclkmul)
        return

    def save_params(self):
        global params
        params['version'] = version
        params['chrtHt1'] = self.chrtHt1
        params['chrtHt2'] = self.chrtHt2
        params['chrtWid'] = self.chrtWid
        params['xDivs'] = self.xDivs
        params['yDivs1'] = self.yDivs1
        params['yDivs2'] = self.yDivs2
        params['canvFg'] = self.canvFg
        params['canvBg'] = self.canvBg
        params['fBegin'] = str(self.fstart.get())
        params['fEnd'] = str(self.fstop.get())
        params['fIntvl'] = str(self.fstep.get())
        params['vgain'] = str(self.gain.get())
        params['vchan'] = str(self.ipchan.get())
        params['colour'] = self.colour.get()
        params['cc'] = str(self.colcyc.get())
        params['as'] = str(self.autostep.get())
        params['ms'] = str(self.memstore.get())
        params['rec'] = str(self.record.get())
        params['cls'] = str(self.cls.get())
        params['grid'] = str(self.graticule.get())
        params['bits'] = str(self.bitres.get())
        params['ddsclk'] = self.ddsclkfreq
        params['ddsmul'] = self.ddsclkmul

        with open(paramFN, "wb") as paramFile:
            try:
                pickle.dump(params, paramFile)
            except pickle.PicklingError:
                messagebox.showerror('File Error', 'An error occurred')
        return

    def file_load(self):
        ttl = 'Load Wobbulator Trace File'
        ft = (("Wobbulator Trace Files", "*.wtf"),("All files", "*.*"))
        filename = filedialog.askopenfilename(defaultextension = '.wtf',
                                                title = ttl, filetypes = ft)
        if filename:
            fname, fext = os.path.splitext(filename)
            if fext.upper() == '.WTF':
                # wobbulator trace file
                with open(filename, "rb") as dataFile:
                    try:
                        trace_state = pickle.load(dataFile)
                        trace_list = pickle.load(dataFile)
                        marker_list = pickle.load(dataFile)
                    except EOFError:
                        messagebox.showerror('File Error',
                                    'File "{}" is empty!'.format(filename))
                        return
                    except pickle.UnpicklingError:
                        messagebox.showerror('File Error',
                                    'File "{}" is corrupt!'.format(filename))
                        return
                self.trace_init(trace_state, trace_list, marker_list)
            else:
                messagebox.showerror('Bad file extension',
                                    'Only WTF file format is supported\n' + 
                                    'Please specify a ".wtf" suffixed file')
        return

    def file_save(self):
        # disabled file_save instead...
        if len(self.trace_list):
            ttl = 'Save Wobbulator Trace File'
            ft = (("Wobbulator Trace Files", "*.wtf"),("All files", "*.*"))
            filename = filedialog.asksaveasfilename(defaultextension = '.wtf',
                                                title = ttl, filetypes = ft)
            if filename:
                fname, fext = os.path.splitext(filename)
                if fext.upper() == '.WTF':
                    # wobbulator trace file
                    with open(filename, 'wb') as dataFile:
                        try:
                            pickle.dump(self.trace_state, dataFile)
                            pickle.dump(self.trace_list, dataFile)
                            pickle.dump(self.marker_list, dataFile)
                        except pickle.PicklingError:
                            messagebox.showerror('File Error',
                                                        'File is corrupt!')
                            return
                else:
                    messagebox.showerror('Bad file extension',
                                    'Only WTF file format is supported\n' +
                                        'Please specify ".wtf" file suffix')
        else:
            messagebox.showerror('No recorded data',
                    'Record data before attempting save')
        return

    def file_export(self):
        # disabled file_export instead...
        if len(self.trace_list):
            ttl = 'Export Wobbulator Trace File'
            ft = (("Comma Seperated Values", "*.csv"),("All files", "*.*"))
            filename = filedialog.asksaveasfilename(defaultextension = '.csv',
                                                    title = ttl, filetypes = ft)
            if filename:
                fname, fext = os.path.splitext(filename)
                if fext.upper() == ".CSV":
                    import csv
                    with open(filename, 'w', newline='') as f_csv:
                        # FIXME: 'try' harden
                        w = csv.DictWriter(f_csv, sorted(self.trace_list[0].keys()))
                        w.writeheader()
                        w.writerows(self.trace_list)
                else:
                    messagebox.showerror('Bad file extension',
                                    'Only CSV file export is supported\n' +
                                        'Please specify ".csv" file suffix')
        else:
            messagebox.showerror('No recorded data',
                    'Record data before attempting export')
        return

    def exit(self):
        """ exit, tidy up after GUI destruction """
        root.destroy()
        return

    def marker_label(self, event):
        f = self.convf(int((event.x + self.x2) / self.x1))
        v = ((self.y1 - event.y) / (self.y2 * self._imm_gain))
        if self._imm_ipchan != 2:
            return '{0:02.3f} V\n'.format(v) + f
        else:
            # Input Channel 2 (dBm)
            p = self.volts_dBm(v)
            return '{0:02.1f} dBm\n'.format(p) + f

    def place_marker(self, marker_list, colour):
        """ Draw trace mark and related text label """
        # draw text at given x\y co-ordinates
        mtext = self.marker['mtext']
        text_x = self.marker['xtext']
        text_y = self.marker['ytext']
        tag_marker = 'm_' + colour
        itemID = canvas.create_text(text_x, text_y - 20, anchor = CENTER,
                                    fill = colour, font = self.text_font,
                                            text = mtext, tag = tag_marker)
        marker_list.append(itemID)
        # draw trace mark at original x\y co-ordinates
        mx = self.marker['x']
        my = self.marker['y']
        itemID = canvas.create_line(mx - 3, my - 3, mx + 4, my + 4,
                                            fill = colour, tag = tag_marker)
        marker_list.append(itemID)
        itemID = canvas.create_line(mx - 3, my + 3, mx + 4, my - 4,
                                            fill = colour, tag = tag_marker)
        marker_list.append(itemID)
        return

    def movable_mark(self, event):
        """ Move mark text label of an existing mark to new position """
        self.marker['xtext'] = event.x
        self.marker['ytext']  = event.y
        colour = self.canvFg
        ID_list = []
        self.place_marker(ID_list, colour)
        self.undo_list.append([self.undo_marker, ID_list])
        return

    def mrd_common(self, event, colour):
        """ Mouse Right Button Down """
        # Issues with tkinter
        # BUG: depressing right mouse button before releasing
        # left button can cause the left release to be missed.
        # BUG: depressing left mouse button over trace then
        # moving mouse off trace and depressing right button
        # (off trace) invokes mrd_?????, causing a mark to be
        # placed off trace.
        self.mlu_common(event)
        # create mark at current position
        self.marker = {}
        self.marker['mtext'] = self.marker_label(event)
        self.marker['colour'] = colour
        self.marker['x'] = event.x
        self.marker['y'] = event.y
        self.movable_mark(event)
        return

    def mrd_movement(self, event):
        """ Mouse Right Button Down & Movement """
        # erase current mark
        self.undo()
        # redraw mark text at new position
        self.movable_mark(event)
        return

    def mru_common(self, event):
        """ Mouse Right Button Up """
        # erase current mark
        self.undo()
        # redraw mark text at final position in correct colour
        self.marker['xtext'] = event.x
        self.marker['ytext']  = event.y
        self.mru_mark()
        return

    def mru_mark(self):
        # Add the mark to the canvas & lists
        self.marker_list.append(deepcopy(self.marker))
        colour = self.marker['colour']
        ID_list = []
        self.place_marker(ID_list, colour)
        # Require undo the marker list as well as the canvas marker
        self.undo_list.append([self.undo_marker_list, ID_list])
        return

    def marker_list_redraw(self):
        while len(self.marker_redraw_list):
            self.marker = self.marker_redraw_list.pop()
            # Add the mark to the canvas & lists
            self.mru_mark()
        return

    def mrd_red(self, event):
        """ Mouse Right Button Down on red trace"""
        self.mrd_common(event, 'red')
        return

    def mrd_yellow(self, event):
        """ Mouse Right Button Down on yellow trace"""
        self.mrd_common(event, 'yellow')
        return

    def mrd_magenta(self, event):
        """ Mouse Right Button Down on magenta trace"""
        self.mrd_common(event, 'magenta')
        return

    def mrd_green(self, event):
        """ Mouse Right Button Down """
        self.mrd_common(event, 'green')
        return

    def mrd_blue(self, event):
        """ Mouse Right Button Down """
        self.mrd_common(event, 'blue')
        return

    def mlu_common(self, event):
        """ Mouse Left Button up """
        canvas.delete('vhtext')

    def mld_common(self, event, colour):
        """ Mouse Left Button Down """
        vhstr = self.marker_label(event)
        canvas.create_text(event.x, event.y - 20, anchor = CENTER, 
            font = self.text_font, fill = colour, text = vhstr, tag = 'vhtext')
        canvas.create_line(event.x - 3, event.y - 3,
                        event.x + 4, event.y + 4, fill = colour, tag = 'vhtext')
        canvas.create_line(event.x - 3, event.y + 3,
                        event.x + 4, event.y - 4, fill = colour, tag = 'vhtext')
        return

    def mld_red(self, event):
        """ Mouse Left Button Down """
        self.mld_common(event, 'red')
        return

    def mld_magenta(self, event):
        """ Mouse Left Button Down """
        self.mld_common(event, 'magenta')
        return

    def mld_yellow(self, event):
        """ Mouse Left Button Down """
        self.mld_common(event, 'yellow')
        return

    def mld_green(self, event):
        """ Mouse Left Button Down """
        self.mld_common(event, 'green')
        return

    def mld_blue(self, event):
        """ Mouse Left Button Down """
        self.mld_common(event, 'blue')
        return

    def calibrate(self):
        msg = 'Not Yet Implemented'
        messagebox.showinfo('Wobbulator Calibration', msg)
        return

    def volts_dBm(self, volts):
        """ convert the AD8307 milli-volt representation to dBm """
        # (volts / volts per dBm) + dBm @ 0v
        return ((volts / self.VdBm) + self.dBm_offset)

    def dBm_volts(self, dBm):
        """ convert dBm to the AD8307 milli-volt representation """
        return ((dBm - self.dBm_offset) * self.VdBm)

    def fresh_canvas(self):
        """ reclaim and re-draw canvas area """
        self.memstore_reset()
        self.trace_erase()
        self.label_yscale()
        self.label_xscale()
        self.graticule_update()
        self.desc_update()
        # clear associated lists
        self.undo_list_reset()
        self.line_list_reset()
        self.trace_list_reset()
        self.marker_list_reset()
        return

    def graticule_update(self):
        """ reclaim and re-draw graticule or label border """
        canvas.delete('graticule')
        ydatum = self.mrgnTop - 1
        xdatum = self.mrgnLeft
        # FIXME: this algorithm does not scale
        if self.graticule.get():

            # coarse division horizontal lines
            xend = xdatum + self.chrtWid
            ystep = int(self.chrtHt/self.yDivs)
            for y in range(ydatum, ydatum + self.chrtHt + 1, ystep):
                canvas.create_line(xdatum, y, xend, y, fill = self.canvFg,
                                                            tag = 'graticule')

            # coarse division vertical lines
            #yend = ydatum + self.chrtHt
            yend = y
            xstep = int(self.chrtWid / self.xDivs)
            for x in range(xdatum, xdatum + self.chrtWid + 1, xstep):
                canvas.create_line(x, ydatum, x, yend, fill = self.canvFg,
                                                            tag = 'graticule')

            # fine divisions along x and y centres only
            # fine division horizontal lines along vertical axis
            x = xdatum + int(self.chrtWid / 2)
            xs = x - 4
            xe = x + 5

            ystep = int(ystep / self.subDivs)
            for y in range(ydatum + ystep,
                                ydatum + self.chrtHt + 1 - ystep, ystep):
                canvas.create_line(xs, y, xe, y, fill = self.canvFg,
                                                            tag = 'graticule')

            # fine division vertical lines along horizontal axis
            y = ydatum + int(self.chrtHt / 2)
            ys = y - 4
            ye = y + 5
            xstep = int(xstep / 5)
            for x in range(xdatum + xstep,
                                xdatum + self.chrtWid + 1 - xstep, xstep):
                canvas.create_line(x, ys, x, ye, fill = self.canvFg,
                                                            tag = 'graticule')
        else:
            # border the scale labels
            y = ydatum + self.chrtHt
            canvas.create_line(xdatum, ydatum, xdatum, y,
                                        fill = self.canvFg, tag = 'graticule')

            canvas.create_line(xdatum, y, xdatum + self.chrtWid, y,
                                        fill = self.canvFg, tag = 'graticule')
        canvas.update_idletasks()
        return

    def reflect_state(self):
        if (self._imm_startfreq == self.fconv(self.fstart.get()) and
                        self._imm_stopfreq == self.fconv(self.fstop.get()) and
                        self._imm_stepfreq == self.fconv(self.fstep.get()) and
                                    self._imm_gain == self.gain.get() and
                                    (self._imm_ipchan == self.ipchan.get() or
                            self._imm_ipchan != 2 and self.ipchan.get() != 2)):
            self.sweep_start_reqd = False
            #if len(self.line_buffer):
            if len(self.trace_list):
                self.reflect_save_state(True)
        else:
            self.reflect_save_state(False)
            self.sweep_start_reqd = True
        return

    def set_subDivs(self):
        """
        # points per division
        subDivs = chrtHt / yDivs;
        while subDivs % 2 == 0 and subDivs > 6:
            subDivs = subDivs / 2
        subDivs = (chrtHt / yDivs) / subDivs

        Rewrite to calculate from
        self.chrtHt
        self.yDivs
        and the range covered by one division
        """
        if self.ipchan.get() == 2:
            self.subDivs = 5
        else:
            self.subDivs = 4

    def ipchan_update(self):
        """ input channel change, effect and adjust y-scale labels """
        ipchan = self.ipchan.get()
        self.adc.set_ipchan(ipchan)
        if ipchan == 2:
            self.chrtHt = self.chrtHt2
            self.yDivs = self.yDivs2
        else:
            self.chrtHt = self.chrtHt1
            self.yDivs = self.yDivs1
        self.set_subDivs()
        self.label_xscale()
        self.label_yscale()
        self.graticule_update()
        self.reflect_state()
        return

    def gain_update(self):
        """ gain change, effect and adjust y-scale labels """
        gain = self.gain.get()
        self.adc.set_gain(gain)
        self.label_yscale()
        self.reflect_state()
        return

    def bitres_update(self):
        """ bit resolution change, effect """
        bitres = self.bitres.get()
        self.adc.set_bitres(bitres)
        return

    def colour_update(self):
        """ colour\cycling change, synchronise colour cycling """
        self.colour_sync()
        return

    def record_update(self):
        """ record sweep state change, placeholder """
        pass

    def trace_erase(self):
        for key, colour in self._colour_option.items():
            tag_colour = 'p_' + colour
            canvas.delete(tag_colour)
            # delete any trace marker's
            tag_colour = 'm_' + colour
            canvas.delete(tag_colour)
        # delete any 'out-of-range' too
        canvas.delete('p_white')
        canvas.delete('m_white')
        return

    def memstore_update(self):
        """ memory store state change """
        if not self.memstore.get():
            self.memstore_reset()
            self.trace_erase()
        return

    def autostep_update(self):
        """ enable\disable automatic frequency step update, placeholder """
        pass

    def desc_update(self, event = None):
        """ Update the canvas\trace file header description fields """
        canvas.delete('desc')
        xpos = self.mrgnLeft + (self.chrtWid / 2)
        ypos = self.mrgnTop / 2
        canvas.create_text(xpos, ypos, fill = self.canvFg, anchor = CENTER,
                                        text = self.desc.get(), tag = 'desc')
        # update the description in the trace header to
        # allow defining\changing it *after* sweep recording
        self.trace_state.update({'Desc' : self.desc.get()})
        return

    def freq_update(self, event):
        """ Update Start\Stop\Step parameters on Start\Stop frequency change """
        stop = self.fconv(self.fstop.get())
        # maximum permissible frequency is 'crystal clock / 2'
        if stop > self.dds.maxfreq():
            stop = self.dds.maxfreq()
            self.fstop.set(stop)
        if self.autostep.get():
            # fill step field with suitable value
            start = self.fconv(self.fstart.get())
            span = stop - start
            # one pixel per step
            step = int(span / self.chrtWid)
            # update the GUI, informing User
            self.e_stepf.delete(0, END)
            self.e_stepf.insert(0, step)
        self.label_xscale()
        self.reflect_state()
        return

    def step_update(self, event):
        self.reflect_state()
        return

    def undo_trace(self, tag = ""):
        """ Remove the current trace, restoring canvas previous sweep state """
        # delete the 'current' trace from the canvas
        for key, lineID in self.line_buffer.items():
            canvas.delete(lineID)
        self.line_buffer.clear()

        # FIXME: 'line_buffer' is a duplicate of the last entry in 'line_list',
        # the wobbulator program could be rewritten to avoid duplication.
        if len(self.line_list):
            # remove the 'current' trace from the list
            self.line_list.pop()
            # copy any previous trace from the list making it 'current'
            if len(self.line_list):
                self.line_buffer = deepcopy(self.line_list[len(self.line_list)-1])
        else:
            # program error, should always be at least one
            assert False

        # FIXME: by also 'undo'ing immutable state changes the following
        # 1 & 2 FIXME's will automagically work and be FIXED!

        if self._imm_record:
            # FIXME: 1) fataly assumes record state never changed.
            # FIXME: should remove any markers on this trace
            # remove the 'was current' trace from the record list
            if len(self.trace_list):
                del self.trace_list[len(self.trace_list)-1]

        self.reflect_save_state(len(self.trace_list))

        # FIXME: 2) will only work for the first 'undo' occurrence
        if self.colcyc.get():
            while self._colour_cycle != self._imm_colour:
                self.colour_next()
        return

    def reflect_save_state(self, state):
        if state:
            self.m_file.entryconfig(1, state = NORMAL)
            self.m_file.entryconfig(2, state = NORMAL)
            self.b_save.config(state = NORMAL)
        else:
            # nothing to be saved
            self.m_file.entryconfig(1, state = DISABLED)
            self.m_file.entryconfig(2, state = DISABLED)
            self.b_save.config(state = DISABLED)

    def undo(self):
        if len(self.undo_list):
            fn_arg = self.undo_list.pop()
            if not len(self.undo_list):
                self.b_undo.config(state = DISABLED)
            (fn_arg[0])(fn_arg[1])
            # fn_arg[0] is responsible for unallocating fn_arg[1]
            del fn_arg[0]
        return

    def fconv(self, f):
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

    def convf(self, f):
        if not f % 1000:
            if not f % 1000000:
                return '{} MHz'.format(int(f / 1000000))
            return '{} kHz'.format(int(f / 1000))
        else:    
            return '{} Hz'.format(f)

    # FIXME: do this the python way & ditch this 'C' function
    # Close but not quite, sometimes strips off one too many zero's
    def lblfmt(self, val):
        lbl = str('{0:02.4f}'.format(val)).rstrip('0')
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
        return

    def label_yscale(self):
        """ reclaim and display y-axis labels """
        gain = self.gain.get()
        ipchan = self.ipchan.get()
        if ipchan == 2:
            # Input Channel 2 (dBm)
            scale_start = self.dBm_start
            scale_range = self.dBm_range
            vDesc = 'dBm'
        else:
            # Assume linear scale
            scale_start = float(0)
            scale_range = 2.0
            vDesc = 'Volts'

        canvas.delete('vlabel')

        scale_scope = scale_range / gain
        scale_step = scale_scope / self.yDivs
        xpos = self.mrgnLeft - 25
        ypos = self.mrgnTop
        vN = scale_start + scale_scope
        while vN > scale_start:
            stry = self.lblfmt(vN)
            canvas.create_text( xpos, ypos, fill = self.canvFg,
                                                text = stry, tag = 'vlabel')
            vN = vN - scale_step
            ypos = ypos + (self.chrtHt / self.yDivs)
        stry = self.lblfmt(scale_start)
        canvas.create_text(xpos, ypos, fill = self.canvFg,
                                                text = stry, tag = 'vlabel')
        # write the vertical label
        xpos = self.mrgnLeft - 48
        ypos = int((self.chrtHt - len(vDesc)) / 2) + self.mrgnTop
        canvas.create_text(xpos, ypos, fill = self.canvFg,
                                    text = "\n".join(vDesc), tag = 'vlabel')
        canvas.update_idletasks()
        return

    def simplify_x(self):
        """ simplify x-coordinate calulation  """
        # x = int((chrtWid * ((frequency - startfreq) / span)) + mrgnLeft)
        # re-express
        # x = int((chrtWid * ((frequency / span) - (startfreq/ span))) + mrgnLeft)
        # re-express
        # x = int(((chrtWid * (frequency / span))
        #                           - (chrtWid * (startfreq / span))) + mrgnLeft)
        # re-express
        # x = int((chrtWid * (frequency / span))
        #                           - ((chrtWid * (startfreq / span)) - mrgnLeft))
        # re-express
        # x2 = ((chrtWid * (startfreq / span)) - mrgnLeft)
        # x = int((chrtWid * (frequency / span)) - x2)
        # re-express
        # x = int(((chrtWid / span) * frequency) - x2)
        # x1 = (chrtWid / span)
        # simplified equivalence
        # x = int((x1 * frequency) - x2)
        self.x2 = ((self.chrtWid * (self._imm_startfreq / self._imm_spanfreq))
                                                            - self.mrgnLeft)
        self.x1 = (self.chrtWid / self._imm_spanfreq)
        return

    def simplify_y(self):
        """ simplify y-coordinate calulation """
        # y = int(self.chrtHt + self.mrgnTop
        #             - ((reading - plotbias) * self.chrtHt/plotscale))
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
        self.y2 = (self.chrtHt / self.plotscale)
        self.y1 = (self.chrtHt + self.mrgnTop + (self.plotbias * self.y2))
        return

    def save_adapt(self, reading):
        """
        Convert reading for saving\exporting

        The voltage reading value is converted into it's
        'real' value for storage and export.
        Keep synchronised with partner function 'load_adapt'.
        """
        if self._imm_ipchan != 2:
            return (reading / self._imm_gain)
        else:
            # Input Channel 2 (dBm)
            return self.volts_dBm(reading)

    def load_adapt(self, reading):
        """
        Convert reading for plotting

        The voltage reading value is converted into it's
        'internal' representation for trace plotting.
        Keep synchronised with partner function 'save_adapt'.
        """
        if self._imm_ipchan != 2:
            return (reading * self._imm_gain)
        else:
            # Input channel two (dBm)
            return self.dBm_volts(reading)

    def trace_state_save(self):
        """ Construct trace sweep save header """
        # Need to handle the case of multiple traces
        self.trace_state.update({'fstart' : self._imm_startfreq})
        self.trace_state.update({'fstop' : self._imm_stopfreq})
        self.trace_state.update({'fstep' : self._imm_stepfreq})
        self.trace_state.update({'Input' : self._imm_ipchan})
        self.trace_state.update({'Gain' : self._imm_gain})
        self.trace_state.update({'bias' : self.plotbias})
        self.trace_state.update({'scale' : self.plotscale})
        self.trace_state.update({'colour' : self._imm_colour})
        self.trace_state.update({'BitRes' : self._imm_bitres})

        self.trace_state.update({'Desc' : self.desc.get()})
        return

    def compensate(self):
        # compensate for errors in first readings related to a
        # significant change in frequency and\or low bit resolution
        v = 0.0
        #print("compensate:")
        for n in range(1, 5):
            v += self.adc.read()
            #print(" {}".format(v / n), end = '')
        v = v / n
        #print("Compensate:{0:2.6}".format(v))
        return v

    def trace_init(self, trace_state, trace_list, marker_list):
        """ perform trace sweep from memory """

        # cannot process here, store for use on completion
        self.marker_redraw_list = marker_list

        self.b_reset['command'] = self.reset_trace
        self.b_reset.config(state = NORMAL)

        self.b_action.config(state = DISABLED)
        self.b_sweep.config(state = DISABLED)
        self.b_undo.config(state = DISABLED)
        self.reflect_save_state(False)

        # synchronise wobbulator state to trace header
        try:
            self._imm_startfreq = trace_state['fstart']
            self._imm_stopfreq = trace_state['fstop']
            self._imm_stepfreq = trace_state['fstep']
            self._imm_ipchan = trace_state['Input']
            self._imm_gain = trace_state['Gain']
            self._imm_bitres = trace_state['BitRes']
            colour = trace_state['colour']
            description = trace_state['Desc']
            self.plotbias = trace_state['bias']
            self.plotscale = trace_state['scale']
        except KeyError:
            self.reset_trace()
            messagebox.showerror('Load Error', 'Corrupted Wobbulator Trace File')
            return

        self._imm_spanfreq = (self._imm_stopfreq - self._imm_startfreq)

        self._imm_record = self.record.get()

        self.fstart.set(self._imm_startfreq)
        self.fstop.set(self._imm_stopfreq)
        self.fstep.set(self._imm_stepfreq)
        self.ipchan.set(self._imm_ipchan)
        # FIXME: unsatisfactory duplication here
        if self.ipchan.get() == 2:
            self.chrtHt = self.chrtHt2
            self.yDivs = self.yDivs2
        else:
            self.chrtHt = self.chrtHt1
            self.yDivs = self.yDivs1
        self.set_subDivs()
        self.gain.set(self._imm_gain)
        self.bitres.set(self._imm_bitres)

        self.colour.set(colour)
        self.colour_sync()
        self._imm_colour = self._colour_cycle

        self.desc.set(description)
        self.desc_update()

        self.fresh_canvas()

        if self._imm_record:
            self.trace_state_save()

        self.simplify_x()
        self.simplify_y()

        self.sweep_start_reqd = False

        self._list_iterator = self.buf_iterate(trace_list)
        self.sweep_start_func = self.trace_next
        self.sweep_stop_func = self.trace_stop
        self.trace_next()
        return

    def trace_next(self):
        """ Start trace from list """
        # if this gets set, we come straight back here
        if self.sweep_start_reqd:
            # and bomb out
            self.reset_trace()
            return
        try:
            trace = next(self._list_iterator)
            # FIXME: rather than run into the StopIteration exception,
            # on the last trace iterator set the 'oneflag'.
        except StopIteration:
            self.sweep_stop_func()
            return
        else:
            # Initialise the frequency\reading generator
            self._sweep_iterator = self.trace_iterate(trace)
            # take the first reading
            startfreq = next(self._sweep_iterator)
            # for y-coordinate start point
            self.ystart = self.y1 - (self.reading * self.y2)
            # graticule offset for x-coordinate start point
            self.xstart = self.mrgnLeft

            if self._imm_record:
                self.trace_set.update({startfreq : self.save_adapt(self.reading)})
                #self.trace_set.update({startfreq : self.reading})

            self.trace_set.clear()
            self._imm_colour = self._colour_cycle
            self.oneflag = False
            if self.cls.get():
                self.fresh_canvas()
            self.sweep_continue()
        return

    def sweep_start(self):
        """ perform frequency sweep """
        # start\stop\stepfreq could be made 'enter key' bind dependant all
        # setting 'sweep_start_reqd' when changed, simplifying code here.
        # Do we wish to force 'Enter'ing on the User ?
        startfreq = self.fconv(self.fstart.get())
        stopfreq = self.fconv(self.fstop.get())
        stepfreq = self.fconv(self.fstep.get())

        ipchan = self.ipchan.get()
        gain = self.gain.get()
        bitres = self.bitres.get()

        self._imm_colour = self._colour_cycle

        # scale and bias are dependant on input channel
        if ipchan == 2:
            # FIXME: fix input gain at 1 ???
            # set wave to 0 Hz
            self.dds.set_wave(0)
            # calculate bias compensating for errors in first readings
            # from input with no wave on output.
            bias = self.compensate()
            if bias > 2.0:
                self.invalid_sweep('The input voltage\gain is out of range')
                return
            self.plotbias = self.VdBm_bias * gain
            self.plotscale = self.dBm_scale
        else:
            self.plotbias = 0
            self.plotscale = 2

        self.trace_set.clear()

        #  If a sweep dependant value has changed
        if (self.sweep_start_reqd or (self._imm_startfreq != startfreq) or
                                        (self._imm_stopfreq != stopfreq) or
                                            (self._imm_stepfreq != stepfreq)):
            if (startfreq > stopfreq) or (stepfreq < 1) or (stopfreq > self.dds.maxfreq()):
                self.invalid_sweep('The frequency selection settings are invalid')
                return
            # immutable variables, may not change during a sweep
            self._imm_spanfreq = (stopfreq-startfreq)
            self._imm_startfreq = startfreq
            self._imm_stopfreq = stopfreq
            self._imm_stepfreq = stepfreq
            self._imm_ipchan = ipchan
            self._imm_gain = gain
            self._imm_bitres = bitres
            self._imm_record = self.record.get()
            self.fresh_canvas()
            self.sweep_start_reqd = False
            if self._imm_record:
                self.trace_state_save()
        elif self.cls.get():
            self.fresh_canvas()

        self.simplify_x()
        self.simplify_y()

        # graticule offset for x-coordinate start point
        self.xstart = self.mrgnLeft

        # program the DDS to output the required frequency
        self.dds.set_wave(startfreq)
        # take voltage reading
        # compensate for errors in first readings
        self.reading = self.compensate()

        # for y-coordinate start point
        self.ystart = self.y1 - (self.reading * self.y2)

        # Initialise the frequency generator
        # If stepfreq is not a divisor of span then stopfreq
        # will be exceeded by some proportion of stepfreq.
        # Handle any overstep in the frequency generator
        self._sweep_iterator = self.sweep_iterate(startfreq + stepfreq,
                                            stopfreq + stepfreq, stepfreq)
        if self._imm_record:
            self.trace_set.update({startfreq : self.save_adapt(self.reading)})
        self.sweep_start_func = self.sweep_start
        self.sweep_stop_func = self.single_stop
        self.sweep_continue()
        return

    def sweep_continue(self):
        """
        time-share with GUI by returning after a number of plots

        The number of plots is inversely proportional to the bit resolution
        as the higher the bit resolution the longer it takes to sample.
        """
        _magic = abs(self._imm_bitres - 17) ** 2
        _do_over = 1
        while _do_over:
            if self.sweep_start_reqd:
                # GUI changes flagged a sweep_start is required
                self._callback_id = root.after(1, self.sweep_start_func)
                return

            try:
                frequency = next(self._sweep_iterator)
            except StopIteration:
                # should never happen, prove it
                assert False
                self.sweep_end()
            else:
                if not self.memstore.get():
                    # memory store disabled
                    if frequency in self.line_buffer:
                        # FIXME: this may leave a 'marker' with no trace
                        # erase the part trace
                        try:
                            lineID = self.line_buffer[frequency]
                            canvas.delete(lineID)
                        except:
                            raise ProgramError('Program error')

                # optionally record trace sweep data for later saving to file
                if self._imm_record:
                    self.trace_set.update({frequency : self.save_adapt(self.reading)})

                # calculate x co-ordinate from the reading
                xend = int((self.x1 * frequency) - self.x2)
                # calculate y co-ordinate from the reading
                yend = int(self.y1 - (self.reading * self.y2))

                """
                if (self.ystart > yend):
                    # plotting up the canvas
                    self._imm_colour = 'green'
                elif (yend > self.ystart):
                    # plotting down the canvas
                    self._imm_colour = 'red'
                else:
                    # plotting across the canvas
                    self._imm_colour = 'blue'

                # restrict plotting range to within graticule display area, any
                # out-of-bounds plotting would also show up on any saved images
                if ((self.ystart > self.mrgnTop) and
                                (self.ystart < (self.canvHt - self.mrgnTop))):
                    # start is on canvas
                    if (yend < self.mrgnTop):
                        yend = self.mrgnTop
                    elif (yend > (self.canvHt - self.mrgnTop)):
                        yend = self.canvHt - self.mrgnTop
                    doplot = True
                elif ((yend > self.mrgnTop) and
                                        (yend < (self.canvHt - self.mrgnTop))):
                    # end is on canvas
                    if (self.ystart < self.mrgnTop):
                        self.ystart = self.mrgnTop
                    elif (self.ystart > (self.canvHt - self.mrgnTop)):
                        self.ystart = self.canvHt - self.mrgnTop
                    doplot = True
                else:
                    doplot = False
                """

                colour = self._imm_colour
                if (yend < self.mrgnTop):
                    yend = self.mrgnTop - 3
                    colour = 'white'
                elif (yend > (self.canvHt - self.mrgnTop)):
                    yend = (self.canvHt - self.mrgnTop) + 1
                    colour = 'white'

                if (self.ystart < self.mrgnTop):
                    self.ystart = self.mrgnTop - 3
                    colour = 'white'
                elif (self.ystart > (self.canvHt - self.mrgnTop)):
                    self.ystart = (self.canvHt - self.mrgnTop) + 1
                    colour = 'white'

                tag_colour = 'p_' + colour
                lineID = canvas.create_line(self.xstart, self.ystart,
                    xend, yend, fill = colour, tag = tag_colour)

                # record the trace handle for later individual removal
                self.line_buffer.update({frequency : lineID})

                canvas.update_idletasks()

                self.xstart = xend
                self.ystart = yend

            if frequency >= self._imm_stopfreq:
                self.sweep_end()
                return

            _do_over = (_do_over + 1) % _magic
        # momentarily relinquish to GUI
        self._callback_id = root.after(1, self.sweep_continue)
        return

    def sweep_end(self):
        # completed a full sweep

        if self.colcyc.get():
            # cycle to next colour
            self.colour_next()

        if self._imm_record:
            # Save as a list of 'trace plot sets'
            self.trace_list.append(deepcopy(self.trace_set))

        self.undo_list.append([self.undo_trace, ''])
        self.line_list.append(deepcopy(self.line_buffer))

        self.b_undo.config(state = NORMAL)

        if self.oneflag:
            # single sweep completed
            self.sweep_stop_func()
        else:
            # schedule a fresh sweep
            self._callback_id = root.after(1, self.sweep_start_func)
        return

    def buf_iterate(self, trace_list):
        for trace in trace_list:
            yield trace

    def trace_iterate(self, trace):
        for freq in sorted(trace):
            self.reading = self.load_adapt(trace[freq])
            yield freq

    def sweep_iterate(self, start, finish, step):
        for freq in range(start, finish, step):
            # correct any overstep
            if freq > self._imm_stopfreq:
                freq = self._imm_stopfreq
            # program the DDS to output the required frequency
            self.dds.set_wave(freq)
            # take a reading at the required frequency
            self.reading = self.adc.read()
            yield freq

    def trace_stop(self):
        """ stop trace sweep """
        self.marker_list_redraw()
        if _has_wobbulator:
            self.b_action.config(state = NORMAL)
            self.b_sweep.config(state = NORMAL)
        self.b_reset.config(state = NORMAL)
        self.b_undo.config(state = NORMAL)
        self.reflect_save_state(True)
        return

    def single_stop(self):
        """ stop single sweep """
        self.dds.reset()
        self.b_sweep['text'] = 'Sweep'
        self.b_sweep['command'] = self.single_sweep
        self.b_action.config(state = NORMAL)
        self.reflect_save_state(True)
        #tstop = time.time()
        #print(str(int(tstop) - int(tstart)))
        return

    def cycle_stop(self):
        """ stop cyclic sweeps """
        self.b_action['text'] = 'Cycle'
        self.b_action['command'] = self.cycle_sweep
        self.b_sweep.config(state = NORMAL)
        # change cycle sweep to single sweep
        # to allow current sweep to complete
        self.oneflag = True
        self.b_sweep['text'] = 'Abort'
        self.b_sweep['command'] = self.abort_sweep
        self.b_action.config(state = DISABLED)
        return

    def single_sweep(self):
        """ start single sweep """
        #tstart = time.time()
        self.oneflag = True
        self.b_sweep['text'] = 'Abort'
        self.b_sweep['command'] = self.abort_sweep
        self.b_action.config(state = DISABLED)
        self.b_undo.config(state = DISABLED)
        self.reflect_save_state(False)
        self.b_reset['command'] = self.reset_sweep
        self.b_reset.config(state = NORMAL)
        self.sweep_start()
        return

    def cycle_sweep(self):
        """ start cyclic sweeps """
        self.oneflag = False
        self.b_action['text'] = 'Stop'
        self.b_action['command'] = self.cycle_stop
        self.b_sweep.config(state = DISABLED)
        self.b_undo.config(state = DISABLED)
        self.reflect_save_state(False)
        self.b_reset['command'] = self.reset_sweep
        self.b_reset.config(state = NORMAL)
        self.sweep_start()
        return

    def abort_sweep(self):
        """ abort during physical sweep """
        root.after_cancel(self._callback_id)
        self.dds.reset()

        for key, lineID in self.line_buffer.items():
            canvas.delete(lineID)
        self.line_buffer.clear()

        self.b_action['text'] = 'Cycle'
        self.b_action['command'] = self.cycle_sweep
        self.b_sweep.config(state = NORMAL)
        self.b_sweep['text'] = 'Sweep'
        self.b_sweep['command'] = self.single_sweep
        self.b_action.config(state = NORMAL)
        return

    def reset_common(self):
        root.after_cancel(self._callback_id)
        self.sweep_start_reqd = True
        self.fresh_canvas()
        self.memstore_reset()
        self.reflect_save_state(False)

    def reset_sweep(self):
        """ reset during physical sweep """
        self.reset_common()
        self.dds.reset()
        self.b_action['text'] = 'Cycle'
        self.b_action['command'] = self.cycle_sweep
        self.b_sweep.config(state = NORMAL)
        self.b_sweep['text'] = 'Sweep'
        self.b_sweep['command'] = self.single_sweep
        self.b_action.config(state = NORMAL)
        return

    def reset_trace(self):
        """ reset during trace load """
        self.reset_common()
        if _has_wobbulator:
            self.b_sweep.config(state = NORMAL)
            self.b_action.config(state = NORMAL)
        return

    def history_invalidated(self):
        pass

    def invalid_sweep(self, msg):
        """ stop and reset the runtime variables """
        root.after_cancel(self._callback_id)
        self.dds.reset()
        self.b_action['text'] = 'Cycle'
        self.b_action['command'] = self.cycle_sweep
        self.b_sweep.config(state = NORMAL)
        self.b_sweep['text'] = 'Sweep'
        self.b_sweep['command'] = self.single_sweep
        self.b_action.config(state = NORMAL)
        if msg:
            messagebox.showerror('Invalid Settings', msg)
        else:
            messagebox.showerror('Invalid Settings',
                                        'The chosen parameters are invalid')
        return

    def undo_marker(self, markerIDs):
        while len(markerIDs):
            marker = markerIDs.pop()
            canvas.delete(marker)
        return

    def undo_marker_list(self, markerIDs):
        self.undo_marker(markerIDs)
        self.marker_list.pop()
        return

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
        """ Synchronise the colour cycle to the User selected colour. """
        while self._colour_cycle != self.colour.get():
            self.colour_cycle()
        return

    def colour_next(self):
        """ Set the active colour to the next colour in the cycle. """
        key = self.colour_cycle()
        # Be careful, select() not invoke()
        self._colour_button[key].select()
        return

    def memstore_reset(self):
        """
        Wipe the memory store and flag as invalid.

        Any references to previous trace sweep data is erased.
        NOTE: the trace plot is not removed from the canvas.
        """
        self.line_buffer.clear()
        return

    def trace_list_reset(self):
        """
        Initialise\Wipe the trace buffer store
        """
        self.trace_state.clear()
        self.trace_set.clear()
        self.trace_list[:] = []
        self.reflect_save_state(False)
        return

    def marker_list_reset(self):
        """
        Initialise\Wipe the marker list
        """
        self.marker_list[:] = []
        return

    def line_list_reset(self):
        """
        Initialise\Wipe the line list
        """
        self.line_list[:] = []
        return

    def undo_list_reset(self):
        """
        Initialise\Wipe the undo list
        """
        self.undo_list[:] = []
        self.b_undo.config(state = DISABLED)
        return

    # FIXME: not enough try's
    def save_canvas(self):
        self.b_action.config(state = DISABLED)
        self.b_sweep.config(state = DISABLED)
        self.b_reset.config(state = DISABLED)
        self.b_undo.config(state = DISABLED)
        self.reflect_save_state(False)
        ttl = 'Save Canvas Image'
        ft = (("portable document format", "*.pdf"),
                                        ("Portable Document Format", "*.PDF"),
                                                        ("postscript", "*.ps"),
                                                        ("PostScript", "*.PS"),
                                                        ("All files", "*.*"))
        filename = filedialog.asksaveasfilename(title=ttl, filetypes=ft)
        if filename:
            fname, fext = os.path.splitext(filename)
            if fext.upper() == '.PDF':
                ftemp = tempfile.NamedTemporaryFile()
                canvas.postscript(file = ftemp.name, colormode = 'color')
                ftemp.seek(0)
                if self.reformat_ps(ftemp.name):
                    ftemp.seek(0)
                    try:
                        process = subprocess.Popen(['ps2pdf',
                                                        ftemp.name, filename])
                    except OSError:
                        messagebox.showerror('Conversion Error',
                                        'please check "ps2pdf" is installed')
                    else:
                        process.wait()
                    finally:
                        ftemp.close()
                else:
                    ftemp.close()
            elif fext.upper() == '.PS':
                canvas.postscript(file = filename, colormode = 'color')
                self.reformat_ps(filename)
            else:
                messagebox.showerror('Bad file extension',
                                            'Please specify ".ps" or ".pdf"')

        if _has_wobbulator:
            self.b_action.config(state = NORMAL)
            self.b_sweep.config(state = NORMAL)
        self.b_reset.config(state = NORMAL)
        self.b_undo.config(state = NORMAL)
        self.reflect_save_state(True)
        return

    def reformat_ps(self, fn_ps):
        """
        enlargen the postscript pixelsize

        The canvas.postscript documentation related to the definition
        of fonts is vague at best. Until fonts can be controlled by
        the correct method, live with whatever font type ghostscript
        chooses to use, but change the font size to make it readable.
        """
        pixelsize = self.text_font[1]
        args = [ 'sed', '-i']
        args.extend([ '-e', 's/findfont ' + pixelsize + '/findfont 12/g'])
        args.extend([fn_ps])
        try:
            process = subprocess.Popen(args)
        except OSError:
            messagebox.showerror('Re-formatting Error',
                                        'please check "sed" is installed')
            return False
        else:
            process.wait()
        if process.returncode < 0:
            return False
        return True

# Check for presence of RPi Wobbulator ADC on i2c bus
_has_wobbulator = False
try:
    i2c_op = str(subprocess.check_output(('i2cdetect', '-y', '1')))
except FileNotFoundError:
    print("i2cdetect not found (assuming RPi Wobbulator not present)")
except:
    pass
else:
    if i2c_op.find('68') != -1:
        _has_wobbulator = True

if not _has_wobbulator:
    print("RPi Wobbulator not detected")

# Assign TK to root
root = Tk()
# Set main window title and menubar
root.wm_title('RPi Wobbulator ' + version)
# Create instance of class WobbyPi
# this instantiates the DDS and ADC modules which
# from this point will require cleaning up on exit
app = WobbyPi(root, params)
try:
    app.makemenu(root)
    app.initialise()
    # Start main loop and wait for input from GUI
    root.mainloop()
finally:
    if _has_wobbulator:
        # tell the library modules to clean up
        app.dds.exit()
        app.adc.exit()
