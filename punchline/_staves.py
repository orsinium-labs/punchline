from __future__ import annotations
from dataclasses import dataclass
from functools import cached_property, lru_cache
import math
from pathlib import Path
import re
from typing import TYPE_CHECKING, Iterator, TextIO

import svg
from ._music_box import MusicBox
from ._melody import Melody

if TYPE_CHECKING:
    from argparse import _ArgumentGroup, Namespace
    from HersheyFonts import HersheyFonts


mm = svg.mm


def camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case.

    We do that because the most popular midi download site uses CamelCase for file names.

    Source:
        https://stackoverflow.com/a/1176023/8704691
    """
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    name = name.lower().replace('_', ' ')
    return name


@lru_cache(maxsize=4)
def get_font(size: float) -> HersheyFonts:
    """Load hershey font that can be used to render text as a set of lines.

    https://github.com/apshu/HersheyFonts
    """
    from HersheyFonts import HersheyFonts  # pip3 install hershey-fonts
    font = HersheyFonts()
    font.load_default_font("rowmans")
    font.normalize_rendering(size)
    return font


@dataclass
class Staves:
    music_box: MusicBox
    melody: Melody

    output_path: Path = Path('output')
    margin: float = 5.
    font_size_notes: float = 2.
    font_size_captions: float = 4.
    speed: float = 67.
    page_width: float = 297.
    page_height: float = 210.
    start_width: float = 3.
    diameter: float = 2.5
    name: str = "melody"

    write_borders: bool = True
    write_notes: bool = True
    write_lines: bool = True
    write_captions: bool = True
    hershey: bool = False

    @classmethod
    def init_parser(cls, parser: _ArgumentGroup) -> None:
        parser.add_argument(
            '--output', type=Path, default=cls.output_path,
            help='the directory to save generated SVG pages',
        )
        parser.add_argument(
            '--name', help='melody name to write on the first stave',
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
            '--font-size-notes', type=float, default=cls.font_size_notes,
            help='size of note names on the left from staves (in mm)',
        )
        parser.add_argument(
            '--font-size-captions', type=float, default=cls.font_size_captions,
            help='size of captions (stave number and melody name) on staves (in mm)',
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
            '--start-width', type=float, default=cls.start_width,
            help='width of the triangle start of the first stave.',
        )
        parser.add_argument(
            '--diameter', type=float, default=cls.diameter,
            help='diameter (in mm) of circles.',
        )
        parser.add_argument(
            '--no-notes', action='store_true',
            help='do not write note names.',
        )
        parser.add_argument(
            '--no-lines', action='store_true',
            help='do not draw horizontal lines.',
        )
        parser.add_argument(
            '--no-captions', action='store_true',
            help='do not write caption with song name and stave number.',
        )
        parser.add_argument(
            '--no-borders', action='store_true',
            help='do not write borders of the stave.',
        )
        parser.add_argument(
            '--hershey', action='store_true',
            help='use hershey font for text to make it laser-cutter friendly.',
        )

    @classmethod
    def from_args(cls, args: Namespace, *, melody: Melody) -> Staves:
        return cls(
            music_box=melody.music_box,
            melody=melody,
            output_path=args.output,
            margin=args.margin,
            speed=args.speed,
            font_size_notes=args.font_size_notes,
            font_size_captions=args.font_size_captions,
            page_width=args.page_width,
            page_height=args.page_height,
            start_width=args.start_width,
            diameter=args.diameter,
            name=args.name or camel_to_snake(args.input.stem),
            write_notes=not args.no_notes,
            write_lines=not args.no_lines,
            write_captions=not args.no_captions,
            write_borders=not args.no_borders,
            hershey=args.hershey,
        )

    @cached_property
    def stave_width(self) -> float:
        """How wide (vertically) each stave (stripe) is (in mm) including paddings.
        """
        return self.music_box.width + self.music_box.padding_bottom + self.music_box.padding_top

    @cached_property
    def staves_per_page(self) -> int:
        """How many staves (stripes) can fit on a single page.
        """
        assert self.page_height > 0
        assert self.stave_width > 0
        assert self.stave_width < self.page_height
        return math.floor((self.page_height - self.margin * 2) / self.stave_width)

    @cached_property
    def stave_length(self) -> float:
        """How long each stave (stripe) is (in mm).
        """
        assert self.margin >= 0
        return self.page_width - self.margin * 2

    @cached_property
    def total_length(self) -> float:
        """The summary length of all stripes to be generated in mm.
        """
        assert self.melody.max_time >= 0
        assert self.speed > 0
        assert self.start_width >= 0
        return self.melody.max_time / self.speed + self.start_width

    @cached_property
    def staves_count(self) -> int:
        """How many staves (stripes) the are to generate.
        """
        assert self.total_length >= 0
        assert self.stave_length > 0
        return math.ceil(self.total_length / self.stave_length)

    @cached_property
    def pages_count(self) -> int:
        """How many pages the are to generate.
        """
        assert self.staves_count >= 0
        assert self.staves_per_page >= 1
        return math.ceil(self.staves_count / self.staves_per_page)

    @cached_property
    def last_stave_length(self) -> float:
        return self.total_length % self.stave_length

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
        file_name = f"{page}.svg"
        if self.pages_count == 1:
            name = self.name.replace(' ', '-')
            file_name = f"{name}.svg"
        file_path = self.output_path / file_name
        file_path.write_text(str(canvas))
        return offset

    def _write_stave(self, dwg: svg.SVG, page: int, stave: int, offset: int) -> int:
        first_stave = page == 0 and stave == 0
        line_offset = stave * self.stave_width + self.margin * 2
        assert line_offset >= 0
        if dwg.elements is None:
            dwg.elements = []
        emit = dwg.elements.append
        if self.write_borders:
            dwg.elements.extend(
                self._write_borders(line_offset=line_offset, page=page, stave=stave),
            )

        # draw caption (melody name and stave number)
        if self.write_captions:
            stave_crossnumber = page * self.staves_per_page + stave + 1
            assert line_offset >= 1
            y_top = line_offset - self.music_box.padding_top
            assert y_top >= 0
            caption = self.name if stave_crossnumber == 1 else f"#{stave_crossnumber}"
            dwg.elements.extend(self._write_text(
                x=self.margin * 2,
                y=y_top + self.stave_width - 1,
                text=caption,
                color="blue",
                size=self.font_size_captions,
            ))

        # draw lines
        for i, note in enumerate(self.music_box.notes):
            line_y = i * self.music_box.pitch + line_offset
            assert line_y >= 0
            margin_left = self.margin
            if first_stave:
                margin_left += self.start_width
            if self.write_lines:
                emit(svg.Line(
                    x1=mm(margin_left),
                    y1=mm(line_y),
                    x2=mm(self.stave_length + self.margin),
                    y2=mm(line_y),
                    stroke="grey",
                    stroke_width=mm(.1),
                ))
            if self.write_notes:
                dwg.elements.extend(self._write_text(
                    text=note.letter,
                    x=self.margin - 2,
                    y=line_y + self.font_size_notes / 2,
                    color="orange",
                    size=self.font_size_notes,
                ))

        # draw cut circles
        offset_time = (page * self.staves_per_page + stave) * self.stave_length - self.start_width
        trans = self.melody.best_transpose.shift
        latest_notes: dict[int, float] = dict()
        for sound in self.melody.sounds[offset:]:
            sound_offset = sound.time / self.speed - offset_time
            assert sound_offset >= 0
            if sound_offset > self.stave_length:
                break

            # place the sound, fill black for exact placement and fill red for transposed
            fill: str | None = "black"
            note_number = sound.note + trans
            assert note_number > 0
            assert note_number < 1000
            if self.music_box.contains_note(note_number):
                note_pos = self.music_box.get_note_pos(note_number)
            else:
                note_pos = self.music_box.guess_note_pos(note_number)
                fill = "red"
            assert fill in ("red", "black")

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

            emit(svg.Circle(
                cx=mm(sound_offset + self.margin),
                cy=mm(note_pos * self.music_box.pitch + line_offset),
                r=mm(self.diameter / 2),
                fill=fill,
                stroke=stroke,
                stroke_width=stroke_width,
            ))
            offset += 1
        assert offset >= 0
        return offset

    def _write_borders(
        self,
        line_offset: float,
        page: int,
        stave: int,
    ) -> Iterator[svg.Element]:
        x_left = self.margin
        x_right = self.margin + self.stave_length
        y_top = line_offset - self.music_box.padding_top
        y_bottom = y_top + self.stave_width

        # if this is the last stave, shorten its length to the melody length
        stave_number = page * self.staves_per_page + stave + 1
        if stave_number == self.staves_count:
            x_right = min(x_right, self.margin + self.last_stave_length + 5.0)

        # bottom border
        x_left_bottom = x_left
        # if there is only one stave, the bottom line should be shifted to align
        # with the starting triangle (usually, it is aligned with the stave below)
        if self.staves_count == 1:
            x_left_bottom += self.start_width
        yield svg.Line(
            x1=mm(x_left_bottom), y1=mm(y_bottom),
            x2=mm(x_right), y2=mm(y_bottom),
            stroke_width=mm(.1), stroke="green",
        )

        # left border
        if page == 0 and stave == 0:
            x_left += self.start_width
            x_peak = x_left - self.start_width
            y_mid_diff = (y_bottom - y_top) / 2
            y_middle = y_top + y_mid_diff
            quarter_diff = y_mid_diff / 2
            pairs = [
                (y_top, y_middle - quarter_diff),
                (y_middle, y_middle - quarter_diff),
                (y_middle, y_middle + quarter_diff),
                (y_bottom, y_middle + quarter_diff),
            ]
            for y1, y2 in pairs:
                yield svg.Line(
                    x1=mm(x_left), y1=mm(y1),
                    x2=mm(x_peak), y2=mm(y2),
                    stroke_width=mm(.1), stroke="green",
                )
        else:
            yield svg.Line(
                x1=mm(x_left), y1=mm(y_top),
                x2=mm(x_left), y2=mm(y_bottom),
                stroke_width=mm(.1), stroke="green",
            )

        # right border
        yield svg.Line(
            x1=mm(x_right), y1=mm(y_top),
            x2=mm(x_right), y2=mm(y_bottom),
            stroke_width=mm(.1), stroke="green",
        )

        # top border
        if stave == 0:
            yield svg.Line(
                x1=mm(x_left), y1=mm(y_top),
                x2=mm(x_right), y2=mm(y_top),
                stroke_width=mm(.1), stroke="green",
            )

    def _write_text(
        self,
        x: float,
        y: float,
        text: str,
        color: str,
        size: float,
    ) -> Iterator[svg.Element]:
        assert x > 0
        assert y > 0
        assert x < self.page_width
        assert y < self.page_height
        if not self.hershey:
            yield svg.Text(
                text=text, x=mm(x), y=mm(y),
                fill=color, font_size=mm(size),
            )
            return
        font = get_font(size=size)
        for (dx1, dy1), (dx2, dy2) in font.lines_for_text(text):
            yield svg.Line(
                x1=mm(x + dx1),
                y1=mm(y - dy1),
                x2=mm(x + dx2),
                y2=mm(y - dy2),
                stroke=color,
                stroke_width=mm(.1),
            )
