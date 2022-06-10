from __future__ import annotations
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from collections import Counter
import math
from typing import TYPE_CHECKING

from mido import MidiFile, Message

if TYPE_CHECKING:
    from ._music_box import MusicBox


@dataclass(frozen=True)
class Note:
    note: int
    time: float


@dataclass
class Melody:
    path: Path
    music_box: MusicBox
    transpose_lower: int = -100
    transpose_upper: int = 100
    tracks: frozenset = frozenset(range(16))
    debug: bool = False

    @classmethod
    def init_parser(cls, parser: ArgumentParser) -> None:
        parser.add_argument('--input', type=Path, required=True)
        parser.add_argument('--transpose-lower', type=int, default=cls.transpose_lower)
        parser.add_argument('--transpose-upper', type=int, default=cls.transpose_upper)
        parser.add_argument('--tracks', nargs='*', type=int, default=[])

    @classmethod
    def from_args(cls, args: Namespace, *, music_box: MusicBox) -> Melody:
        return cls(
            path=args.input,
            transpose_lower=args.transpose_lower,
            transpose_upper=args.transpose_upper,
            tracks=frozenset(args.tracks) or cls.tracks,
            music_box=music_box,
        )

    @cached_property
    def notes(self) -> list[Note]:
        notes = []
        with MidiFile(str(self.path)) as midi_file:
            message: Message
            for i, track in enumerate(midi_file.tracks):
                if i not in self.tracks:
                    continue
                print(f'reading track #{i} "{track.name}"...')
                time = 0
                for message in track:
                    time += message.time
                    if message.is_meta:
                        continue
                    if message.type != "note_on":
                        continue
                    if message.velocity == 0:
                        continue
                    notes.append(Note(note=message.note, time=time))
        return sorted(notes, key=lambda note: note.time)

    @cached_property
    def notes_use(self) -> dict[int, int]:
        """How many times each note appears in the melody.
        """
        return dict(Counter(note.note for note in self.notes))

    @cached_property
    def sounds_count(self) -> int:
        """How many sounds in total there are in the melody.
        """
        return len(self.notes)

    def count_available_sounds(self, trans: int) -> int:
        """How many notes from the melody fit in the music box.
        """
        count = 0
        for note, freq in self.notes_use.items():
            if note + trans in self.music_box.note_data:
                count += freq
        return count

    @cached_property
    def max_time(self) -> float:
        return max(note.time for note in self.notes)

    @cached_property
    def best_transpose(self) -> tuple[int, float]:
        transpose = range(self.transpose_lower, self.transpose_upper)
        best_transpose: tuple[int, float]
        best_transpose = (0, 0)
        for trans in transpose:
            avail = self.count_available_sounds(trans)
            percen = avail / float(self.sounds_count)
            if percen == 1:
                return (trans, 1)

            if percen > best_transpose[1]:
                if self.debug:
                    unavail = {
                        self.music_box.get_note_name(note): freq
                        for note, freq in self.notes_use.items()
                        if note + trans not in self.music_box.note_data
                    }
                    print("Transposition Candidate Report")
                    print("Transposition: {}".format(trans))
                    print("Total Notes: {}".format(self.sounds_count))
                    print("Notes OK: {}".format(avail))
                    print("Distinct Notes Missing: {}".format(len(unavail)))
                    print("Total Notes Missing: {}".format(self.sounds_count - avail))
                    print("Unavailables: {}".format(unavail))
                    print("========================================")
                best_transpose = (trans, percen)
        return best_transpose

    @cached_property
    def min_distance(self) -> float:
        """Find the shortest time between 2 consequentive sounds.
        """
        min_distances: dict[int, Distance] = {}
        for note in self.notes:
            distance = min_distances.setdefault(note.note, Distance(note.time))
            diff = note.time - distance.time
            if math.isclose(diff, 0):
                continue
            distance.diff = min(distance.diff, diff)
            distance.time = note.time
        if not min_distances:
            return math.inf
        return min(d.diff for d in min_distances.values())


@dataclass
class Distance:
    time: float
    diff: float = math.inf
