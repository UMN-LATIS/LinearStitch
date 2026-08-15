"""Configuration management.

This is a faithful, typed reimplementation of the original ``config.LSConfig``.
The on-disk format, section names, keys, defaults, fallbacks and file location
are preserved exactly so existing ``config.ini`` files load unchanged.
"""

from __future__ import annotations

import configparser
import pathlib
from typing import Any

import platformdirs

_HOME = pathlib.Path.home()
_APP_NAME = "LinearStitch"

# Default fallbacks — kept identical to the original implementation.
_ZERENE_LAUNCH_DEFAULT = (
    '"{{Install}}jre/bin/java.exe" -Xmx8000m -DjavaBits=64bitJava '
    '-Dlaunchcmddir="{{License}}" -classpath '
    '"{{Install}}ZereneStacker.jar;{{Install}}JREextensions/*" '
    "com.zerenesystems.stacker.gui.MainFrame -noSplashScreen "
    '-exitOnBatchScriptCompletion -runMinimized  -batchScript "{{script}}"'
)
_FOCUSSTACK_LAUNCH_DEFAULT = (
    '"{{Install}}" --consistency=0 --align-keep-size --no-whitebalance '
    '--no-contrast --jpgquality=100 --output="{{outputPath}}" {{folderPath}}'
)


def default_config_path() -> pathlib.Path:
    """Return the platform-specific path to ``config.ini``.

    ``platformdirs`` produces the same locations as the original ``appdirs``
    dependency on macOS, Windows and Linux.
    """

    return pathlib.Path(platformdirs.user_config_dir(_APP_NAME)) / "config.ini"


class Settings:
    """Typed wrapper around the ``config.ini`` persisted settings."""

    def __init__(self, config_path: pathlib.Path | None = None) -> None:
        self.config_path = config_path or default_config_path()
        self.parser = configparser.ConfigParser()
        self.values: dict[str, Any] = {}

        if not self.config_path.is_file():
            self._write_empty_sections()

        self._load()

    # -- persistence ------------------------------------------------------

    def _write_empty_sections(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            "\n[General]\n[Zerene]\n[Processing]\n[FocusStack]\n\t\t"
        )

    def _ensure_sections(self) -> None:
        for section in ("General", "Zerene", "Processing", "FocusStack"):
            if section not in self.parser:
                self.parser[section] = {}

    def _load(self) -> None:
        self.parser.read(self.config_path)
        self._ensure_sections()

        home = str(_HOME.absolute())
        get = self.parser.get
        v = self.values

        v["BrowsePath"] = get("General", "BrowsePath", fallback=home)
        v["ArchivePath"] = get("General", "ArchivePath", fallback=home)
        v["CoreOutputPath"] = get("General", "CoreOutputPath", fallback=home)

        v["ZereneInstall"] = get("Zerene", "Install", fallback=home)
        v["ZereneLicense"] = get("Zerene", "License", fallback="{{APPDATA}}/ZereneStacker/")
        v["ZereneLaunchPath"] = get("Zerene", "LaunchPath", fallback=_ZERENE_LAUNCH_DEFAULT)
        v["ZereneTemplateFile"] = get("Zerene", "TemplateFile", fallback="zereneTemplate.xml")

        v["CoreCount"] = get("Processing", "CoreCount", fallback="4")
        v["VignetteMagic"] = get("Processing", "VignetteMagic", fallback="1.1")
        v["Overlap"] = get("Processing", "Overlap", fallback="0.35")
        v["FocusThreshold"] = get("Processing", "FocusThreshold", fallback="13.0")
        v["RightToLeft"] = get("Processing", "RightToLeft", fallback="0") == "1"
        v["PruneBeforeStacking"] = get("Processing", "PruneBeforeStacking", fallback="0") == "1"
        v["StackerSelection"] = get("Processing", "StackerSelection", fallback="FocusStack")

        v["FocusStackInstall"] = get("FocusStack", "Install", fallback=home)
        v["FocusStackLaunchPath"] = get(
            "FocusStack", "LaunchPath", fallback=_FOCUSSTACK_LAUNCH_DEFAULT
        )

    def save(self) -> None:
        """Persist the current values back to ``config.ini``."""

        self._ensure_sections()
        v = self.values
        s = self.parser.set

        s("General", "BrowsePath", v["BrowsePath"])
        s("General", "ArchivePath", v["ArchivePath"])
        s("General", "CoreOutputPath", v["CoreOutputPath"])

        s("Zerene", "Install", v["ZereneInstall"])
        s("Zerene", "License", v["ZereneLicense"])
        s("Zerene", "LaunchPath", v["ZereneLaunchPath"])
        s("Zerene", "TemplateFile", v["ZereneTemplateFile"])

        s("Processing", "CoreCount", str(v["CoreCount"]))
        s("Processing", "FocusThreshold", str(v["FocusThreshold"]))
        s("Processing", "VignetteMagic", str(v["VignetteMagic"]))
        s("Processing", "Overlap", str(v["Overlap"]))
        s("Processing", "RightToLeft", "1" if v["RightToLeft"] else "0")
        s("Processing", "PruneBeforeStacking", "1" if v["PruneBeforeStacking"] else "0")
        s("Processing", "StackerSelection", v["StackerSelection"])

        s("FocusStack", "Install", v["FocusStackInstall"])
        s("FocusStack", "LaunchPath", v["FocusStackLaunchPath"])

        with open(self.config_path, "w") as f:
            self.parser.write(f)

    # -- typed convenience accessors -------------------------------------

    @property
    def core_count(self) -> int:
        return int(self.values["CoreCount"])

    @property
    def overlap(self) -> float:
        return float(self.values["Overlap"])

    @property
    def vignette_magic(self) -> float:
        return float(self.values["VignetteMagic"])

    @property
    def focus_threshold(self) -> float:
        return float(self.values["FocusThreshold"])

    @property
    def right_to_left(self) -> bool:
        return bool(self.values["RightToLeft"])

    @property
    def prune_before_stacking(self) -> bool:
        return bool(self.values["PruneBeforeStacking"])

    @property
    def stacker_selection(self) -> str:
        return str(self.values["StackerSelection"])
