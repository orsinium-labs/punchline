from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from argparse import _ArgumentGroup, Namespace

# https://www.inspiredacoustics.com/en/MIDI_note_numbers_and_center_frequencies
A0 = 21
NAMES = ('A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#')


@dataclass
class MusicBox:
    note_data: tuple[int, ...]
    pitch: float = 2.0
    padding_top: float = 6.
    padding_bottom: float = 6.

    @classmethod
    def init_parser(cls, parser: _ArgumentGroup) -> None:
        parser.add_argument(
            '--pitch', type=int, default=cls.pitch,
            help='distance (in mm) between 2 notes on the music box',
        )
        parser.add_argument(
            '--padding-top', type=float, default=cls.padding_top,
            help='the padding from the stripe top to the first line (in mm).',
        )
        parser.add_argument(
            '--padding-bottom', type=float, default=cls.padding_bottom,
            help='the padding from the stripe top to the first line (in mm).',
        )

    @classmethod
    def from_args(cls, args: Namespace) -> MusicBox:
        return cls(
            note_data=BOX_35,
            pitch=args.pitch,
            padding_top=args.padding_top,
            padding_bottom=args.padding_bottom,
        )

    @property
    def note_names(self) -> Iterator[str]:
        """Sequence of all notes names that are presented on the music box.
        """
        for note_number in self.note_data:
            yield self._get_note_name(note_number)

    def _get_note_name(self, val: int) -> str:
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
