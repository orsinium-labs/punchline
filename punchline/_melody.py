from __future__ import annotations
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from collections import Counter
import math
from typing import TYPE_CHECKING, Iterable

from mido import MidiFile, Message

if TYPE_CHECKING:
    from argparse import _ArgumentGroup, Namespace
    from ._music_box import MusicBox


@dataclass
class Sound:
    note: int
    time: int
    track: int


@dataclass(frozen=True)
class Transposition:
    shift: int
    ratio: float


@dataclass
class Distance:
    time: int
    diff: float = math.inf


@dataclass
class Melody:
    path: Path
    music_box: MusicBox
    transpose_lower: int = -100
    transpose_upper: int = 100
    max_pause: int = 2000
    start_pause: int = 200
    cut_pause: int = 50_000
    transpose: bool = True
    tracks: frozenset = frozenset(range(40))

    @classmethod
    def init_parser(cls, parser: _ArgumentGroup) -> None:
        parser.add_argument(
            '--input', type=Path, required=True,
            help='path to the input MIDI (*.mid) file',
        )
        parser.add_argument(
            '--transpose-lower', type=int, default=cls.transpose_lower,
            help='the lowest transposition to try',
        )
        parser.add_argument(
            '--transpose-upper', type=int, default=cls.transpose_upper,
            help='the highest transposition to try',
        )
        parser.add_argument(
            '--no-transpose', action='store_true',
            help='do only octave transposition (in steps of 12 notes)',
        )
        parser.add_argument(
            '--tracks', nargs='*', type=int, default=[],
            help='numbers of sound tracks to include',
        )
        parser.add_argument(
            '--max-pause', type=int, default=cls.max_pause,
            help='maximum pause (in ticks) between two consequentive sounds',
        )
        parser.add_argument(
            '--start-pause', type=int, default=cls.start_pause,
            help='pause (in ticks) at the beginning of the first stripe',
        )
        parser.add_argument(
            '--cut-pause', type=int, default=cls.cut_pause,
            help='cut the song if pause is longer than this value (in ticks)',
        )

    @classmethod
    def from_args(cls, args: Namespace, *, music_box: MusicBox) -> Melody:
        return cls(
            path=args.input,
            transpose_lower=args.transpose_lower,
            transpose_upper=args.transpose_upper,
            max_pause=args.max_pause,
            start_pause=args.start_pause,
            cut_pause=args.cut_pause,
            transpose=not args.no_transpose,
            tracks=frozenset(args.tracks) or cls.tracks,
            music_box=music_box,
        )

    @cached_property
    def sounds(self) -> list[Sound]:
        sounds: list[Sound] = []
        with MidiFile(str(self.path)) as midi_file:
            message: Message
            for i, track in enumerate(midi_file.tracks):
                if i not in self.tracks:
                    continue
                time = 0
                prev_time = 0
                sounds_before = len(sounds)
                for message in track:
                    time += message.time
                    if message.is_meta:
                        continue
                    if message.type != "note_on":
                        continue
                    if message.velocity == 0:
                        continue
                    # if the pause too long, make it shorter
                    diff = time - prev_time
                    if sounds and diff > self.cut_pause:
                        break
                    time = prev_time + min(self.max_pause, diff)
                    prev_time = time
                    sound = Sound(note=message.note, time=time, track=i)
                    sounds.append(sound)
                name = f'#{i} "{track.name.strip()}"'
                print(f'  included {len(sounds) - sounds_before} sounds from track {name}')

        # set fixed silence at the beginning
        if sounds:
            shift = self.start_pause - min(sound.time for sound in sounds)
            for sound in sounds:
                sound.time += shift

        sounds.sort(key=lambda sound: sound.time)
        return sounds

    @cached_property
    def notes_use(self) -> dict[int, int]:
        """How many times each note appears in the melody.
        """
        return dict(Counter(sounds.note for sounds in self.sounds))

    @cached_property
    def sounds_count(self) -> int:
        """How many sounds in total there are in the melody.
        """
        return len(self.sounds)

    def count_available_sounds(self, trans: int) -> int:
        """How many notes from the melody fit in the music box.
        """
        count = 0
        for note, freq in self.notes_use.items():
            if self.music_box.contains_note(note + trans):
                count += freq
        return count

    @cached_property
    def max_time(self) -> int:
        """The tick when the last note plays.
        """
        if not self.sounds:
            return 0
        return max(sounds.time for sounds in self.sounds)

    @cached_property
    def best_transpose(self) -> Transposition:
        """Transposition that fits most of the notes.
        """
        lower_octave = int(self.transpose_lower / 12) * 12
        best_transpose = self._get_best_transpose(
            range(lower_octave, self.transpose_upper, 12),
        )
        # Better to transpose with preserving most of the notes.
        # If full octave transposition doesn't fit just a bit, roll with it.
        if best_transpose.ratio >= .90:
            return best_transpose
        if not self.transpose:
            return best_transpose
        return self._get_best_transpose(
            range(self.transpose_lower, self.transpose_upper),
        )

    def _get_best_transpose(self, seq: Iterable[int]) -> Transposition:
        """Try all transpositions from the sequence and pick the best one.
        """
        if not self.sounds:
            return Transposition(0, 1)
        best_transpose: Transposition = Transposition(0, 0)
        for shift in seq:
            avail = self.count_available_sounds(shift)
            ratio = avail / float(self.sounds_count)
            if ratio == 1:
                return Transposition(shift, 1)
            if ratio > best_transpose.ratio:
                best_transpose = Transposition(shift, ratio)
        return best_transpose

    @cached_property
    def min_distance(self) -> float:
        """The shortest time between 2 consequentive sounds (in ticks).
        """
        min_distances: dict[int, Distance] = {}
        for sound in self.sounds:
            distance = min_distances.setdefault(sound.note, Distance(sound.time))
            diff = sound.time - distance.time
            if math.isclose(diff, 0):
                continue
            distance.diff = min(distance.diff, diff)
            distance.time = sound.time
        if not min_distances:
            return math.inf
        return min(d.diff for d in min_distances.values())
