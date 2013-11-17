# RPi Wobbulator v1.1

# Copyright (C) 2013 Tom Herbison MI0IOU
# Email tom@asliceofraspberrypi.co.uk
# Web <http://www.asliceofraspberrypi.co.uk>

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

# Function to get reading from ADC		
def getadcreading(address):
	h, m, l ,s = bus.transaction(i2c.reading(address,4))[0]
	while (s & 128):
		h, m, l, s  = bus.transaction(i2c.reading(address,4))[0]
	# shift bits to product result
	t = ((h & 0b00000001) << 16) | (m << 8) | l
	# check if positive or negative number and invert if needed
	if (h > 128):
		t = ~(0x020000 - t)
	return (t / 64000)

# Class definition for WobbyPi application
class WobbyPi:

        # Build Graphical User Interface
        def __init__(self, master):
                frame = Frame(master, bd=10)
                frame.pack(fill=BOTH,expand=1)
                # canvas to display results
                global canvas
                canvas = Canvas(frame, width=500, height=500, bg='cyan')
                canvas.grid(row=0, column=0, columnspan=6, rowspan=7)
                canvas.create_rectangle(1, 1, 500, 500)
                # choose channel
                channelframe = LabelFrame(frame, text='Ch', labelanchor='n')
                self.channel = IntVar()
                g1 = Radiobutton(channelframe, text='1', variable=self.channel, value=0)
                g1.grid(row=0)
                g1.select()
                g2 = Radiobutton(channelframe, text='2', variable=self.channel, value=1)
                g2.grid(row=1)
                g3 = Radiobutton(channelframe, text='3', variable=self.channel, value=2)
                g3.grid(row=2)
                g4 = Radiobutton(channelframe, text='4', variable=self.channel, value=3)
                g4.grid(row=3)
                channelframe.grid(row=1, column=6)
                # choose input gain
                gainframe = LabelFrame(frame, text='Gain', labelanchor='n')
                self.gain = IntVar()
                g1 = Radiobutton(gainframe, text='1', variable=self.gain, value=156)
                g1.grid(row=0)
                g1.select()
                g2 = Radiobutton(gainframe, text='2', variable=self.gain, value=157)
                g2.grid(row=1)
                g3 = Radiobutton(gainframe, text='4', variable=self.gain, value=158)
                g3.grid(row=2)
                g4 = Radiobutton(gainframe, text='8', variable=self.gain, value=159)
                g4.grid(row=3)
                gainframe.grid(row=2, column=6)
                # choose a colour
                colourframe = LabelFrame(frame, text='Colour', labelanchor='n')
                self.colour = StringVar()
                c1 = Radiobutton(colourframe, fg='blue', text='[B]', variable=self.colour, value='blue')
                c1.grid(row=0)
                c1.select()
                c2 = Radiobutton(colourframe, fg='red', text='[R]', variable=self.colour, value='red')
                c2.grid(row=1)
                c3 = Radiobutton(colourframe, fg='green', text='[G]', variable=self.colour, value='green')
                c3.grid(row=2)
                c4 = Radiobutton(colourframe, fg='magenta', text='[M]', variable=self.colour, value='magenta')
                c4.grid(row=3)
                c5 = Radiobutton(colourframe, fg='yellow', text='[Y]', variable=self.colour, value='yellow')
                c5.grid(row=4)
                colourframe.grid(row=3, column=6)
                # display a grid
                self.grid = IntVar()
                gridcheck = Checkbutton(frame, text="Grid", variable=self.grid, onvalue=1, offvalue=0, command=self.checkgrid)
                gridcheck.grid(row=4, column=6)
                # remove bias
                self.bias = IntVar()
                biascheck = Checkbutton(frame, text="Bias", variable=self.bias, onvalue=1, offvalue=0)
                biascheck.grid(row=5, column=6)
                # CLS button to clear the screen
                clearbutton = Button(frame, text='CLS', command=self.clearscreen)
                clearbutton.grid(row=6, column=6)
                # RUN button to start the sweep
                runbutton = Button(frame, text='RUN', command=self.runsweep)
                runbutton.grid(row=7, column=6)
                # start frequency for sweep
                fstartlabel = Label(frame, text='Start Freq (Hz)')
                fstartlabel.grid(row=7, column=0)
                self.fstart = StringVar()
                fstartentry = Entry(frame, textvariable=self.fstart, width=10)
                fstartentry.grid(row=7, column=1)
                # stop frequency for sweep
                fstoplabel = Label(frame, text='Stop Freq (Hz)')
                fstoplabel.grid(row=7, column=2)
                self.fstop = StringVar()
                fstopentry = Entry(frame, textvariable=self.fstop, width=10)
                fstopentry.grid(row=7, column=3)
                # increment for sweep
                fsteplabel = Label(frame, text='Step (Hz)')
                fsteplabel.grid(row=7, column=4)
                self.fstep = StringVar()
                fsteplabel = Entry(frame, textvariable=self.fstep, width=8)
                fsteplabel.grid(row=7, column=5)
                
        # display grid
        def checkgrid(self):
                checked = self.grid.get()
                if checked == 1:
                        colour='black'
                else:
                        colour='cyan'
                for x in range(50, 500, 50):
                        canvas.create_line(x, 2, x, 500, fill=colour)
                for y in range(50, 500, 50):
                        canvas.create_line(2, y, 500, y, fill=colour)

        # start frequency sweep
        def runsweep(self):
                pulseHigh(RESET)
                address = int(self.gain.get())
                channel = int(self.channel.get())
                chip = adc_address
                address = (address + (32 * channel))
                changechannel(chip, address)
                startfreq = int(self.fstart.get())
                stopfreq = int(self.fstop.get())
                span = (stopfreq-startfreq)
                step = int(self.fstep.get())
                colour = str(self.colour.get())
                removebias = self.bias.get()
                bias = getadcreading(chip)
                for frequency in range((startfreq - step), (stopfreq + step), step):
                        pulseHigh(RESET)
                        pulseHigh(W_CLK)
                        pulseHigh(FQ_UD)
                        sendFrequency(frequency)
                        reading = getadcreading(chip)
                        x = int(500 * ((frequency - startfreq) / span))
                        y = int(490 - ((reading - (bias * removebias)) * 250))
                        if frequency > startfreq:
                                canvas.create_line(oldx, oldy, x, y, fill=colour)
                        oldx = x
                        oldy = y
                        if frequency == stopfreq:
                                pulseHigh(RESET)
                        
        # clear the screen
        def clearscreen(self):
                canvas.create_rectangle(1, 1, 500, 500, fill='cyan')
                canvas.create_rectangle(1, 1, 500, 500)
                checked = self.grid.get()
                if checked == 1:
                        for x in range(50, 500, 50):
                                canvas.create_line(x, 2, x, 500, fill='black')
                        for y in range(50, 500, 50):
                                canvas.create_line(2, y, 500, y, fill='black')

# Assign TK to root
root = Tk()

# Set main window title
root.wm_title('RPi Wobbulator v1.1')

# Create instance of class WobbyPi
app = WobbyPi(root)

# Start main loop and wait for input from GUI
root.mainloop()


