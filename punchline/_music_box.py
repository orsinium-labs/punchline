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
        """The name of the note, including letter, sharp, and octave (A#1)
        """
        return f"{self.letter}{self.octave}"


@dataclass
class MusicBox:
    sharps: bool = False
    first_note: str = 'C4'
    notes_count: int = 15
    reverse: bool = False
    pitch: float = 2.0
    padding_top: float = 6.
    padding_bottom: float = 7.
    min_distance: float = 8.
    prefer_up: bool = False

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
            '--reverse', action='store_true', default=False,
            help='set this flag if the first note should be at the top',
        )
        parser.add_argument(
            '--pitch', type=float, default=cls.pitch,
            help='distance (in mm) between 2 notes on the music box',
        )
        parser.add_argument(
            '--padding-top', type=float, default=cls.padding_top,
            help='the padding from the stripe top to the first line (in mm)',
        )
        parser.add_argument(
            '--padding-bottom', type=float, default=cls.padding_bottom,
            help='the padding from the stripe top to the first line (in mm)',
        )
        parser.add_argument(
            '--min-distance', type=float, default=cls.min_distance,
            help='if 2 notes are closer than this value (in mm), the second one is silent',
        )
        parser.add_argument(
            '--prefer-up', action='store_true',
            help='prefer shifting sharp notes half-tone up rather than down (when unsupported)',
        )

    @classmethod
    def from_args(cls, args: Namespace) -> MusicBox:
        return cls(
            sharps=args.sharps,
            first_note=args.first_note,
            notes_count=args.notes_count,
            reverse=args.reverse,
            pitch=args.pitch,
            padding_top=args.padding_top,
            padding_bottom=args.padding_bottom,
            min_distance=args.min_distance,
            prefer_up=args.prefer_up,
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
        """Get the line number on which the note should be put.
        """
        return self._note_data.index(note)

    def guess_note_pos(self, note: int) -> int:
        """For the note that isn't on the music box, try to put it on a good enough place.
        """
        # try to transposition note with changing octave but preserving the letter.
        is_sharp = Note(note).is_sharp
        transpositions = (0, -12, 12, -24, 24, -36, 36)
        for trans in transpositions:
            shifted = note + trans
            guesses = [shifted]
            # if the note is sharp but the music box doesn't support sharps,
            # try to shift it on semitone below or above.
            if is_sharp and not self.sharps:
                if self.prefer_up:
                    guesses.extend([shifted + 1, shifted - 1])
                else:
                    guesses.extend([shifted - 1, shifted + 1])
            for guess in guesses:
                if self.contains_note(guess):
                    return self.get_note_pos(guess)

        above = note < min(self._note_data)
        if self.reverse:
            above = not above
        if above:
            return self.notes_count - 1
        return 0

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
        if not self.reverse:  # sic! we reverse if reverse is False.
            notes.reverse()
        return tuple(notes)
