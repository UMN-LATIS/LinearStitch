"""Focus-stacking integrations (Zerene Stacker and FocusStack)."""

from __future__ import annotations

import os
import statistics
import subprocess
from collections.abc import Callable
from os.path import isdir, isfile, join
from string import Template
from subprocess import DEVNULL

from ..config import Settings

MessageCallback = Callable[[str], None]


def stack_zerene(folder: str, settings: Settings, echo: MessageCallback | None = None) -> None:
    """Run Zerene Stacker over every child stack folder of ``folder``."""

    only_folders = [f for f in os.listdir(folder) if isdir(join(folder, f))]
    only_folders.sort()
    source_string = ""
    for stack_folder in only_folders:
        source_string += '<Source value="' + folder + "/" + stack_folder + '"/>\n'

    substitution_dict = {
        "batchLength": len(only_folders),
        "sourceFiles": source_string,
        "outputPath": folder + "/",
    }
    with open(settings.values["ZereneTemplateFile"]) as template:
        src = Template(template.read())
    populated_template = src.substitute(substitution_dict)

    xml_file = folder + "/stack.xml"
    with open(xml_file, "w") as output:
        output.write(populated_template)

    zerene_install = settings.values["ZereneInstall"]
    zerene_license = settings.values["ZereneLicense"]
    zerene_license = zerene_license.replace("{{APPDATA}}", os.getenv("APPDATA"))

    if not zerene_install.endswith("/"):
        zerene_install += "/"
    if not zerene_license.endswith("/"):
        zerene_license += "/"

    command_line = (
        settings.values["ZereneLaunchPath"]
        .replace("{{Install}}", zerene_install)
        .replace("{{License}}", zerene_license)
        .replace("{{script}}", xml_file)
    )

    subprocess.call(command_line, stdout=DEVNULL, stderr=subprocess.STDOUT)


def stack_focus_stack(
    folder: str, settings: Settings, echo: MessageCallback | None = None
) -> None:
    """Run FocusStack over every child stack folder of ``folder``."""

    emit = echo or print
    only_folders = [f for f in os.listdir(folder) if isdir(join(folder, f))]
    only_folders.sort()
    for stack_folder in only_folders:
        focus_stack_install = settings.values["FocusStackInstall"]
        input_path = ""
        if settings.values["PruneBeforeStacking"]:
            files = [
                f
                for f in os.listdir(folder + "/" + stack_folder)
                if isfile(join(folder + "/" + stack_folder, f))
            ]
            files.sort()
            only_jpegs = [jpg for jpg in files if jpg.lower().endswith(".jpg")]
            if len(only_jpegs) < 1:
                continue
            file_sizes = [
                os.path.getsize(folder + "/" + stack_folder + "/" + file)
                for file in only_jpegs
            ]
            median = statistics.median(file_sizes)
            for file in only_jpegs:
                if os.path.getsize(folder + "/" + stack_folder + "/" + file) >= median:
                    input_path = input_path + ' "' + folder + "/" + stack_folder + "/" + file + '"'
        else:
            input_path = '"' + folder + "/" + stack_folder + "/" + '"' + "*[jJ][pP][gG]"

        command_line = (
            settings.values["FocusStackLaunchPath"]
            .replace("{{Install}}", focus_stack_install)
            .replace("{{folderPath}}", input_path)
            .replace("{{outputPath}}", folder + "/" + stack_folder + ".jpg")
        )
        emit(command_line)
        subprocess.call(
            command_line, stdout=DEVNULL, stderr=subprocess.STDOUT, shell=True
        )
