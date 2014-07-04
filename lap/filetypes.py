"""Definitions for filetype filtering"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 2 or later"

# TODO: Redesign this to support ack-like command-line filter options
ADLIB_EXTS = ['.a2m', '.adl', '.amd', '.bam', '.cff', '.cmf', '.d00', '.dfm',
              '.dmo', '.dro', '.dtm', '.hsc', '.hsp', '.jbm', '.ksm', '.laa',
              '.lds', '.mad', '.mkj', '.msc', '.mtk', '.rad', '.raw', '.rix',
              '.rol', '.sat', '.sa2', '.sci', '.sng', '.imf', '.wlf', '.xad',
              '.xsm', '.m', '.adlib']

CONSOLE_EXTS = ['.adx', '.gbs', '.gym', '.hes', '.kss', '.nsf', '.nsfe', '.ay',
                '.psf', '.sap', '.sid', '.spc', '.vgm', '.vgz', '.vtx', '.ym',
                '.minipsf']

# pylint: disable=bad-whitespace
MIDI_EXTS     = ['.mid', '.rmi', '.midi']
MODULE_EXTS   = [',mod', '.s3m', '.stm', '.xm', '.it']
PLAYLIST_EXTS = ['.cue', '.m3u', '.pls', '.xspf']
VIDEO_FILES   = ['.avi', '.flv', '.m4v', '.mov', '.mp4', '.webm', '.rm']
WAVEFORM_EXTS = ['.aac', '.ac3', '.aif', '.aiff', '.ape', '.au', '.flac',
                 '.m4a', '.mp2', '.mp3', '.mpc', '.ogg', '.shn', '.snd',
                 '.tta', '.voc', '.wav', '.wma', '.wv']

# Edit these lines to choose the kind of files to be filtered for.
# By default, playlist extensions are excluded.
OK_EXTS = (WAVEFORM_EXTS + MODULE_EXTS + CONSOLE_EXTS + MIDI_EXTS +
           ADLIB_EXTS    + VIDEO_FILES)
# If you want true format filtering, YOU write the mimetype cache.

# Blacklist used for gather_random()
BLACKLISTED_EXTS = [
    '.m3u', '.pls', '.xspf'     # Playlists (just enqueue directly)
    '.jpg', '.jpeg', '.png', '.gif', '.bmp',  # Images (eg. Cover Art)
    '.txt', '.html', '.htm',    # Not media
    '.sid',                     # Capable of looping infinitely
    '.mid', '.midi', '.rmi',    # Require the keyboard to be turned on manually
]
# Note: SID is actually blacklisted for two reasons:
#  1. I have the entire HVSC and I don't want that to weight the randomization
#     in favor of SIDs.
#  2. All the SIDs I've encountered loop infinitely and I want my playlist to
#     stop after a predictable interval.
