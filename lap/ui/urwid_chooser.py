"""urwid-based chooser UI"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 2 or later"

import logging
log = logging.getLogger(__name__)

import urwid
from urwid import AttrMap

CURSOR_MAX_UP = 'cursor max up'
CURSOR_MAX_DOWN = 'cursor max down'

urwid.command_map['home'] = CURSOR_MAX_UP
urwid.command_map['end'] = CURSOR_MAX_DOWN

class BetterListBox(urwid.ListBox):
    """C{urwid.ListBox} subclass which implements more GUI-like behaviours."""
    def _find_limit(self, reverse=False):
        """Find the first/last focusable widget in the list.

        @todo: Use the modified signal on the list walker to cache this
               for proper performance on long lists.
        """
        # pylint: disable=maybe-no-member
        for x in self.body.positions(reverse=reverse):
            if self.body[x].selectable():
                return x

    def keypress(self, size, key):
        """@todo: Figure out how to get browser-like behaviour where this
                  only gets it if a child widget didn't.
        """
        cmd = self._command_map[key]
        if cmd in [CURSOR_MAX_UP, CURSOR_MAX_DOWN]:
            key = None
            self.focus_position = self._find_limit(cmd == CURSOR_MAX_DOWN)

        return super(BetterListBox, self).keypress(size, key)

    # pylint: disable=too-many-arguments,unused-argument
    def mouse_event(self, size, event, button, col, row, focus):
        """@todo: Make the scrolling less jumpy and figure out how to do
                  it without altering widget focus.
        """
        if urwid.util.is_mouse_press(event):
            if button == 4:
                limit = self._find_limit(False)
                self.focus_position = max(self.focus_position - 1, limit)
            elif button == 5:
                limit = self._find_limit(True)
                self.focus_position = min(self.focus_position + 1, limit)
        return super(BetterListBox, self).mouse_event(
            size, event, button, col, row, focus)

class MyCheckBox(urwid.CheckBox):
    _command_map = urwid.command_map.copy()
    del _command_map['enter']

    # pylint: disable=unused-argument
    def pack(self, size, focus=False):
        """@todo: Submit as patch"""
        return 4 + len(self.get_label()), 1

# pylint: disable=too-many-public-methods
class SetEdit(urwid.Edit):
    def get_results(self):
        return self.get_edit_text().strip().split()

    def set_idx(self, idx, new_state):
        selected = self.get_results()

        idx = str(idx)
        if new_state and idx not in selected:
            selected.append(idx)
        elif not new_state:
            while idx in selected:
                selected.remove(idx)

        self.set_edit_text(' '.join(selected))

class UrwidChooser(object):
    """
    @todo: Implement Tab-based widget focus cycling.
    @todo: Implement find-as-you-type filtering.
    @todo: Other enhancements to consider:
       - https://excess.org/hg/urwid-contrib/file/
       - http://excess.org/urwid/wiki/ApplicationList
        -
    """
    palette = [
        (None, 'light gray', 'black'),
        ('heading', 'white', 'dark red'),
        ('heading_ul', 'white,underline', 'dark red'),
        ('line', 'black', 'dark red'),
        ('row', 'black', 'light gray', 'standout', 'black', 'g85'),
        ('row_zebra', 'black', 'light gray', 'standout', 'black', 'g89'),
        ('selected', 'white', 'dark blue')
    ]
    success = False

    def __init__(self, title, choices):
        """@todo: Implement Home/End support for urwid.Edit"""
        self.choices = choices
        self.w_exec = urwid.Edit(wrap='clip')
        self.w_selected = SetEdit()
        self.w_queue = MyCheckBox([('heading_ul', u'Q'), ('heading', u'ueue')])
        self.w_frame = self._menu(title, choices)

        # TODO: Why is right=1 required to prevent layout glitches?
        self.main = urwid.Padding(self._menu(title, choices), left=1, right=1)

    def _menu(self, title, choices):
        head = AttrMap(urwid.Pile([
            urwid.Divider(),
            urwid.Padding(urwid.Columns([
                AttrMap(urwid.Text(title), 'heading'),
                ('pack', urwid.Text('Exec:')),
                (20, AttrMap(self.w_exec, 'row')),
            ], dividechars=1), left=2, right=2),
            AttrMap(urwid.Divider(u'\N{LOWER ONE QUARTER BLOCK}'), 'line'),
        ]), 'heading')

        body = [urwid.Divider()]
        for pos, path in enumerate(choices):
            cbox = MyCheckBox(path)
            urwid.connect_signal(cbox, 'change', self.item_toggled, pos)
            body.append(AttrMap(urwid.Padding(cbox, left=2, right=2),
                                'row' if pos % 2 else 'row_zebra',
                                focus_map='selected'))
        body += [urwid.Divider()]

        foot = AttrMap(urwid.Pile([
            AttrMap(urwid.Divider(u'\N{UPPER ONE EIGHTH BLOCK}'), 'line'),
            urwid.Padding(urwid.Columns([
                ('pack', urwid.Text('Selected:')),
                AttrMap(self.w_selected, 'row'),
                ('pack', self.w_queue),
            ], dividechars=1), left=2, right=2),
            urwid.Divider(),
        ]), 'heading')

        self.w_list = BetterListBox(urwid.SimpleFocusListWalker(body))
        return urwid.Frame(AttrMap(self.w_list, 'row'),
                           header=head, footer=foot)

    def item_toggled(self, cbox, new_state, idx):  # pylint: disable=W0613
        self.w_selected.set_idx(idx, new_state)

    def run(self, queue, exec_cmd=''):

        self.w_selected.set_edit_text('')
        self.w_exec.set_edit_text(exec_cmd)
        self.w_queue.set_state(queue)

        loop = urwid.MainLoop(self.main, palette=self.palette,
                              unhandled_input=self.unhandled_key)
        loop.screen.set_terminal_properties(256)
        # self.screen.reset_default_terminal_palette()

        loop.run()

        _ids = self.w_selected.get_results()
        while 'q' in _ids:
            self.w_queue.set_state(True)
            _ids.remove('q')

        results = []
        for idx in _ids:
            try:
                results.append(self.choices[int(idx)])
            except (ValueError, IndexError):
                log.warn("Invalid index: %s of %s", idx, len(self.choices))
        return results, self.w_queue.get_state(), self.w_exec.get_edit_text()

    def unhandled_key(self, key):
        if key == 'esc':
            raise urwid.ExitMainLoop()
        elif key == 'enter':
            self.w_list.focus.original_widget.original_widget.set_state(True)
            raise urwid.ExitMainLoop()
        elif key in ['q', 'meta q']:
            self.w_queue.toggle_state()
        # else:
        #     self.w_selected.set_caption(str(key) + ': ')
