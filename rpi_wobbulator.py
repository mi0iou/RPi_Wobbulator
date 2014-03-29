# RPi Wobbulator v2.6.6

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

# import GUI module
from tkinter import *

# ---- get user preferences or set defaults ----
# for param file persistence, import faster cPickle if available
try:
    import cPickle as pickle
except:
    import pickle
    
params = {}
try:
    # user parameters
    paramFN = 'wobParam.pkl'
    paramFile = open(paramFN,"rb")
    params = pickle.load(paramFile)
    #print (params)
    paramFile.close()
except IOError:
    # default parameters
    params['chrtHt'] = 500
    params['chrtWid'] = 500
    params['xDivs'] = 10
    params['yDivs'] = 10
    params['canvFg'] = 'black'
    params['canvBg'] = 'cyan'
    params['fBegin'] = 14000000
    params['fEnd'] = 14200000
    params['fIntvl'] = 10000
    params['vgain'] = 132
    params['vchan'] = 0
    params['colour'] = 'blue'
    params['bias'] = 0
    params['fast'] = 0
    params['cls'] = 0
    params['grid'] = 1
    params['dB'] = 0
# ---- end of user param support ----

# ---- for app menus and associated displays ----
from tkinter import messagebox
from tkinter import colorchooser

def notDone():
    messagebox.showerror('Not implemented', 'Not yet available')

def getForegroundColor():
    fgColor = colorchooser.askcolor(params['canvFg'], title='Foreground Color')
    if fgColor[1] != 'None':
        params['canvFg'] = fgColor[1]
        app.canvFg = fgColor[1]
    #print (params['canvFg'])   

def getBackgroundColor():
    bgColor = colorchooser.askcolor(params['canvBg'], title='Background Color')
    if bgColor[1] != 'None':
        params['canvBg'] = bgColor[1]
        app.canvBg = bgColor[1]
    #print (params['canvBg'])

def getChartWidth():
    chrtWid = simpledialog.askinteger('Chart Width', '300 to 1000',initialvalue=params['chrtWid'],minvalue=300,maxvalue=1000)
    if chrtWid != 'None':
        params['chrtWid'] = chrtWid
        app.chrtWid = chrtWid
    #print (chrtWid)

def getChartHeight():
    chrtHt = simpledialog.askinteger('Chart Height', '300 to 1000',initialvalue=params['chrtHt'],minvalue=300,maxvalue=1000)
    if chrtHt != 'None':
        params['chrtHt'] = chrtHt
        app.chrtHt = chrtHt
    #print (chrtHt)

def getXdivisions():
    xDivs = simpledialog.askinteger('X-divisions', '10-50',initialvalue=params['xDivs'],minvalue=10,maxvalue=50)
    if xDivs != 'None':
        params['xDivs'] = xDivs
        app.xDivs = xDivs
    #print (xDivs)
def getYdivisions():
    yDivs = simpledialog.askinteger('Y-divisions', '10-50',initialvalue=params['yDivs'],minvalue=10,maxvalue=50)
    if yDivs != 'None':
        params['yDivs'] = yDivs
        app.yDivs = yDivs
    #print (yDivs)
    
def makemenu(win):
    top = Menu(win)
    win.config(menu=top)    # set its menu option

    file = Menu(top, tearoff=0)
    top.add_cascade(label='File', menu=file, underline=0)
    file.add_command(label='Exit', command=root.destroy, underline=1, accelerator='Ctrl+Q')

    opt = Menu(top, tearoff=0)
    top.add_cascade(label='Options', menu=opt, underline=0)
    opt.add_command(label='Background', command=getBackgroundColor, underline=0)
    opt.add_command(label='Foreground', command=getForegroundColor, underline=0)
    opt.add_separator()
    opt.add_command(label='Chart Width', command=getChartWidth, underline=6)
    opt.add_command(label='Chart Height', command=getChartHeight, underline=6)
    opt.add_separator()
    opt.add_command(label='X-divisions', command=getXdivisions, underline=0)
    opt.add_command(label='Y-divisions', command=getYdivisions, underline=0)

    help = Menu(top, tearoff=0)
    top.add_cascade(label='Help', menu=help, underline=0)
    help.add_command(label='About Wobbulator', command=notDone, underline=1)
# ---- end of menu support ----

# ---- RaspBerry Pi IO support ----
#import quick2wire i2c module
import quick2wire.i2c as i2c

# import GPIO module
import RPi.GPIO as GPIO

# setup GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

# Define GPIO pins
W_CLK = 15
FQ_UD = 16
DATA = 18
RESET = 22

# setup IO bits
GPIO.setup(W_CLK, GPIO.OUT)
GPIO.setup(FQ_UD, GPIO.OUT)
GPIO.setup(DATA, GPIO.OUT)
GPIO.setup(RESET, GPIO.OUT)

# initialize everything to zero
GPIO.output(W_CLK, False)
GPIO.output(FQ_UD, False)
GPIO.output(DATA, False)
GPIO.output(RESET, False)

#define address for ADC chip
adc_address = 0x68

# setup i2c bus
bus = i2c.I2CMaster()

# Function to send a pulse to GPIO pin
def pulseHigh(pin):
    GPIO.output(pin, True)
    GPIO.output(pin, False)
    return
# ---- end of RaspBerry Pi IO support ----

# ---- application specific stuff starts here ----
# Function to send a byte to AD9850 module
def tfr_byte(data):
    for i in range (0,8):
        GPIO.output(DATA, data & 0x01)
        pulseHigh(W_CLK)
        data=data>>1
    return

# Function to send frequency (assumes 125MHz xtal) to AD9850 module
def sendFrequency(frequency):
    freq=int(frequency*4294967296/125000000)
    for b in range (0,4):
        tfr_byte(freq & 0xFF)
        freq=freq>>8
    tfr_byte(0x00)
    pulseHigh(FQ_UD)
    return

# Function to set address for ADC
def changechannel(address, adcConfig):
    bus.transaction(i2c.writing_bytes(address, adcConfig))
    return

# Function to get reading from ADC (12 bit mode)
def getadcreading(address, adcConfig): # << changed afa
    bus.transaction(i2c.writing_bytes(address, adcConfig)) # << added afa 
    m, l ,s = bus.transaction(i2c.reading(address,3))[0]
    while (s & 128):
        m, l, s  = bus.transaction(i2c.reading(address,3))[0]
    # shift bits to product result
    t = (m << 8) | l
    # check if positive or negative number and invert if needed
    if (m > 128):
        t = ~(0x02000 - t)
    if root.fast:
        return (t * 0.001) # 1mV per DN in 12 bit mode
    else:
        return (t * 0.00025) # 0.25mV per DN in 14 bit mode

# Function to convert frequency f to Hz and return as int value
#          e.g.: 10 MHz, 14.1m, 1k, 3.67 Mhz, 1.2 khz
def fconv(f):	
	f = f.upper()	
	if f.find("K") > 0:	
  		return (int(float(f[:f.find("K")]) * 1000))	
	elif f.find("M") > 0:	
  		return (int(float(f[:f.find("M")]) * 1000000))	
	else:	
  		return (int(float(f)))	

# Class definition for WobbyPi application
class WobbyPi():

    # Build Graphical User Interface
    def __init__(self, master, params):
        frame = Frame(master, bd=10)
        frame.pack(fill=BOTH,expand=1)

        self.chrtHt = 0

        # setup working parameters
        # system values
        self.mrgnLeft = 56 #<-changed ta
        self.mrgnRight = 20 
        self.mrgnTop = 10 
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
        canvas = Canvas(frame, width=self.canvWid, height=self.canvHt, bg=self.canvBg)
        canvas.grid(row=0, column=0, columnspan=6, rowspan=10)

        # choose channel
        channelframe = LabelFrame(frame, text='Ch', labelanchor='n')
        self.channel = IntVar()
        g1 = Radiobutton(channelframe, text='1', variable=self.channel, value=0, command = self.dispScales) # << afa
        g1.grid(row=0)
        if int(params['vchan']) == 0:
            g1.select()
        g2 = Radiobutton(channelframe, text='2', variable=self.channel, value=1, command = self.dispScales) # << afa
        g2.grid(row=1)
        if int(params['vchan']) == 1:
            g2.select()
        g3 = Radiobutton(channelframe, text='3', variable=self.channel, value=2)
        g3.grid(row=2)
        if int(params['vchan']) == 2:
            g3.select()
        g4 = Radiobutton(channelframe, text='4', variable=self.channel, value=3)
        g4.grid(row=3)
        if int(params['vchan']) == 3:
            g4.select()
        channelframe.grid(row=1, column=6)

        # choose input gain - values changed from 3.75 SPS 18 bit to 60 SPS 14 bit, one shot mode
        gainframe = LabelFrame(frame, text='Gain', labelanchor='n')
        self.gainval = IntVar()
        g1 = Radiobutton(gainframe, text='1', variable=self.gainval, value=132, command = self.dispScales)
        g1.grid(row=0)
        if int(params['vgain']) == 132:
            g1.select()
        g2 = Radiobutton(gainframe, text='2', variable=self.gainval, value=133, command = self.dispScales)
        g2.grid(row=1)
        if int(params['vgain']) == 133:
            g2.select()
        g3 = Radiobutton(gainframe, text='4', variable=self.gainval, value=134, command = self.dispScales)
        g3.grid(row=2)
        if int(params['vgain']) == 134:
            g3.select()
        g4 = Radiobutton(gainframe, text='8', variable=self.gainval, value=135, command = self.dispScales)
        g4.grid(row=3)
        if int(params['vgain']) == 135:
            g4.select()
        gainframe.grid(row=2, column=6)

        # choose a colour
        colourframe = LabelFrame(frame, text='Colour', labelanchor='n')
        self.colour = StringVar()
        c1 = Radiobutton(colourframe, fg='blue', text='[B]', variable=self.colour, value='blue')
        c1.grid(row=0)
        if params['colour'] == 'blue':
            c1.select()
        c2 = Radiobutton(colourframe, fg='red', text='[R]', variable=self.colour, value='red')
        c2.grid(row=1)
        if params['colour'] == 'red':
            c2.select()
        c3 = Radiobutton(colourframe, fg='green', text='[G]', variable=self.colour, value='green')
        c3.grid(row=2)
        if params['colour'] == 'green':
            c3.select()
        c4 = Radiobutton(colourframe, fg='magenta', text='[M]', variable=self.colour, value='magenta')
        c4.grid(row=3)
        if params['colour'] == 'magenta':
            c4.select()
        c5 = Radiobutton(colourframe, fg='yellow', text='[Y]', variable=self.colour, value='yellow')
        c5.grid(row=4)
        if params['colour'] == 'yellow':
            c5.select()
        colourframe.grid(row=3, column=6)

        # remove bias
        self.bias = IntVar()
        biascheck = Checkbutton(frame, text="Bias", variable=self.bias, onvalue=1, offvalue=0)
        biascheck.grid(row=5, column=6)
        if int(params['bias']) == 1:
            biascheck.select()

        # fast flag
        self.fast = IntVar()
        fastcheck = Checkbutton(frame, text="Fast", variable=self.fast, onvalue=1, offvalue=0)
        fastcheck.grid(row=6, column=6)
        if int(params['fast']) == 1: #<< changed FL
            fastcheck.select()

        # CLS check button to clear the screen every sweep
        self.cls = IntVar()
        clearbutton = Checkbutton(frame, text='CLS', variable=self.cls, onvalue=1, offvalue=0)
        clearbutton.grid(row=7, column=6)
        if int(params['cls']) == 1: #<< changed FL
            clearbutton.select()
            
        # dBm check button to change Y scale to dB #<< New button afa
        self.dB = IntVar()
        dBbutton = Checkbutton(frame, text='dBm', variable=self.dB, onvalue=1, offvalue=0, command = self.dispScales)
        dBbutton.grid(row=8, column=6)
        if int(params['dB']) == 1: 
            dBbutton.select()

        # Button to start a single sweep        #<< New button db
        self.sweepbutton = Button(frame, text='Sweep', height = 1, width = 3, relief=RAISED, command=self.onesweep)
        self.sweepbutton.grid(row=9, column=6)

        # RUN button to start the sweep
        self.runbutton = Button(frame, text='RUN', height = 1, width = 3, relief=RAISED, command=self.loopsweep)
        self.runbutton.grid(row=10, column=6)

        # STOP button to stop continuous sweep
        self.stopbutton = Button(frame, text='STOP', height = 1, width = 3, relief=SUNKEN, command=self.stop)
        self.stopbutton.grid(row=11, column=6)

        # start frequency for sweep
        fstartlabel = Label(frame, text='Start Freq (Hz)')
        fstartlabel.grid(row=10, column=0)
        self.fstart = StringVar()
        fstartentry = Entry(frame, textvariable=self.fstart, width=10)
        fstartentry.grid(row=10, column=1)
        fstartentry.insert(0,self.fBegin)

        # stop frequency for sweep
        fstoplabel = Label(frame, text='Stop Freq (Hz)')
        fstoplabel.grid(row=10, column=2)
        self.fstop = StringVar()
        fstopentry = Entry(frame, textvariable=self.fstop, width=10)
        fstopentry.grid(row=10, column=3)
        fstopentry.insert(0,self.fEnd)

        # increment for sweep
        fsteplabel = Label(frame, text='Step (Hz)')
        fsteplabel.grid(row=10, column=4)
        self.fstep = StringVar()
        fstepentry = Entry(frame, textvariable=self.fstep, width=8)
        fstepentry.grid(row=10, column=5)
        fstepentry.insert(0,self.fIntvl)

        # user description space #<< new addition FL
        descLabel = Label(frame, text='Description')
        descLabel.grid(row=11, column=0)
        descEntry = Entry(frame, width=57)  #<< changed db
        descEntry.grid(row=11, column=1, columnspan=5)
        
        # display a grid
        self.grid = IntVar()
        gridcheck = Checkbutton(frame, text="Grid", variable=self.grid, onvalue=1, offvalue=0, command=self.checkgrid)
        gridcheck.grid(row=4, column=6)
        if int(params['grid']) == 1:
            gridcheck.select()
        self.checkgrid()
        self.dispScales()


    # clear the screen
    def clearscreen(self):
        chart = canvas.create_rectangle(self.mrgnLeft, self.mrgnTop,
                                        self.mrgnLeft+self.chrtWid, self.mrgnTop+self.chrtHt,
                                        fill=self.canvBg, outline=self.canvFg)
        self.checkgrid()

    # display grid
    def checkgrid(self):
        checked = self.grid.get()
        if checked == 1:
                colour=self.canvFg
        else:
                colour=self.canvBg
        for x in range(self.mrgnLeft, self.mrgnLeft+self.chrtWid+1, int(self.chrtWid/self.xDivs)):
                canvas.create_line(x, self.mrgnTop, x, self.mrgnTop+self.chrtHt, fill=colour)
        for y in range(self.mrgnTop, self.chrtHt+self.mrgnBotm, int(self.chrtHt/self.yDivs)):
                canvas.create_line(self.mrgnLeft, y, self.chrtWid+self.mrgnLeft, y, fill=colour)

    # display horizontal axis labels
    def dispScales(self):
        startF = float(fconv(self.fstart.get()))	
        stopF = float(fconv(self.fstop.get()))	
        if stopF > 1000000:
            f0 = round((startF/1000000.0),1)
            fN = round(stopF/1000000.0,1)
            fDesc = 'MHz'
        elif stopF > 1000:
            f0 = round(startF/1000.0,1)
            fN = round(stopF/1000.0,1)
            fDesc = 'kHz'
        else:
            f0 = round(startF/1.0,1)
            fN = round(stopF/1.0,1)
            fDesc = 'Hz'

        canvas.create_rectangle(0, self.mrgnTop+self.chrtHt+1,
                                self.canvWid+self.mrgnLeft, self.canvHt,
                                fill=self.canvBg, outline=self.canvBg) #remove old X scale

        fStep = (fN-f0)/self.xDivs
        fLbls = ''
        f = f0
        hWhere = (self.mrgnLeft/2)+18
        while f < fN:
            hLbl = canvas.create_text(hWhere,self.canvHt-20, text="{0:10.2f}".format(f))
            f = f + fStep
            hWhere = hWhere+self.chrtWid/self.xDivs
        hLbl = canvas.create_text(hWhere,self.canvHt-20, text='{0:10.2f}'.format(fN))
        hWhere = ((self.mrgnLeft+self.chrtWid+self.mrgnRight) - len(fDesc)) / 2
        hLbl = canvas.create_text(hWhere, self.canvHt-5, text=fDesc)

    # display vertical axis labels << new function
    
        canvas.create_rectangle(0, 0, self.mrgnLeft-1, self.canvHt-self.mrgnBotm,
                                fill=self.canvBg, outline=self.canvBg)
   
        gain = pow(2,(self.gainval.get()-132))
        
        if self.dB.get() == 1 and self.channel.get() == 1: # optional for channel 2 << afa
            self.bias.set(1) # << automatically select bias removal option when dBm scale is selected - tgh
            startV = float(-75)
            stopV = float(25) # scale change <<afa
            v0 = startV
            vN = startV + 100/gain # scale change <<afa
            vDesc = 'dBm'
            vStep = (vN-v0)/self.yDivs
            vLbls = ''
            v = vN
            vWhere = (self.mrgnBotm)/2 - 5
            while v > v0:
              vLbl = canvas.create_text(self.mrgnLeft-30, vWhere, text='{0:10.1f}'.format(v))
              v = v - vStep
              vWhere = vWhere+self.chrtHt/self.yDivs
            vLbl = canvas.create_text(self.mrgnLeft-30, vWhere, text='{0:10.1f}'.format(v0))

            
        if  self.channel.get() == 0 or self.dB.get() == 0: #  auto for channel 1 << afa
            self.dB.set(0) # unset dB << afa
            startV = float(0)
            stopV = float(2.0) #  scale change << afa
            v0 = startV
            vN = stopV/gain
            vDesc = 'Volts'
            vStep = (vN-v0)/self.yDivs
            vLbls = ''
            v = vN
            vWhere = (self.mrgnBotm)/2 - 5
            while v > v0:
              vLbl = canvas.create_text(self.mrgnLeft-30, vWhere, text='{0:10.3f}'.format(v))
              v = v - vStep
              vWhere = vWhere+self.chrtHt/self.yDivs
            vLbl = canvas.create_text(self.mrgnLeft-30, vWhere, text='{0:10.3f}'.format(v0))
            
        vWhere = (self.chrtHt) / 2 - 6
        vLbl = canvas.create_text(8, vWhere, text="\n".join(vDesc))
        
    # start frequency sweep
    def sweep(self):
        pulseHigh(RESET)
        root.fast = int(self.fast.get())
        address = int(self.gainval.get())-4*root.fast # change to fast value if fast flag
        channel = int(self.channel.get())
        chip = adc_address
        address = (address + (32 * channel))

        startfreq = fconv(self.fstart.get())	 
        stopfreq = fconv(self.fstop.get())	
        span = (stopfreq-startfreq)
        step = fconv(self.fstep.get())
        #  If a value has changed, only then refresh scales. This to avoid slowdown between sweeps    #<< added db
        if self.oldstartfreq != startfreq or self.oldstopfreq != stopfreq or self.oldspan != span or self.oldstep != step:
            self.dispScales()
            self.oldstartfreq = startfreq 
            self.oldstopfreq = stopfreq
            self.oldspan = span
            self.oldstep = step	
        colour = str(self.colour.get())
        removebias = self.bias.get()
        bias = (getadcreading(chip, address) + getadcreading(chip, address))/2
        if int(self.cls.get()):
           self.clearscreen()
        root.fast = int(self.fast.get())
        for frequency in range((startfreq - step), (stopfreq + step), step):
            pulseHigh(RESET)
            pulseHigh(W_CLK)
            pulseHigh(FQ_UD)
            sendFrequency(frequency)
            
            reading = getadcreading(chip, address) 
            x = int(self.chrtWid * ((frequency - startfreq) / span)) + self.mrgnLeft
            y = int(self.chrtHt + self.mrgnTop - ((reading - (bias * removebias)) * self.chrtHt/2.0)) # << scale change afa
            if frequency > startfreq:
                canvas.create_line(oldx, oldy, x, y, fill=colour)
                canvas.update_idletasks() # new code to look like oscilloscope
            oldx = x
            oldy = y
            if frequency == stopfreq:      #<< changed db
                pulseHigh(RESET)
                root.after(100, self.runsweep)

    # continuous sweep
    def runsweep(self):
        if not root.stopflag:
            if root.oneflag:
                root.stopflag = True
            self.sweep()
        else:
            # change relief of button to show selected button
            self.runbutton.config(relief=RAISED)
            self.sweepbutton.config(relief=RAISED)
            self.stopbutton.config(relief=SUNKEN)

    # initialize parameters for first sweep
    def startsweep(self):                                          #<< new function db
        self.stopbutton.config(relief=RAISED)
        #   Initial data to check when Scales need refresh
        self.oldstartfreq = 0 
        self.oldstopfreq = 0
        self.oldspan = 0
        self.oldstep = 0
        #	---------------------------------------------
        root.stopflag = False
        self.runsweep()

    # start single sweep
    def onesweep(self):                                       #<< new function db
        self.sweepbutton.config(relief=SUNKEN)
        root.oneflag = True
        self.startsweep()
        
    # start sweep after clearing stop flag to prevent need for dubble click run button
    def loopsweep(self):                                         #<< changed db
        self.runbutton.config(relief=SUNKEN)
        root.oneflag = False
        self.startsweep()

    # set stop flag
    def stop(self):
        # change relief of button to show selected button     #<< added db
        self.stopbutton.config(relief=SUNKEN)
        self.dispScales()	
        root.stopflag = True

# Assign TK to root
root = Tk()

# Set main window title and menubar
root.wm_title('RPi Wobbulator v2.6.6')
makemenu(root)

# Create instance of class WobbyPi
app = WobbyPi(root, params)

# initialise start and stopflags
root.startflag = 0
root.stopflag = 0
root.oneflag = 0
root.fast = 0

# Start main loop and wait for input from GUI
root.mainloop()

# When program stops, save user parameters
paramFile = open(paramFN, "wb")
params['chrtHt'] = app.chrtHt
params['chrtWid'] = app.chrtWid
params['canvFg'] = app.canvFg
params['canvBg'] = app.canvBg
params['fBegin'] = str(app.fstart.get())
params['fEnd'] = str(app.fstop.get())
params['fIntvl'] = str(app.fstep.get())
params['vgain'] = str(app.gainval.get())
params['vchan'] = str(app.channel.get())
params['colour'] = app.colour.get()
params['bias'] = str(app.bias.get())
params['fast'] = str(app.fast.get())
params['cls'] = str(app.cls.get())
params['grid'] = str(app.grid.get())
params['dB'] = str(app.dB.get())
#print (params)
params = pickle.dump(params, paramFile)
paramFile.close()


