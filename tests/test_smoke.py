import sys
from punchline import main

from pathlib import Path

import pytest


input_root = Path(__file__).parent.parent / 'midi'


@pytest.mark.parametrize('input_path', input_root.iterdir())
def test_defaults(input_path: Path):
    cmd = ['--input', str(input_path)]
    code = main(cmd, sys.stdout)
    assert code == 0


def test_no_notes():
    input_path = list(input_root.iterdir())[0]
    cmd = ['--input', str(input_path), '--tracks', '100']
    code = main(cmd, sys.stdout)
    assert code == 0


@pytest.mark.parametrize('input_path', input_root.iterdir())
def test_laser_cutter(input_path: Path):
    cmd = ['--no-notes', '--no-lines', '--hershey', '--input', str(input_path)]
    code = main(cmd, sys.stdout)
    assert code == 0
