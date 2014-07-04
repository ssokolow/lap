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

from __future__ import print_function

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 2 or later"
from lap.version import __version__

from lap.filetypes import OK_EXTS, BLACKLISTED_EXTS

USE_PAGER = False   # Should we page output if it's more than a screenful?
DEFAULT_RAND_COUNT = 10

locate_command = ['locate', '-i']

# ========== Configuration Ends ==========

import string  # pylint: disable=deprecated-module
import fnmatch, logging, os, random, subprocess, sys
log = logging.getLogger(__name__)

from lap.ui.fallback_chooser import choose
try:
    from lap.ui.urwid_chooser import UrwidChooser
except ImportError:
    UrwidChooser = None  # pylint: disable=invalid-name

try:
    from lap.backends.mpris import MPRISAdder, DBusException
except ImportError:
    DBusException = None  # pylint: disable=invalid-name

def sh_quote(text):
    """Reliably quote a string as a single argument for /bin/sh

    Borrowed from the pipes module in Python 2.6.2 stdlib and fixed to quote
    empty strings properly and pass completely safechars strings through.
    """
    _safechars = string.ascii_letters + string.digits + '!@%_-+=:,./'
    _funnychars = '"`$\\'           # Unsafe inside "double quotes"

    if not text:
        return "''"

    for char in text:
        if char not in _safechars:
            break
    else:
        return text

    if not [x for x in text if x not in _safechars]:
        return text
    elif '\'' not in text:
        return '\'' + text + '\''

    res = ''
    for char in text:
        if char in _funnychars:
            char = '\\' + char
        res = res + char
    return '"' + res + '"'


def gather_random(roots, wanted_count):
    """Use C{os.walk} to choose C{wanted_count} files from C{roots}.

    @type roots: C{list} of C{basestring}
    """
    choices = []
    for root in roots:
        for fldr, _, files in os.walk(root):
            choices.extend(os.path.join(fldr, x) for x in files
                    if not os.path.splitext(x)[1].lower() in BLACKLISTED_EXTS)

    chosen = []
    for _ in range(0, wanted_count):
        if choices:
            # We don't want duplicates
            chosen.append(choices.pop(random.randrange(0, len(choices))))

    return chosen

#TODO: Refactor and reuse elsewhere
def get_results(query, locate_cmd=locate_command):  # pylint: disable=W0102
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


#TODO: Split this up more
def main():
    cmd = os.path.split(sys.argv[0])[1]
    usage_t = (cmd.lower() in ('ap', 'aq')) and '<path> ...' or '<keyword> ...'

    from optparse import OptionParser
    opars = OptionParser(version="%%prog v%s" % __version__,
        usage="%prog [options] " + usage_t,
        description=__doc__.replace('\r\n', '\n').split('\n--snip--\n')[0])

    # TODO: Reconcile all these. Maybe make all input via options and then
    #       use configurable personalities to map positional arguments to
    #       options.
    opars.add_option("-0", "--print0", action="store_true", dest="print_null",
            default=False, help="Display the list of results, separated by "
                                "NULL characters. (good for `xargs -0`)")
    opars.add_option("-e", "--exec", action="store", dest="exe_cmd",
        default='', help="Use this command to enqueue/play rather than "
                         "the default.")
    opars.add_option("-l", "--locate", action="store_true", dest="locate",
            default=(cmd.lower() in ('lap', 'laq')),
            help="Treat the arguments as search keywords rather than "
                 "paths. (default if called as 'lap' or 'laq')")
    opars.add_option("-n", "--song-count", action="store", type=int,
        dest="wanted_count", default=DEFAULT_RAND_COUNT, metavar="NUM",
        help="Request that NUM randomly-chosen songs be picked rather than"
             " %default.")
    opars.add_option("--no-urwid", action="store_false", dest="urwid",
        default=True, help="Don't use urwid-based ncurses chooser even if it "
                           "is available.")
    opars.add_option("-p", "--print", action="store_true", dest="print_nl",
            default=False, help="Display the list of results, one per line.")
    opars.add_option("-P", "--show_path", action="store_true",
            dest="show_path", default=False,
            help="Show the full path to each result.")
    opars.add_option('-q', '--quiet', action="count", dest="quiet",
        default=0, help="Decreased verbosity. Use twice for extra effect")
    opars.add_option("-Q", "--enqueue", action="store_true", dest="enqueue",
            default=(cmd.lower() in ('aq', 'laq', 'raq')),
            help="Don't start the song playing after enqueueing it. "
                 "(default if called as 'aq' or 'laq')")
    opars.add_option("-r", "--random", action="store_true", dest="random",
            default=(cmd.lower() in ('rap', 'raq')),
            help="Select X entries at random from the provided paths. "
                 "(default if called as 'rap' or 'raq')")
    opars.add_option("--sh", action="store_true", dest="print_quoted",
            help="Like --print but shell-quoted for use with tab completion "
                 "via backticks")
    opars.add_option('-v', '--verbose', action="count", dest="verbose",
        default=2, help="Increased verbosity. Use twice for extra effect")

    # Allow pre-formatted descriptions
    opars.formatter.format_description = lambda description: description

    (opts, args) = opars.parse_args()

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
        for keyword in args:
            results = [x for x in results
                    #TODO: Implement locate's "only *%s* if no globbing chars"
                    if fnmatch.fnmatch(x.lower(), '*%s*' % keyword.lower())]
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
