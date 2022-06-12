from __future__ import annotations
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import _ArgumentGroup, Namespace

# https://www.inspiredacoustics.com/en/MIDI_note_numbers_and_center_frequencies
A0 = 21
NAMES = ('A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#')


@dataclass
class Note:
    number: int  # the value used in MIDI to represent the note

    @classmethod
    def from_name(cls, name: str) -> Note:
        """Get note from its full name (like `C#4`)
        """
        octave = int(name[-1])
        mod = NAMES.index(name[:-1]) + A0
        number = octave * 12 + mod
        note = Note(number)
        assert note.name == name, f'{note.name} != {name}'
        return note

    @cached_property
    def is_sharp(self) -> bool:
        """Check if the note is a semitone.
        """
        return '#' in self.letter

    @cached_property
    def octave(self) -> int:
        return int(self.number / 12) - 2

    @cached_property
    def letter(self) -> str:
        """The letter (including # sign if needed) representing the note.
        """
        mod = (self.number - A0) % 12
        return NAMES[mod]

    @cached_property
    def name(self) -> str:
        return f"{self.letter}{self.octave}"


@dataclass
class MusicBox:
    sharps: bool = False
    first_note: str = 'C4'
    notes_count: int = 35
    pitch: float = 2.0
    padding_top: float = 6.
    padding_bottom: float = 6.

    @classmethod
    def init_parser(cls, parser: _ArgumentGroup) -> None:
        parser.add_argument(
            '--sharps', action='store_true', default=False,
            help='set this flag if the music box supports sharp notes (semitones)',
        )
        parser.add_argument(
            '--first-note', default=cls.first_note,
            help='the most low-frequency note on the music box',
        )
        parser.add_argument(
            '--notes-count', type=int, default=cls.notes_count,
            help='how many notes in total there are on the music box',
        )
        parser.add_argument(
            '--pitch', type=float, default=cls.pitch,
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
            sharps=args.sharps,
            first_note=args.first_note,
            notes_count=args.notes_count,
            pitch=args.pitch,
            padding_top=args.padding_top,
            padding_bottom=args.padding_bottom,
        )

    @property
    def width(self) -> float:
        """The distance between edge notes of the music box.
        """
        return (self.notes_count - 1) * self.pitch

    def contains_note(self, note: int) -> bool:
        """Check if the note is present on the music box.
        """
        return note in self._note_data

    def get_note_pos(self, note: int) -> int:
        return self._note_data.index(note)

    @cached_property
    def _note_data(self) -> tuple[int, ...]:
        """Sequence of all notes names that are presented on the music box.
        """
        return tuple(note.number for note in self.notes)

    @cached_property
    def notes(self) -> tuple[Note, ...]:
        """Sequence of all notes that are presented on the music box.
        """
        notes: list[Note] = []
        note_number = Note.from_name(self.first_note).number - 1
        while len(notes) < self.notes_count:
            note_number += 1
            note = Note(note_number)
            if not self.sharps and note.is_sharp:
                continue
            notes.append(note)
        return tuple(notes)
