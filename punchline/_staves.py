from __future__ import annotations
from dataclasses import dataclass
from functools import cached_property
import itertools
import math
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, TextIO

import svg
from ._music_box import MusicBox
from ._melody import Melody

if TYPE_CHECKING:
    from argparse import _ArgumentGroup, Namespace


mm = svg.mm


def cross(x: float, y: float) -> Iterator[svg.Element]:
    hs = 1
    yield svg.Line(
        x1=mm(x),
        y1=mm(y - hs),
        x2=mm(x),
        y2=mm(y + hs),
        stroke="green",
        stroke_width=mm(.1),
    )
    yield svg.Line(
        x1=mm(x - hs),
        y1=mm(y),
        x2=mm(x + hs),
        y2=mm(y),
        stroke="green",
        stroke_width=mm(.1),
    )


@dataclass
class Staves:
    music_box: MusicBox
    melody: Melody

    output_path: Path = Path('output')
    margin: float = 5.
    font_size: float = 1.
    speed: float = 67.
    page_width: float = 297.
    page_height: float = 210.
    diameter: float = 2.
    name: str = "melody"

    @classmethod
    def init_parser(cls, parser: _ArgumentGroup) -> None:
        parser.add_argument(
            '--output', type=Path, default=cls.output_path,
            help='the directory to save generated SVG pages',
        )
        parser.add_argument(
            '--margin', type=float, default=cls.margin,
            help='distance (in mm) to keep between stripes and page borders',
        )
        parser.add_argument(
            '--speed', type=float, default=cls.speed,
            help='how densly the holes should be packed (ticks/mm)',
        )
        parser.add_argument(
            '--font-size', type=float, default=cls.font_size,
            help='size of all text on the page (in mm)',
        )
        parser.add_argument(
            '--page-width', type=float, default=cls.page_width,
            help='horizontal (longer) page size (in mm). A4 by default.',
        )
        parser.add_argument(
            '--page-height', type=float, default=cls.page_height,
            help='vertical (shorter) page size (in mm). A4 by default.',
        )
        parser.add_argument(
            '--diameter', type=float, default=cls.diameter,
            help='diameter (in mm) of circles.',
        )

    @classmethod
    def from_args(cls, args: Namespace, *, melody: Melody) -> Staves:
        return cls(
            music_box=melody.music_box,
            melody=melody,
            output_path=args.output,
            margin=args.margin,
            speed=args.speed,
            font_size=args.font_size,
            page_width=args.page_width,
            page_height=args.page_height,
            diameter=args.diameter,
            name=args.input.stem,
        )

    @cached_property
    def stave_width(self) -> float:
        """How wide each stave (stripe) is (in mm) including paddings.
        """
        return self.music_box.width + self.music_box.padding_bottom + self.music_box.padding_top

    @cached_property
    def staves_per_page(self) -> int:
        """How many staves (stripes) can fit on a single page.
        """
        return math.floor((self.page_height - self.margin * 2) / self.stave_width)

    @cached_property
    def stave_length(self) -> float:
        """How long each stave (stripe) is (in mm).
        """
        return self.page_width - self.margin * 2

    @cached_property
    def total_length(self) -> float:
        """The summary length of all stripes to be generated in mm.
        """
        return self.melody.max_time / self.speed

    @cached_property
    def staves_count(self) -> int:
        """How many staves (stripes) the are to generate.
        """
        return math.ceil(self.total_length / self.stave_length)

    @cached_property
    def pages_count(self) -> int:
        """How many pages the are to generate.
        """
        return math.ceil(self.staves_count / self.staves_per_page)

    def write(self) -> None:
        """Generate SVG pages and save them into output_path directory.
        """
        self.output_path.mkdir(exist_ok=True, parents=True)
        offset = 0
        for page in range(self.pages_count):
            offset = self._write_page(page=page, offset=offset)

    def write_stats(self, stream: TextIO) -> None:
        """Write human-readable stats into the stream.
        """
        print(f"sounds: {len(self.melody.sounds)}", file=stream)
        print(f"notes: {len(self.melody.notes_use)}", file=stream)
        print(f"duration: {round(self.melody.max_time)} ticks", file=stream)
        min_dist = self.melody.min_distance / self.speed
        print(f"minimum note distance: {round(min_dist, 2)} mm", file=stream)
        print(f"transpose: {self.melody.best_transpose.shift}", file=stream)
        print(f"sounds fit: {round(self.melody.best_transpose.ratio * 100)}%", file=stream)
        if self.melody.best_transpose.ratio == 1:
            print("^ PERFECT!")
        print(f"total length: {round(self.total_length)} mm", file=stream)
        print(f"stave length: {self.stave_length} mm", file=stream)
        print(f"staves: {self.staves_count}", file=stream)
        print(f"pages: {self.pages_count}", file=stream)

    def _write_page(self, page: int, offset: int) -> int:
        canvas = svg.SVG(
            width=mm(self.page_width),
            height=mm(self.page_height),
            xmlns="http://www.w3.org/2000/svg",
        )
        for stave in range(self.staves_per_page):
            offset = self._write_stave(canvas, page=page, stave=stave, offset=offset)
            # stop drawing staves when the last sound is written
            if offset >= self.melody.sounds_count:
                break
        file_path = self.output_path / f"{page}.svg"
        file_path.write_text(str(canvas))
        return offset

    def _write_stave(self, dwg: svg.SVG, page: int, stave: int, offset: int) -> int:
        line_offset = stave * self.stave_width + self.margin * 2
        if dwg.elements is None:
            dwg.elements = []

        # draw crosses at the coners of stave
        padding_top = self.music_box.padding_top
        x_left = self.margin
        x_right = self.margin + self.stave_length
        y_top = line_offset - padding_top
        y_bottom = y_top + self.stave_width
        if stave == 0:
            dwg.elements.extend(itertools.chain(
                cross(x=x_left, y=y_top),
                cross(x=x_right, y=y_top),
            ))
        dwg.elements.extend(itertools.chain(
            cross(x=x_left, y=y_bottom),
            cross(x=x_right, y=y_bottom),
        ))

        # draw caption (melody name and stave number)
        stave_crossnumber = page * self.staves_per_page + stave + 1
        text = svg.Text(
            text=f"{self.name} #{stave_crossnumber}",
            x=mm(self.margin * 2),
            y=mm(y_bottom),
            fill="blue",
            font_size=mm(self.font_size),
        )
        dwg.elements.append(text)

        # draw lines
        for i, note in enumerate(self.music_box.notes):
            line_x = i * self.music_box.pitch + line_offset
            line = svg.Line(
                x1=mm(self.margin),
                y1=mm(line_x),
                x2=mm(self.stave_length + self.margin),
                y2=mm(line_x),
                stroke="grey",
                stroke_width=mm(.1),
            )
            dwg.elements.append(line)
            text = svg.Text(
                text=note.name,
                x=mm(-2 + self.margin),
                y=mm(line_x + self.font_size / 2),
                fill="orange",
                font_size=mm(self.font_size),
            )
            dwg.elements.append(text)

        # draw cut circles
        offset_time = (page * self.staves_per_page + stave) * self.stave_length
        trans = self.melody.best_transpose.shift
        latest_notes: dict[int, float] = dict()
        for sound in self.melody.sounds[offset:]:
            sound_offset = sound.time / self.speed - offset_time
            if sound_offset > self.stave_length:
                break

            # place the sound, fill black for exact placement and fill red for transposed
            fill: str | None = "black"
            note_number = sound.note + trans
            if self.music_box.contains_note(note_number):
                note_pos = self.music_box.get_note_pos(note_number)
            else:
                note_pos = self.music_box.guess_note_pos(note_number)
                fill = "red"

            # outline instead of fill if note is too close to the previous one
            stroke = None
            stroke_width = None
            prev_offset = latest_notes.get(note_pos)
            if prev_offset is not None:
                distance = sound_offset - prev_offset
                if distance < self.music_box.min_distance:
                    stroke = fill
                    stroke_width = mm(.1)
                    fill = "white"
            if stroke is None:
                latest_notes[note_pos] = sound_offset

            circle = svg.Circle(
                cx=mm(sound_offset + self.margin),
                cy=mm(note_pos * self.music_box.pitch + line_offset),
                r=mm(self.diameter / 2),
                fill=fill,
                stroke=stroke,
                stroke_width=stroke_width,
            )
            dwg.elements.append(circle)
            offset += 1
        return offset
