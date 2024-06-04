# Copyright (c) Quectel Wireless Solution, Co., Ltd.All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import utime
from machine import Pin
from usr.threading import Thread


class Led(object):

    def __init__(self, GPIOn):
        self.__led = Pin(
            getattr(Pin, 'GPIO{}'.format(GPIOn)),
            Pin.OUT,
            Pin.PULL_PD,
            0
        )
        self.__blink_thread = None

    def on(self):
        self.__led.write(1)

    def off(self):
        self.__led.write(0)

    def blink(self, on_remaining, off_remaining, count):
        """start LED blink"""
        if self.__blink_thread and self.__blink_thread.is_running():
            return
        self.__blink_thread = Thread(target=self.__blink_thread_worker, args=(on_remaining, off_remaining, count))
        self.__blink_thread.start()

    def __blink_thread_worker(self, on_remaining, off_remaining, count):
        while count > 0:
            self.on()
            utime.sleep_ms(on_remaining)
            self.off()
            utime.sleep_ms(off_remaining)
            count -= 1
