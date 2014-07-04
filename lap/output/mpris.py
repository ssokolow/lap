"""MPRIS-based backend (currently only developed for Audacious Media Player)"""

from __future__ import print_function, absolute_import

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 2 or later"

import logging, os, sys
log = logging.getLogger(__name__)

import dbus
from dbus.exceptions import DBusException
import xml.etree.cElementTree as ET

class MPRISAdder(object):
    """Convenience wrapper for accessing MPRIS AddTrack via D-Bus.
    @todo: Blog about the tasks within this. I had to piece it together.
        - Dynamically retrieving a suitable MPRIS interface.
        - Testing for method existence
    """
    ifname = 'org.freedesktop.MediaPlayer'

    def __init__(self, bus=None):
        """
        @todo: Support a configurable preference for a specific player
        @todo: Make sure I properly support both MPRIS1 and MPRIS2.
        """
        self.bus = bus or dbus.Bus(dbus.Bus.TYPE_SESSION)

        for name in self.get_player_names():
            iface = self._get_dbus_if(name, '/TrackList', self.ifname)
            if 'AddTrack' in self.get_method_names(iface):
                self.iface = iface

                # FIXME: Figure out why qdbusviewer can introspect this but I
                # can't. (Could be related to how qdbus segfaults calling it)
                if name == 'org.mpris.audacious':
                    # pylint: disable=bad-continuation
                    self.pq_add = self._get_dbus_if(name,
                        '/org/atheme/audacious',
                        'org.atheme.audacious').PlayqueueAdd
                else:
                    self.pq_add = lambda x: None

                break
        else:
            raise DBusException("No media player with MPRIS AddTrack found")

    def _get_dbus_if(self, name, path, interface):
        """Shorthand wrapper to retrieve a C{dbus.Interface}"""
        obj = self.bus.get_object(name, path)
        return dbus.Interface(obj, dbus_interface=interface)

    def get_player_names(self):
        """Find all D-Bus names for MPRIS-compatible players"""
        # pylint: disable=bad-continuation
        ispect_if = self._get_dbus_if(
                'org.freedesktop.DBus', '/', 'org.freedesktop.DBus')
        return [x for x in ispect_if.ListNames() if x.startswith('org.mpris.')]

    def get_method_names(self, interface):
        """Get all method names within C{self.ifname} on the given interface.

        @todo: Extract ifname from the passed-in interface object.
        """
        # pylint: disable=bad-continuation
        dom = ET.fromstring(interface.Introspect(
                dbus_interface='org.freedesktop.DBus.Introspectable'))
        funcs = dom.findall(".//interface[@name='" + self.ifname + "']/method")
        return [x.get('name') for x in funcs]

    def add_tracks(self, paths, play=False):
        """Add the given tracks to the player's playlist and, C{if play=True},
        start the first one playing.
        """
        for path in paths:
            if not os.path.exists(path):
                log.error("File does not exist: %s", path)

            if isinstance(path, str):
                path = path.decode(sys.getfilesystemencoding())
            file_url = 'file://' + path

            self.iface.AddTrack(file_url, play)
            if self.pq_add and not play:
                self.pq_add(self.iface.GetLength() - 1)
            play = False  # Only start the first one playing
