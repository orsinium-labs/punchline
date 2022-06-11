from __future__ import annotations
from dataclasses import dataclass
from functools import cached_property
import math
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

import svgwrite
from ._music_box import MusicBox
from ._melody import Melody

if TYPE_CHECKING:
    from argparse import _ArgumentGroup, Namespace


def mm(val: float) -> str:
    return f"{val}mm"


def cross(dwg: svgwrite.Drawing, x: float, y: float) -> None:
    hs = 2.5
    dwg.add(
        dwg.line(
            (mm(y - hs), mm(x)),
            (mm(y + hs), mm(x)),
            stroke=svgwrite.rgb(0, 0, 0, "%"),
            stroke_width=".1mm",
        ),
    )
    dwg.add(
        dwg.line(
            (mm(y), mm(x - hs)),
            (mm(y), mm(x + hs)),
            stroke=svgwrite.rgb(0, 0, 0, "%"),
            stroke_width=".1mm",
        ),
    )


@dataclass
class Staves:
    music_box: MusicBox
    melody: Melody

    output_path: Path = Path('output')
    margin: float = 20.
    font_size: float = 1.
    divisor: float = 67.
    page_width: float = 297.
    page_height: float = 210.

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
        parser.add_argument('--divisor', type=float, default=cls.divisor)
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

    @classmethod
    def from_args(cls, args: Namespace, *, melody: Melody) -> Staves:
        return cls(
            music_box=melody.music_box,
            melody=melody,
            output_path=args.output,
            margin=args.margin,
            divisor=args.divisor,
            font_size=args.font_size,
            page_width=args.page_width,
            page_height=args.page_height,
        )

    @cached_property
    def stave_width(self) -> float:
        """How wide each stave (stripe) is.
        """
        return (len(self.music_box.note_data) - 1) * self.music_box.pitch + self.margin

    @cached_property
    def staves_per_page(self) -> int:
        """How many staves (stripes) can fit on a single page.
        """
        return math.floor((self.page_height - self.margin) / self.stave_width)

    @cached_property
    def stave_length(self) -> float:
        """How long is each stave (stripe).
        """
        return self.page_width - (self.margin * 2)

    @cached_property
    def total_length(self) -> float:
        """The summary length of all stripes to be generated.
        """
        return self.melody.max_time / self.divisor

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
        print(f"sounds: {len(self.melody.sounds)}", file=stream)
        print(f"notes: {len(self.melody.notes_use)}", file=stream)
        min_dist = self.melody.min_distance / self.divisor
        print(f"minimum note distance: {round(min_dist, 2)}", file=stream)
        print(f"transpose: {self.melody.best_transpose.shift}", file=stream)
        print(f"percentage hit: {round(self.melody.best_transpose.ratio * 100)}%", file=stream)
        if self.melody.best_transpose.ratio == 1:
            print("^ PERFECT!")
        zero_sounds = sum(sound.time == 0 for sound in self.melody.sounds)
        if zero_sounds > 2:
            percent = round(zero_sounds / self.melody.sounds_count * 100)
            print(f"sounds without time: {zero_sounds} ({percent}%)", file=stream)
        print(f"total length: {round(self.total_length)} mm", file=stream)
        print(f"max stave length: {self.stave_length} mm", file=stream)
        print(f"staves: {self.staves_count}", file=stream)
        print(f"pages: {self.pages_count}", file=stream)

    def _write_page(self, page: int, offset: int) -> int:
        file_path = self.output_path / f"{page}.svg"
        dwg = svgwrite.Drawing(str(file_path), size=(mm(self.page_width), mm(self.page_height)))

        for stave in range(self.staves_per_page):
            offset = self._write_stave(dwg=dwg, page=page, stave=stave, offset=offset)
        dwg.save()
        return offset

    def _write_stave(self, dwg: svgwrite.Drawing, page: int, stave: int, offset: int) -> int:
        offset_time = ((page * self.staves_per_page) + stave) * self.stave_length
        line_offset = (stave * (self.stave_width)) + self.margin
        padding_top = self.music_box.padding_top
        padding_bottom = self.music_box.padding_bottom
        cross(
            dwg,
            line_offset - padding_top,
            self.margin + self.stave_length,
        )
        cross(
            dwg,
            line_offset + self.stave_width - self.margin + padding_bottom,
            self.margin + self.stave_length,
        )
        cross(dwg, line_offset - padding_top, self.margin)
        cross(dwg, line_offset + self.stave_width - self.margin + padding_bottom, self.margin)
        stave_crossnumber = (page * self.staves_per_page) + stave
        text = dwg.text(
            f"STAVE {stave_crossnumber} - {self.output_path.name}",
            insert=(mm(self.margin * 2), mm(line_offset + self.stave_width - self.margin + padding_bottom)),
            fill="blue",
            font_size=mm(self.font_size),
        )
        dwg.add(text)
        for i, note_number in enumerate(self.music_box.note_data):
            line_x = (i * self.music_box.pitch) + line_offset
            line = dwg.line(
                (mm(self.margin), mm(line_x)),
                (mm(self.stave_length + self.margin), mm(line_x)),
                stroke=svgwrite.rgb(0, 0, 0, "%"),
                stroke_width=".1mm",
            )
            dwg.add(line)
            text = dwg.text(
                self.music_box.get_note_name(note_number),
                insert=(mm(-2 + self.margin), mm(line_x + self.font_size / 2)),
                fill="red",
                font_size=mm(self.font_size),
            )
            dwg.add(text)

        trans = self.melody.best_transpose.shift
        for sound in self.melody.sounds[offset:]:
            fill = "black"
            try:
                note_pos = self.music_box.note_data.index(sound.note + trans)
            except ValueError:
                # TODO: handle missed notes
                note_pos = 0
                fill = "red"
            sound_offset = (sound.time / self.divisor) - offset_time

            if sound_offset > self.stave_length:
                break
            circle = dwg.circle(
                (
                    mm(sound_offset + self.margin),
                    mm((note_pos * self.music_box.pitch) + line_offset),
                ),
                "1mm",
                fill=fill,
            )
            dwg.add(circle)
            offset += 1
        return offset
