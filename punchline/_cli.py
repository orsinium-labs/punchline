from __future__ import annotations
from argparse import ArgumentParser
import sys
from typing import NoReturn, TextIO
from ._melody import Melody
from ._music_box import MusicBox
from ._staves import Staves


def main(argv: list[str], stream: TextIO) -> int:
    parser = ArgumentParser()
    Melody.init_parser(parser)
    Staves.init_parser(parser)
    MusicBox.init_parser(parser)
    args = parser.parse_args(argv)
    music_box = MusicBox.from_args(args)
    melody = Melody.from_args(args, music_box=music_box)
    staves = Staves.from_args(args, melody=melody)
    staves.write_stats(stream)
    staves.write()
    return 0


def entrypoint() -> NoReturn:
    sys.exit(main(sys.argv[1:], sys.stdout))
