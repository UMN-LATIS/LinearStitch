"""Config tests: defaults, round-trip persistence, and on-disk format."""

from __future__ import annotations

import configparser

from linearstitch.config import Settings


def test_defaults_match_original(tmp_path):
    settings = Settings(config_path=tmp_path / "config.ini")
    v = settings.values

    assert v["CoreCount"] == "4"
    assert v["Overlap"] == "0.35"
    assert v["VignetteMagic"] == "1.1"
    assert v["FocusThreshold"] == "13.0"
    assert v["RightToLeft"] is False
    assert v["PruneBeforeStacking"] is False
    assert v["StackerSelection"] == "FocusStack"
    assert v["ZereneTemplateFile"] == "zereneTemplate.xml"


def test_typed_accessors(tmp_path):
    settings = Settings(config_path=tmp_path / "config.ini")
    assert settings.core_count == 4
    assert settings.overlap == 0.35
    assert settings.vignette_magic == 1.1
    assert settings.focus_threshold == 13.0
    assert settings.right_to_left is False
    assert settings.prune_before_stacking is False
    assert settings.stacker_selection == "FocusStack"


def test_round_trip(tmp_path):
    path = tmp_path / "config.ini"
    settings = Settings(config_path=path)
    settings.values["Overlap"] = "0.5"
    settings.values["RightToLeft"] = True
    settings.values["CoreCount"] = "8"
    settings.values["StackerSelection"] = "Zerene"
    settings.save()

    # Verify on-disk format uses the original section/key names.
    parser = configparser.ConfigParser()
    parser.read(path)
    assert parser.get("Processing", "Overlap") == "0.5"
    assert parser.get("Processing", "RightToLeft") == "1"
    assert parser.get("Processing", "CoreCount") == "8"
    assert parser.get("Processing", "StackerSelection") == "Zerene"

    # Reload and confirm values survive.
    reloaded = Settings(config_path=path)
    assert reloaded.values["Overlap"] == "0.5"
    assert reloaded.values["RightToLeft"] is True
    assert reloaded.core_count == 8
    assert reloaded.stacker_selection == "Zerene"
