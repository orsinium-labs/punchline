from __future__ import annotations
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass


@dataclass
class MusicBox:
    note_data: tuple[int, ...]
    pitch: float = 2.0
    reverse: bool = False

    @classmethod
    def init_parser(cls, parser: ArgumentParser) -> None:
        parser.add_argument('--pitch', type=int, default=cls.pitch)

    @classmethod
    def from_args(cls, args: Namespace) -> MusicBox:
        return cls(
            note_data=BOX_35,
            pitch=args.pitch,
        )

    def get_note_name(self, val: float) -> str:
        mod = val % 12
        octave = (val / 12) - 2
        letter = f"[{mod}]"
        return f"{letter}{octave}"


BOX_35 = (
    60, 62, 67, 69,
    71, 72, 74, 76, 77, 78, 79,
    80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
    90, 91, 92, 93, 94, 95, 96, 98, 100,
)
