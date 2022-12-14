# -*- coding: utf-8 -*-
"""
Interfuse to do confocal scans with spectrometer data rather than APD count rates.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import time
import numpy as np

from core.module import Base
from core.configoption import ConfigOption
from core.connector import Connector
from interface.confocal_scanner_interface import ConfocalScannerInterface


class SpectrometerScannerInterfuse(Base, ConfocalScannerInterface):
    """ This interfuse merge scanner and spectrometer logics to do SPIM via usual confocal logic """

    scanner = Connector(interface='ConfocalScannerInterface')
    counter = Connector(interface='SlowCounterInterface')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self._frequency = None
        self._count_data = None
        self._pointer = None

        self.scan_point_function = None
        self.scan_point_channels = None

    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        self._count_data = None

    def on_deactivate(self):
        """ Deactivation of the module """
        pass

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs can access it. """
        return self.scanner().reset_hardware()

    def get_position_range(self):
        """ Returns the physical range of the scanner.
        This is a direct pass-through to the scanner HW.

        @return float [4][2]: array of 4 ranges with an array containing lower and upper limit
        """
        return self.scanner().get_position_range()

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner. """
        return self.scanner().set_position_range(mmyrange=myrange)

    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card. """
        return self.scanner().set_voltage_range(mmyrange=myrange)

    def get_scanner_axes(self):
        """ Pass through scanner axes. """
        return self.scanner().get_scanner_axes()

    def get_scanner_count_channels(self):
        """ Returns the list of channels that are recorded while scanning an image.

        @return list(str): channel names

        Most methods calling this might just care about the number of channels.
        """
        if self.scan_point_channels:
            return self.scan_point_channels()
        else:
            return self.scanner().get_scanner_count_channels()

    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.
        This is a direct pass-through to the scanner HW

        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock

        @return int: error code (0:OK, -1:error)
        """
        # Todo : should this function set the exposure time ? Maybe not.
        if clock_frequency is not None:
            self._frequency = clock_frequency
        return 0

    def set_up_scanner(self, counter_channel=None, photon_source=None, clock_channel=None, scanner_ao_channels=None):
        """ Configures the actual scanner with a given clock. """
        return 0

    def scanner_set_position(self, x=None, y=None, z=None, a=None):
        """ Move stage to x, y, z, a.

        @param float x: position in x-direction
        @param float y: position in y-direction
        @param float z: position in z-direction
        @param float a: position in a-direction

        @return int: error code (0:OK, -1:error)
        """
        return self.scanner().scanner_set_position(x=x, y=y, z=z, a=a)

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """
        return self.scanner().get_scanner_position()

    def set_scan_point_function(self, scan_point_function=None, scan_point_channels=None):
        """ Set the function to use at each point of the scan and the function giving the related channels name.

        @param (function) scan_point_function : function taking in argument the scanning index and position and returning
         a ndarray of acquired data.
        @param (function) scan_point_channels : function returning a list of channels with the same length than the array
        returned by scan_point_function.

        """

        self.scan_point_function = scan_point_function
        self.scan_point_channels = scan_point_channels

    def scan_line(self, line_path=None, pixel_clock=False):
        """ Scans a line and returns the counts on that line.

        @param float[][4] line_path: array of 4-part tuples defining the voltage points
        @param bool pixel_clock: whether we need to output a pixel clock for this line

        @return float[]: the photon counts per second
        """
        line_path = line_path.T
        self._count_data = np.zeros((len(line_path), len(self.get_scanner_count_channels())))
        for i, position in enumerate(line_path):
            self._pointer = i
            self.scanner().scanner_set_position(*position)
            if self.scan_point_function:
                data = self.scan_point_function(point_index=i, point_position=position)
            else:
                data = self.counter().get_counter()
            self._count_data[i] = data.flatten()
        return self._count_data

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards. """
        return 0
        #return self.scanner().close_scanner()

    def close_scanner_clock(self):
        """ Closes the clock and cleans up afterwards. """
        return 0
        #return self.scanner().close_scanner_clock()

    def get_last_spectrum(self):
        """ Helper tools to get the last acquired spectrum """
        if self._count_data is not None and self._pointer > 0:
            return self._count_data[self._pointer - 1]
