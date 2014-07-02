#Locate And Play

Locate And Play is a multipurpose Python script for adding
entries to your playlist in Audacious Media Player (and possibly other
MPRIS-based players) or a command specified via `--exec`.

![urwid screenshot](screenshots/lap_urwid.png)

The name originally stood for "Locate, Audacious, Play" (a derivation of
"Audacious Play" because `ap` was the first subcommand to be written) and it
was originally announced
[on my blog](http://blog.ssokolow.com/archives/2013/05/24/a-little-tool-for-command-line-playlist-building/)
as part of my [roaming profile](https://github.com/ssokolow/profile).

### Usage

In the vein of classic UNIX utilities like `grep`, `fgrep`, and `egrep`, this
script will select a different set of default `--option` flags depending on
what name it's called under.

<dl>
<dt>aq &lt;path&gt; [...]</dt>
<dd>Add the given paths to the playlist.</dd>
<dt>ap &lt;path&gt; [...]</dt>
<dd>Like <code>aq</code> but start the first one playing too.</dd>
<dt>laq &lt;substring&gt; [...]</dt>
<dd>Like <code>aq</code> but use <code>locate -i</code> to search for the first argument, filter for known media types and filter for the following arguments, then display a chooser.</dd>
<dt>lap &lt;substring&gt; [...]</dt>
<dd>Like <code>laq</code> but start the first one playing too.</dd>
<dt>raq [path] [...]</dt>
<dd>Randomly select <code>-n NUM</code> songs (default: 10) from the paths provided (default: <code>XDG_MUSIC_DIR</code>) and add them to the playlist.</dd>
<dt>rap [path] [...]</dt>
<dd>Like <code>raq</code> but start the first one playing too.</dd>
</dl>

When displaying a chooser, there are two possible forms it can take: The
urwid-based one depicted above or a simple, fallback chooser with no
external dependencies.

### Requirements

* Python 2.x (Support for 3.x will come later)
* [Audacious Media Player](http://audacious-media-player.org/) (Support for other MPRIS-compliant players planned)
* [locate](https://en.wikipedia.org/wiki/Locate_%28Unix%29) (Only required for
  variants beginning with `l`)
* [urwid](http://urwid.org/) (only required if you want the pretty chooser)
