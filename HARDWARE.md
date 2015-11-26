

EIModule EIM377 ADS8950 Signal Generator Module
===============================================

The following statements have been made With the premise that the EIM377 AD8950 Signal Generator Module is fitted with a genuine Analog Devices AD9850 IC (and not a Chinese clone).

Analog Devices AD9850 Datasheet specifies the relationship between the maximum input clock frequency and the voltage supply, 125MHz@5V or 110MHz@3.3V.
See Page 2, CLOCK INPUT CHARACTERISTICS

Analog Devices AD9850 Datasheet describes an Agile Clock Generator providing two square wave outputs (one output being the compliment of the other).
See Page 8, Figure 1. Basic AD9850 Clock Generator Application with Low-Pass Filter.


Findings
--------

The EIM377 ADS8950 Signal Generator Module is almost an exact duplicate of the Basic AD9850 Clock Generator Application with Low-Pass Filter circuit, and is therefore designed
to provide two square wave outputs (one output being the compliment of the other).

The EIM377 ADS8950 Signal Generator Module is fitted with a 125MHz Input Clock and is therefore designed to operate with a 5V supply.


Conclusions
-----------

The EIM377 ADS8950 Signal Generator Module
* does not fall within Analog Devices operating specifications when supplied with 3.3V.
* circuit is not intended to provide sine wave outputs, but square wave clock outputs.
* if used, could be modified for better application in the RPI Wobbulator

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
