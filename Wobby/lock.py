# RPiWobbulator Lock Module
# vim:ai:sw=4:ts=8:et:fileencoding=ascii
#
# Copyright (C) 2014 Gray Remlin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import fcntl

class LockError(Exception):
    """ Locking not possible """


class Lock:

    _fp = None

    def __init__(self, lockdevice):
        """ Immediately lock when possible """

        lockfile = "/run/lock/Wobby." + lockdevice

        # This looks overly complicated, but if the lockfile exists we don't
        # want to truncate it and loose the pid in the lockfile of the locking
        # process in the case where it is locked. Equally, we dont want to
        # append our pid onto the previous contents (the previous process pid)
        # when it is no longer locked by that previous process.
        # If the lockfile doesn't exist, create it.
        try:
            # Open a lockfile 'read\write'
            fp = open(lockfile, 'r+')
        except:
            try:
                # Open a lockfile 'create\append' 
                fp = open(lockfile, 'a+')
            except:
                raise LockError("Failure to open lockfile {}".format(fp.name))

        try:
            # Exclusively lock the file
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except:
            fp.seek(1)
            pid = fp.read().strip()[:7]
            fp.close()
            if not pid:
                pid = '-1'
            raise LockError("{} already Locked ({} pid={})".format(
                                                    lockdevice, lockfile, pid))
        else:
            # got the lock
            self._fp = fp
            # write our pid
            fp.write(" {}\n".format(os.getpid()))
            fp.truncate()
            fp.flush()
            # hold open to keep the lock

    def release(self):
        if self._fp is not None:
            self._fp.close()
            self._fp = None

