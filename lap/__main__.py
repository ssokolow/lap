#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Locate and Play

Description:
- A quick wrapper to make playing songs via the local command quick and easy.
- Accepts multiple space- and/or comma-separated choices after presenting the
  results.
- Can enqueue or enqueue and play.
- Can show full paths or just filenames.
- Will behave in a sane fashion when asked to enqueue and play multiple files.
- Can randomly select a given number of tracks from a folder tree.

Note:
- If you decide that you want to enqueue after you see the results and you
  forgot to pass in -q on the command-line, just throw q into your result
  string. It doesn't matter whether it's on it's own or as a prefix or suffix
  to another entry.

--snip--

TODO:
 - Don't pass nonexistant paths to Audacious. It actually adds them to the
   playlist.
 - Still needs more refactoring.
 - Decide how to expose filtering options from locate.
 - Implement /-triggered "search within these results" for lap.
 - Look into "insert before/after current song" as an MPRIS option
 - Complete the list of extensions for ModPlug and UADE (3rd-party)
 - Support an "all" keyword and an alternative to Ctrl+C for cancel. (maybe 0)
 - Clean up the code
 - Allow non-file:// URLs.
"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 2 or later"
from version import __version__

from filetypes import OK_EXTS, BLACKLISTED_EXTS

USE_PAGER = False   # Should we page output if it's more than a screenful?
DEFAULT_RAND_COUNT = 10

locate_command = ['locate', '-i']

# ========== Configuration Ends ==========

import fnmatch, logging, os, random, string, subprocess, sys
log = logging.getLogger(__name__)

try:
    from lap.ui.urwid_chooser import UrwidChooser
except ImportError:
    UrwidChooser = None

# Use readline if available but don't depend on it
try:
    import readline
    readline  # Shut PyFlakes up
except ImportError:
    pass

try:
    import dbus
    from dbus.exceptions import DBusException
    import xml.etree.cElementTree as ET
except ImportError:
    # Let the exception handler wrapping the MPRISAdder() call handle it
    DBusException = Exception
    pass

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
                    self.pq_add = self._get_dbus_if(name,
                        '/org/atheme/audacious',
                        'org.atheme.audacious').PlayqueueAdd
                else:
                    self.pq_add = lambda x: None

                break
        else:
            raise DBusException("No media player with MPRIS AddTrack found")

    def _get_dbus_if(self, name, path, interface):
        obj = self.bus.get_object(name, path)
        return dbus.Interface(obj, dbus_interface=interface)

    def get_player_names(self):
        """Find all D-Bus names for MPRIS-compatible players"""
        ispect_if = self._get_dbus_if(
                'org.freedesktop.DBus', '/', 'org.freedesktop.DBus')
        return [x for x in ispect_if.ListNames() if x.startswith('org.mpris.')]

    def get_method_names(self, interface):
        """Get all method names within C{self.ifname} on the given interface.

        @todo: Extract ifname from the passed-in interface object.
        """
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

def sh_quote(file):
    """Reliably quote a string as a single argument for /bin/sh

    Borrowed from the pipes module in Python 2.6.2 stdlib and fixed to quote
    empty strings properly and pass completely safechars strings through.
    """
    _safechars = string.ascii_letters + string.digits + '!@%_-+=:,./'
    _funnychars = '"`$\\'           # Unsafe inside "double quotes"

    if not file:
        return "''"

    for c in file:
        if c not in _safechars:
            break
    else:
        return file

    if not [x for x in file if x not in _safechars]:
        return file
    elif '\'' not in file:
        return '\'' + file + '\''

    res = ''
    for c in file:
        if c in _funnychars:
            c = '\\' + c
        res = res + c
    return '"' + res + '"'


def gather_random(roots, wanted_count):
    """Use C{os.walk} to choose C{wanted_count} files from C{roots}.

    @type roots: C{list} of C{basestring}
    """
    choices = []
    for root in roots:
        for fldr, dirs, files in os.walk(root):
            choices.extend(os.path.join(fldr, x) for x in files
                    if not os.path.splitext(x)[1].lower() in BLACKLISTED_EXTS)

    chosen = []
    for i in range(0, wanted_count):
        if choices:
            # We don't want duplicates
            chosen.append(choices.pop(random.randrange(0, len(choices))))

    return chosen

#TODO: Refactor and reuse elsewhere
def get_results(query, locate_cmd=locate_command):
    """Retrieve matches for C{query} in L{OK_EXTS} using L{locate_command}."""
    if isinstance(query, basestring):
        query = [query]

    results, cmd = [], locate_cmd + query
    for line in subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout:
        result = line.strip()
        if os.path.splitext(result)[1] in OK_EXTS:
            results.append(result)
    results.sort()
    return results

#TODO: Document and, if necessary, refactor
def parse_choice(in_str):
    try:
        return [int(in_str)]
    except ValueError:
        choices = []
        for x in in_str.replace(',', ' ').split():
            try:
                choices.append(int(x))
            except ValueError:
                try:
                    first, last = [int(y) for y in x.split(':', 1)]
                    choices.extend(range(first, last + 1))
                except ValueError:
                    print("Not an integer or range: %s" % x)
        return choices

#TODO: Document and, if necessary, refactor
def choose(results, strip_path, enqueue):
        # Draw the menu
        for pos, val in enumerate(results):
            val = strip_path and os.path.basename(val) or val
            print("%3d) %s" % (pos + 1, val))

        choices = raw_input("Choice(s) (Ctrl+C to cancel): ")

        if 'q' in choices.lower():
            enqueue = True
            choices = choices.replace('q', '')  # FIXME: This will distort
                 # the "Not an integer" message for values containing "q".

        output = []
        for index in parse_choice(choices):
            if index > 0 and index <= len(results):
                output.append(results[index - 1])
            else:
                print("Invalid result index: %d" % index)

        return output, enqueue

#TODO: Split this up more
def main():
    cmd = os.path.split(sys.argv[0])[1]
    usage_t = (cmd.lower() in ('ap', 'aq')) and '<path> ...' or '<keyword> ...'

    from optparse import OptionParser
    op = OptionParser(version="%%prog v%s" % __version__,
        usage="%prog [options] " + usage_t,
        description=__doc__.replace('\r\n', '\n').split('\n--snip--\n')[0])

    # TODO: Reconcile all these. Maybe make all input via options and then
    #       use configurable personalities to map positional arguments to
    #       options.
    op.add_option("-0", "--print0", action="store_true", dest="print_null",
            default=False, help="Display the list of results, separated by "
                                "NULL characters. (good for `xargs -0`)")
    op.add_option("-e", "--exec", action="store", dest="exe_cmd",
        default='', help="Use this command to enqueue/play rather than "
                         "the default.")
    op.add_option("-l", "--locate", action="store_true", dest="locate",
            default=(cmd.lower() in ('lap', 'laq')),
            help="Treat the arguments as search keywords rather than "
                 "paths. (default if called as 'lap' or 'laq')")
    op.add_option("-n", "--song-count", action="store", type=int,
        dest="wanted_count", default=DEFAULT_RAND_COUNT, metavar="NUM",
        help="Request that NUM randomly-chosen songs be picked rather than"
             " %default.")
    op.add_option("--no-urwid", action="store_false", dest="urwid",
        default=True, help="Don't use urwid-based ncurses chooser even if it "
                           "is available.")
    op.add_option("-p", "--print", action="store_true", dest="print_nl",
            default=False, help="Display the list of results, one per line.")
    op.add_option("-P", "--show_path", action="store_true",
            dest="show_path", default=False,
            help="Show the full path to each result.")
    op.add_option('-q', '--quiet', action="count", dest="quiet",
        default=0, help="Decreased verbosity. Use twice for extra effect")
    op.add_option("-Q", "--enqueue", action="store_true", dest="enqueue",
            default=(cmd.lower() in ('aq', 'laq', 'raq')),
            help="Don't start the song playing after enqueueing it. "
                 "(default if called as 'aq' or 'laq')")
    op.add_option("-r", "--random", action="store_true", dest="random",
            default=(cmd.lower() in ('rap', 'raq')),
            help="Select X entries at random from the provided paths. "
                 "(default if called as 'rap' or 'raq')")
    op.add_option("--sh", action="store_true", dest="print_quoted",
            help="Like --print but shell-quoted for use with tab completion "
                 "via backticks")
    op.add_option('-v', '--verbose', action="count", dest="verbose",
        default=2, help="Increased verbosity. Use twice for extra effect")

    # Allow pre-formatted descriptions
    op.formatter.format_description = lambda description: description

    (opts, args) = op.parse_args()

    # Set up clean logging to stderr
    log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING,
                  logging.INFO, logging.DEBUG]
    opts.verbose = min(opts.verbose - opts.quiet, len(log_levels) - 1)
    opts.verbose = max(opts.verbose, 0)
    logging.basicConfig(level=log_levels[opts.verbose],
                        format='%(levelname)s: %(message)s')

    if not args:
        try:
            #TODO: Do I really want this case to require Python 2.7?
            args.append(subprocess.check_output(
                ['xdg-user-dir', 'MUSIC']).strip())
        except OSError, err:
            if err.errno == 2:
                print("Could not use 'xdg-user-dir' to locate your music "
                      "library. Please provide an argument.")
                sys.exit(1)
            else:
                raise

    # If opts.locate, resolve args using `locate` first.
    if opts.locate:
        # Implement implicit AND for locate (default is implicit OR)
        results = (len(args) > 0) and get_results(args.pop(0)) or []
        for kw in args:
            results = [x for x in results
                    #TODO: Implement locate's "only *%s* if no globbing chars"
                    if fnmatch.fnmatch(x.lower(), '*%s*' % kw.lower())]
    else:
        results = [os.path.abspath(x) for x in args]

    # TODO: Decide whether to support locate without chooser
    if opts.random:
        results = gather_random(results, opts.wanted_count)
    elif opts.locate and not (opts.print_nl or opts.print_null):
        try:
            argv = cmd + ' ' + ' '.join(sys.argv[1:])
            if UrwidChooser and opts.urwid:
                chooser = UrwidChooser(argv, results)
                results, opts.enqueue, opts.exe_cmd = chooser.run(
                        opts.enqueue, opts.exe_cmd)
            else:
                results, opts.enqueue = choose(
                    results, not opts.show_path, opts.enqueue)
        except KeyboardInterrupt:
            results = []
    else:
        results = results

    # Branch for --exec, MPRIS, or fallback to print
    if opts.exe_cmd:
        add_func = lambda paths, play: subprocess.call([opts.exe_cmd] + paths)
    else:
        try:
            add_func = MPRISAdder().add_tracks
        except (NameError, DBusException):
            print("Cannot connect to D-Bus session bus. Assuming --print.")
            add_func = lambda paths, play: None
            opts.print_nl = True

    # Feed the results to the player
    if opts.print_quoted:
        print(' '.join(sh_quote(x) for x in results))
    elif opts.print_null:
        print('\0'.join(results))
    elif opts.print_nl:
        print('\n'.join(results))
    elif results:
        add_func(results, not opts.enqueue)
    else:
        print("No Results")

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 :
