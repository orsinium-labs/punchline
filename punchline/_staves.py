from __future__ import annotations
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from functools import cached_property
import math
from pathlib import Path
from typing import TextIO

import svgwrite
from ._music_box import MusicBox
from ._melody import Melody


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
    marker_offset: float = 6.
    marker_offset_top: float = 0.
    marker_offset_bottom: float = 0.
    margin: float = 20.
    font_size: float = 1.
    divisor: float = 67.
    page_width: float = 297.
    page_height: float = 210.

    @classmethod
    def init_parser(cls, parser: ArgumentParser) -> None:
        parser.add_argument('--output', type=Path, default=cls.output_path)
        parser.add_argument('--marker-offset', type=float, default=cls.marker_offset)
        parser.add_argument('--marker-offset-top', type=float, default=cls.marker_offset_top)
        parser.add_argument('--marker-offset-bottom', type=float, default=cls.marker_offset_bottom)
        parser.add_argument('--margin', type=float, default=cls.margin)
        parser.add_argument('--divisor', type=float, default=cls.divisor)
        parser.add_argument('--font-size', type=float, default=cls.font_size)
        parser.add_argument('--page-width', type=float, default=cls.page_width)
        parser.add_argument('--page-height', type=float, default=cls.page_height)

    @classmethod
    def from_args(cls, args: Namespace, *, melody: Melody) -> Staves:
        return cls(
            music_box=melody.music_box,
            melody=melody,
            output_path=args.output,
            marker_offset=args.marker_offset,
            marker_offset_top=args.marker_offset_top,
            marker_offset_bottom=args.marker_offset_bottom,
            margin=args.margin,
            divisor=args.divisor,
            font_size=args.font_size,
            page_width=args.page_width,
            page_height=args.page_height,
        )

    @cached_property
    def stave_width(self) -> float:
        return (len(self.music_box.note_data) - 1) * self.music_box.pitch + self.margin

    @cached_property
    def staves_per_page(self) -> int:
        return int(math.floor((self.page_height - self.margin) / self.stave_width))

    @cached_property
    def max_stave_length(self) -> float:
        return self.page_width - (self.margin * 2)

    @cached_property
    def no_staves_required(self) -> int:
        max_length = self.melody.max_time / self.divisor
        return int(math.ceil(max_length / self.max_stave_length))

    @cached_property
    def pages(self) -> int:
        return int(math.ceil(float(self.no_staves_required) / self.staves_per_page))

    def write(self) -> None:
        self.output_path.mkdir(exist_ok=True, parents=True)
        offset = 0
        for page in range(self.pages):
            offset = self._write_page(page=page, offset=offset)

    def write_stats(self, stream: TextIO) -> None:
        print(f"sounds: {len(self.melody.sounds)}", file=stream)
        print(f"notes: {len(self.melody.notes_use)}", file=stream)
        min_dist = self.melody.min_distance / self.divisor
        print(f"minimum note distance: {round(min_dist, 2)}", file=stream)
        print(f"transpose: {self.melody.best_transpose[0]}", file=stream)
        print(f"percentage hit: {round(self.melody.best_transpose[1] * 100)}%", file=stream)
        if self.melody.best_transpose[1] == 1:
            print("^ PERFECT!")
        zero_sounds = sum(sound.time == 0 for sound in self.melody.sounds)
        if zero_sounds > 2:
            percent = round(zero_sounds / self.melody.sounds_count * 100)
            print(f"sounds without time: {zero_sounds} ({percent}%)", file=stream)
        print(f"max length: {self.melody.max_time / self.divisor}", file=stream)
        print(f"max stave length: {self.max_stave_length}", file=stream)
        print(f"no staves: {self.no_staves_required}", file=stream)
        print(f"pages: {self.pages}", file=stream)

    def _write_page(self, page: int, offset: int) -> int:
        file_path = self.output_path / f"{page}.svg"
        dwg = svgwrite.Drawing(str(file_path), size=(mm(self.page_width), mm(self.page_height)))

        for stave in range(self.staves_per_page):
            offset = self._write_stave(dwg=dwg, page=page, stave=stave, offset=offset)
        dwg.save()
        return offset

    def _write_stave(self, dwg: svgwrite.Drawing, page: int, stave: int, offset: int) -> int:
        mark_top = self.marker_offset_top or self.marker_offset
        mark_btm = self.marker_offset_bottom or self.marker_offset
        offset_time = ((page * self.staves_per_page) + stave) * self.max_stave_length

        line_offset = (stave * (self.stave_width)) + self.margin
        cross(
            dwg,
            line_offset - mark_top,
            self.margin + self.max_stave_length,
        )
        cross(
            dwg,
            line_offset + self.stave_width - self.margin + mark_btm,
            self.margin + self.max_stave_length,
        )
        cross(dwg, line_offset - mark_top, self.margin)
        cross(dwg, line_offset + self.stave_width - self.margin + mark_btm, self.margin)
        text = dwg.text(
            "STAVE {} - {}".format((page * self.staves_per_page) + stave, self.output_path.name),
            insert=(mm(self.margin * 2), mm(line_offset + self.stave_width - self.margin + self.marker_offset)),
            fill="blue",
            font_size=mm(self.font_size),
        )
        dwg.add(text)
        for i, note_number in enumerate(self.music_box.note_data):
            line_x = (i * self.music_box.pitch) + line_offset
            line = dwg.line(
                (mm(self.margin), mm(line_x)),
                (mm(self.max_stave_length + self.margin), mm(line_x)),
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

        trans = self.melody.best_transpose[0]
        for sound in self.melody.sounds[offset:]:
            fill = "black"
            try:
                note_pos = self.music_box.note_data.index(sound.note + trans)
            except ValueError:
                # TODO: handle missed notes
                note_pos = 0
                fill = "red"
            sound_offset = (sound.time / self.divisor) - offset_time

            if sound_offset > self.max_stave_length:
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
