from __future__ import annotations
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass

# https://www.inspiredacoustics.com/en/MIDI_note_numbers_and_center_frequencies
A0 = 21
NAMES = ('A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#')


@dataclass
class MusicBox:
    note_data: tuple[int, ...]
    pitch: float = 2.0

    @classmethod
    def init_parser(cls, parser: ArgumentParser) -> None:
        parser.add_argument(
            '--pitch', type=int, default=cls.pitch,
            help='distance (in mm) between 2 notes on the music box',
        )

    @classmethod
    def from_args(cls, args: Namespace) -> MusicBox:
        return cls(
            note_data=BOX_35,
            pitch=args.pitch,
        )

    def get_note_name(self, val: int) -> str:
        mod = (val - A0) % 12
        letter = NAMES[mod]
        octave = int(val / 12) - 2
        return f"{letter}{octave}"


BOX_35 = (
    60, 62, 67, 69,
    71, 72, 74, 76, 77, 78, 79,
    80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
    90, 91, 92, 93, 94, 95, 96, 98, 100,
)
