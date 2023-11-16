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

import usocket
from usr.logging import getLogger


logger = getLogger(__name__)


class TcpClient(object):
    socket_type = usocket.SOCK_STREAM

    class TimeoutError(Exception):
        pass

    def __init__(self, host, port, timeout=None, keep_alive=None):
        self.__host = host
        self.__port = port
        self.__ip = None
        self.__family = None
        self.__domain = None
        self.__timeout = timeout
        self.__keep_alive = keep_alive
        self.__sock = None

    def __str__(self):
        return '{}(host=\"{}\",port={})'.format(type(self).__name__, self.__host, self.__port)

    @property
    def sock(self):
        if self.__sock is None:
            raise ValueError('Socket Unbound Error')
        return self.__sock

    def __init_args(self):
        rv = usocket.getaddrinfo(self.__host, self.__port)
        if not rv:
            raise ValueError('DNS detect error for addr: {},{}'.format(self.__host, self.__port))
        self.__family = rv[0][0]
        self.__domain = rv[0][3]
        self.__ip, self.__port = rv[0][4]

    def connect(self):
        self.__init_args()
        self.__sock = usocket.socket(self.__family, self.socket_type)
        self.__sock.connect((self.__ip, self.__port))
        if self.__timeout and self.__timeout > 0:
            self.__sock.settimeout(self.__timeout)
        if self.__keep_alive and self.__keep_alive > 0:
            self.__sock.setsockopt(usocket.SOL_SOCKET, usocket.TCP_KEEPALIVE, self.__keep_alive)

    def disconnect(self):
        if self.__sock:
            self.__sock.close()
            self.__sock = None

    def write(self, data):
        return self.sock.send(data) == len(data)

    def read(self, size=1024):
        try:
            return self.sock.recv(size)
        except Exception as e:
            if isinstance(e, OSError) and e.args[0] == 110:
                # read timeout.
                raise self.TimeoutError(str(self))
            else:
                raise e


class UdpClient(TcpClient):
    socket_type = usocket.SOCK_DGRAM
