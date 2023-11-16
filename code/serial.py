# Copyright (c) Quectel Wireless Solution, Co., Ltd.All Rights Reserved.
 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
 
#     http://www.apache.org/licenses/LICENSE-2.0
 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from machine import UART
from usr.threading import Condition, Lock


class Serial(object):

    class TimeoutError(Exception):
        pass

    def __init__(self, port=2, baudrate=115200, bytesize=8, parity=0, stopbits=1, flowctl=0, rs485_config=None):
        self.__port = port
        self.__baudrate = baudrate
        self.__bytesize = bytesize
        self.__parity = parity
        self.__stopbits = stopbits
        self.__flowctl = flowctl
        self.__rs485_config = rs485_config
        self.__uart = None
        self.__r_cond = Condition()
        self.__w_cond = Lock()

    def __repr__(self):
        return '<UART{},{},{},{},{},{},{}>'.format(
            self.__port, self.__baudrate, self.__bytesize,
            self.__parity, self.__stopbits, self.__flowctl,
            self.__rs485_config
        )

    @property
    def uart(self):
        if self.__uart is None:
            raise TypeError('uart not open.')
        return self.__uart

    def open(self):
        """open it"""
        self.__uart = UART(
            getattr(UART, 'UART{}'.format(self.__port)),
            self.__baudrate,
            self.__bytesize,
            self.__parity,
            self.__stopbits,
            self.__flowctl
        )
        if isinstance(self.__rs485_config, dict):
            gpio_num = getattr(UART, "GPIO{}".format(self.__rs485_config['gpio_num']))
            direction = self.__rs485_config['direction']
            self.__uart.control_485(gpio_num, direction)

        self.__uart.set_callback(self.__uart_cb)  # register UART callback

    def close(self):
        """close it"""
        self.__uart.close()
        self.__uart = None

    def __uart_cb(self, _):
        """new data coming callback, we need this callback to unblock `read` method."""
        with self.__r_cond:
            self.__r_cond.notify_all()  # notify condition, `condition.wait` will be unblocked after this method call

    def write(self, data):
        """write bytes data to current serial"""
        with self.__w_cond:
            return self.uart.write(data)

    def read(self, size, timeout=None):
        """read bytes from serial.

        :param size: int, max read size you wanna
        :param timeout: int, timeout seconds
        :raise: after timeout seconds if no data read, just raise self.TimeoutError
        :return: bytes data actually read
        """
        with self.__r_cond:
            if self.__r_cond.wait_for(lambda: self.uart.any() != 0, timeout=timeout):
                return self.uart.read(min(size, self.uart.any()))
            else:
                raise self.TimeoutError('serial read timeout.')
