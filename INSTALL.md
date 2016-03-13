Installation
============


Required Hardware Configuration
-------------------------------

*Enable I2C*
sudo raspi-config
    "Enable/Disable automatic loading of I2C"

*Load I2C modules at boot*
egrep -q "^i2c-bcm2708\>" /etc/modules || sudo tee -a "i2c-bcm2708" /etc/modules
egrep -q "^i2c-dev\>" /etc/modules || sudo tee -a "i2c-dev" /etc/modules

*Apply changes*
sudo reboot

*Check Wobbulator is detected*

sudo i2cdetect -y 1 | egrep -q "\<68\>" && echo OK

*Or*

sudo i2cdetect -y 0 | egrep -q "\<68\>" && echo OK
                  ^ Early 256MB Pi's (with Revision < 0004)
                    NOTE: you will need to edit /opt/RPi_Wobbulator.git/Wobby/ADC.py
                    Find below and change the '1' to a '0'
                    # Default I2C bus of ADC chip
                    _adc_smbus = 1


Required Software Packages
--------------------------

sudo apt-get update
sudo apt-get upgrade

*Install the following packages*
(some of them may already be installed)

sudo apt-get install i2c-tools
sudo apt-get install python3 python3-rpi.gpio python3-smbus python3-tk
sudo apt-get install ghostscript ttf-dejavu
sudo apt-get install git


RPi Wobbulator Software
-----------------------

*Clone the RPi_Wobbulator Repository*
sudo git clone https://github.com/gryrmln/RPi_Wobbulator.git /opt/RPi_Wobbulator.git
sudo chown -R pi:pi /opt/RPi_Wobbulator.git

*Still need to run as root to access GPIO, either*

cd /opt/RPi_Wobbulator.git
sudo python3 rpi_wobbulator.py

*or*

sudo PYTHONPATH=/opt/RPi_Wobbulator.git python3 /opt/RPi_Wobbulator.git/rpi_wobbulator.py

