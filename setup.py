#!/usr/bin/env python
"""@todo:
 - Identify minimum dependency versions properly.
 - Figure out how to mark optional packages as optional.
"""
from setuptools import setup, find_packages
from lap.version import __version__

if __name__ == '__main__':
    setup(
        name='lap',
        version=__version__,
        description='Console frontend for building playlists',
        long_description="""
            A simple, multi-mode tool for selecting media files and playing
            or enqueueing them via MPRIS, calling a command, or shell piping.
            """,
        author="Stephan Sokolow",
        url="https://github.com/ssokolow/lap",
        license="https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Environment :: Console",
            "Environment :: Console :: Curses",
            "Intended Audience :: End Users/Desktop",
            "License :: OSI Approved :: GNU General Public License v2"
                "or later (GPLv2+)",
            "Natural Language :: English",
            "Operating System :: POSIX",
            "Programming Language :: Python :: 2",
            "Topic :: Multimedia :: Sound/Audio",
            "Topic :: Utilities",
        ],

        install_requires=['urwid'],
        packages=find_packages(),

        # Causes a ZipImport error the second time you run `setup.py install`
        # on the same system
        zip_safe=False,

        entry_points={
            'console_scripts': [
                'ap = lap.__main__:main',
                'aq = lap.__main__:main',
                'lap = lap.__main__:main',
                'laq = lap.__main__:main',
                'rap = lap.__main__:main',
                'raq = lap.__main__:main',
            ],
        },

        #test_suite='run_test.get_tests',
    )

# vim: set sw=4 sts=4 :
