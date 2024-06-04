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

import _thread
import usys
import utime
import osTimer


class Lock(object):

    def __init__(self):
        self.__lock = _thread.allocate_lock()
        self.__owner = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *args, **kwargs):
        self.release()

    def acquire(self):
        flag = self.__lock.acquire()
        self.__owner = _thread.get_ident()
        return flag

    def release(self):
        self.__owner = None
        return self.__lock.release()

    def locked(self):
        return self.__lock.locked()

    @property
    def owner(self):
        return self.__owner


class Waiter(object):
    """WARNING: Waiter object can only be used once."""

    def __init__(self):
        self.__lock = Lock()
        self.__lock.acquire()
        self.__gotit = True

    @property
    def unlock_timer(self):
        timer = getattr(self, '__unlock_timer__', None)
        if timer is None:
            timer = osTimer()
            setattr(self, '__unlock_timer__', timer)
        return timer

    def __auto_release(self, _):
        if self.__release():
            self.__gotit = False
        else:
            self.__gotit = True

    def acquire(self, timeout=-1):
        """timeout <= 0 for blocking forever."""
        if not self.__lock.locked():
            raise RuntimeError('Waiter object can only be used once.')
        self.__gotit = True
        if timeout > 0:
            self.unlock_timer.start(timeout * 1000, 0, self.__auto_release)
        self.__lock.acquire()  # block here
        if timeout > 0:
            self.unlock_timer.stop()
        self.__release()
        return self.__gotit

    def __release(self):
        try:
            self.__lock.release()
        except RuntimeError:
            return False
        return True

    def release(self):
        return self.__release()


class Condition(object):

    def __init__(self, lock=None):
        if lock is None:
            lock = Lock()
        self.__lock = lock
        self.__waiters = []
        self.acquire = self.__lock.acquire
        self.release = self.__lock.release

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *args, **kwargs):
        self.release()

    def __is_owned(self):
        return self.__lock.locked() and self.__lock.owner == _thread.get_ident()

    def wait(self, timeout=None):
        if not self.__is_owned():
            raise RuntimeError('cannot wait on un-acquired lock.')
        waiter = Waiter()
        self.__waiters.append(waiter)
        self.release()
        gotit = False
        try:
            if timeout is None:
                gotit = waiter.acquire()
            else:
                gotit = waiter.acquire(timeout)
            return gotit
        finally:
            self.acquire()
            if not gotit:
                try:
                    self.__waiters.remove(waiter)
                except ValueError:
                    pass

    def wait_for(self, predicate, timeout=None):
        endtime = None
        remaining = timeout
        result = predicate()
        while not result:
            if remaining is not None:
                if endtime is None:
                    endtime = utime.time() + remaining
                else:
                    remaining = endtime - utime.time()
                    if remaining <= 0.0:
                        break
            self.wait(remaining)
            result = predicate()
        return result

    def notify(self, n=1):
        if not self.__is_owned():
            raise RuntimeError('cannot wait on un-acquired lock.')
        if n < 0:
            raise ValueError('invalid param, n should be >= 0.')
        waiters_to_notify = self.__waiters[:n]
        for waiter in waiters_to_notify:
            waiter.release()
            try:
                self.__waiters.remove(waiter)
            except ValueError:
                pass

    def notify_all(self):
        if not self.__is_owned():
            raise RuntimeError('cannot wait on un-acquired lock.')
        self.notify(n=len(self.__waiters))


class Thread(object):

    def __init__(self, target=None, args=(), kwargs=None):
        self.__target = target
        self.__args = args
        self.__kwargs = kwargs or {}
        self.__ident = None

    def __repr__(self):
        return '<Thread {}>'.format(self.__ident)

    def is_running(self):
        if self.__ident is None:
            return False
        else:
            return _thread.threadIsRunning(self.__ident)

    def start(self):
        if not self.is_running():
            self.__ident = _thread.start_new_thread(self.run, ())

    def stop(self):
        if self.is_running():
            _thread.stop_thread(self.__ident)
            self.__ident = None

    def run(self):
        try:
            self.__target(*self.__args, **self.__kwargs)
        except Exception as e:
            usys.print_exception(e)

    @property
    def ident(self):
        return self.__ident

    @classmethod
    def get_current_thread_ident(cls):
        return _thread.get_ident()