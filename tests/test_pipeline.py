"""Sequence checks at the boundary between stacking and stitching."""

from unittest.mock import Mock

import pytest

from linearstitch.config import Settings
from linearstitch.core.pipeline import Pipeline, SequenceGap, find_sequence_gaps


@pytest.mark.parametrize(
    ("names", "expected"),
    [
        (["0001.jpg", "0003.jpg"], True),
        (["core_01.jpg", "core_02.jpg", "core_04.JPG"], True),
        (["core7_col_001_stacked.jpg", "core7_col_003_stacked.jpg"], True),
        (["10.jpg", "9.jpg", "11.jpg"], False),
        (["0032.jpg", "0033.jpg"], False),
        (["one.jpg", "three.jpg"], False),
        (["core_01.jpg", "other_03.jpg"], False),
        (["row1_col1.jpg", "row2_col3.jpg"], False),
        (["0001.jpg"], False),
        ([], False),
    ],
)
def test_sequence_gaps(names, expected):
    assert bool(find_sequence_gaps(names)) is expected


@pytest.mark.parametrize(
    ("names", "expected"),
    [
        (["0001.jpg", "0003.jpg"], ["0002.jpg"]),
        (["core_01.jpg", "core_02.jpg", "core_04.JPG"], ["core_03.jpg"]),
        (["core7_col_001_stacked.jpg", "core7_col_003_stacked.jpg"],
         ["core7_col_002_stacked.jpg"]),
        (["photo_06.JPG", "photo_01.JPG", "photo_03.JPG"],
         ["photo_02.JPG", "photo_04.JPG", "photo_05.JPG"]),
        (["9.jpg", "11.jpg"], ["10.jpg"]),
        (["8.jpg", "12.jpg"], ["9.jpg", "10.jpg", "11.jpg"]),
        (["img_098.jpg", "img_102.jpg"],
         ["img_099.jpg", "img_100.jpg", "img_101.jpg"]),
        (["1.jpg", "003.jpg"], ["002.jpg"]),
        (["b_001.jpg", "a_1.jpg", "b_003.jpg", "a_3.jpg"], ["a_2.jpg", "b_002.jpg"]),
    ],
)
def test_missing_filenames(names, expected):
    gaps = find_sequence_gaps(names)
    assert [
        gap.filename(number)
        for gap in gaps
        for number in range(gap.first, gap.last + 1)
    ] == expected


def test_large_gap_is_represented_without_expanding_it():
    gap, = find_sequence_gaps(["image_0001.jpg", "image_999999999999.jpg"])
    assert gap.first == 2
    assert gap.last == 999999999998
    assert gap.filename(gap.first) == "image_0002.jpg"
    assert gap.filename(gap.last) == "image_999999999998.jpg"


@pytest.mark.parametrize("continue_stitching", [True, False])
def test_stitch_checks_actual_jpgs_before_processing(tmp_path, monkeypatch, continue_stitching):
    import linearstitch.core.pipeline as pipeline_module

    core = tmp_path / "core_a"
    core.mkdir()
    for name in ("0001.jpg", "0003.JPG", "core_a_preview.jpg", "notes_99.txt"):
        (core / name).touch()
    # A raw stack folder cannot fill a gap in the stacked output images.
    (core / "0002").mkdir()
    settings = Settings(config_path=tmp_path / "config.ini")
    settings.values["RightToLeft"] = True
    confirm = Mock(return_value=continue_stitching)
    stitcher = Mock()
    monkeypatch.setattr(pipeline_module, "Stitcher", Mock(return_value=stitcher))
    copy = Mock()
    monkeypatch.setattr(pipeline_module.shutil, "copy", copy)
    pipeline = Pipeline(settings, confirm_sequence_gap=confirm)

    assert pipeline.stitch(str(core)) is continue_stitching
    confirm.assert_called_once_with(
        str(core), [SequenceGap(prefix="", suffix=".jpg", width=4, first=2, last=2)]
    )
    assert stitcher.stitch_file_list.called is continue_stitching
    assert copy.called is continue_stitching
    if continue_stitching:
        assert stitcher.stitch_file_list.call_args.args[0] == [
            str(core / "core_a_preview.jpg"),
            str(core / "0003.JPG"),
            str(core / "0001.jpg"),
        ]


def test_contiguous_sequence_does_not_prompt(tmp_path, monkeypatch):
    import linearstitch.core.pipeline as pipeline_module

    for name in ("01.jpg", "02.jpg"):
        (tmp_path / name).touch()
    monkeypatch.setattr(pipeline_module, "Stitcher", Mock())
    monkeypatch.setattr(pipeline_module.shutil, "copy", Mock())
    confirm = Mock()
    pipeline = Pipeline(
        Settings(config_path=tmp_path / "config.ini"), confirm_sequence_gap=confirm
    )
    assert pipeline.stitch(str(tmp_path))
    confirm.assert_not_called()
