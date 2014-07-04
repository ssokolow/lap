"""Pure TTY chooser UI"""

from __future__ import print_function, absolute_import

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 2 or later"

import os

# Use readline if available but don't depend on it
try:
    import readline

    # Shut PyFlakes up
    readline  # pylint: disable=pointless-statement
except ImportError:
    pass

def parse_choice(in_str):
    """Parse a string containing one or more integers or Python ranges
    separated by commas.

    @returns: A list of integers

    @attention: Unlike Python, this treats ranges as inclusive of the upper
        bound.
    """
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

# TODO: Document and, if necessary, refactor
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
