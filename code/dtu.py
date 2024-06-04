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

"""A DTU sample"""


import ql_fs
import checkNet
from usr.serial import Serial
from usr.socket import TcpClient
from usr.logging import getLogger
from usr.threading import Thread
from usr.led import Led


logger = getLogger(__name__)


class Configure(dict):
    """Configure for DTU

    actually it is a dict, but add `from_json` and `save` method.
    - `from_json`: read json file and update to self
    - `save`: save self to `path` json file
    """

    def __init__(self, path=None):
        super().__init__()
        self.path = path

    def __repr__(self):
        return 'Configure(path=\'{}\')'.format(self.path)

    def from_json(self, path):
        self.path = path
        if not ql_fs.path_exists(path):
            raise ValueError('\"{}\" not exists!'.format(path))
        self.update(ql_fs.read_json(path))

    def save(self):
        ql_fs.touch(self.path, self)


class DTU(object):
    """DTU Class with simple features:
        - tcp transparent transmission
        - serial read/write
    """

    def __init__(self, name):
        self.name = name
        self.config = Configure()
        self.serial = None
        self.cloud = None
        self.led = None

    def __str__(self):
        return 'DTU(name=\"{}\")'.format(self.name)

    def open_serial(self):
        try:
            self.serial = Serial(**self.config['UART'])
            self.serial.open()
        except Exception as e:
            logger.error('open serial failed: {}'.format(e))
        else:
            logger.info('open serial successfully.')

    def connect_cloud(self):
        try:
            self.cloud = TcpClient(**self.config['SERVER'])
            self.cloud.connect()
        except Exception as e:
            logger.error('connect cloud failed: {}'.format(e))
        else:
            logger.info('conect cloud successfully.')

    def run(self):
        logger.info('{} run...'.format(self))
        self.led = Led(**self.config['LED'])
        self.open_serial()
        self.connect_cloud()
        self.start_uplink_transaction()
        self.start_downlink_transaction()

    def start_uplink_transaction(self):
        logger.info('start up transaction worker thread {}.'.format(Thread.get_current_thread_ident()))
        Thread(target=self.up_transaction_handler).start()

    def start_downlink_transaction(self):
        logger.info('start down transaction worker thread {}.'.format(Thread.get_current_thread_ident()))
        Thread(target=self.down_transaction_handler).start()

    def down_transaction_handler(self):
        while True:
            try:
                data = self.cloud.read(1024)
                logger.info('down transfer msg: {}'.format(data))
                self.serial.write(data)
            except self.cloud.TimeoutError:
                logger.debug('cloud read timeout, continue.')
                continue
            except Exception as e:
                logger.error('down transfer error: {}'.format(e))

    def up_transaction_handler(self):
        while True:
            try:
                data = self.serial.read(1024)
                if data:
                    self.cloud.write(data)
                    self.led.blink(50, 50, 20)
            except Exception as e:
                logger.error('up transfer error: {}'.format(e))
            else:
                logger.info('up transfer success, {} bytes'.format(len(data)))


if __name__ == '__main__':
    # initialize DTU Object
    dtu = DTU('Quectel')

    # read json configure from json file
    dtu.config.from_json('/usr/dev.json')

    # poweron print once
    checknet = checkNet.CheckNetwork(
        dtu.config['PROJECT_NAME'],
        dtu.config['PROJECT_VERSION'],
    )
    checknet.poweron_print_once()

    # check network until ready
    while True:
        rv = checkNet.waitNetworkReady()
        if rv == (3, 1):
            print('network ready.')
            break
        else:
            print('network not ready, error code is {}.'.format(rv))

    # dtu application run forever
    dtu.run()
