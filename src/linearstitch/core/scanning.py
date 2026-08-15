"""Scanning a capture folder for problem images and file-count mismatches."""

from __future__ import annotations

import os
from collections.abc import Callable
from os.path import isdir, isfile, join

import cv2
import numpy

MessageCallback = Callable[[str], None]


class Processor:
    """Compute the average colour of an image (picklable for multiprocessing)."""

    def __init__(self, path: str) -> None:
        self._path = path

    def __call__(self, filename: str):
        myimg = cv2.imread(self._path + "/" + filename)
        avg_color_per_row = numpy.average(myimg, axis=0)
        avg_color = numpy.average(avg_color_per_row, axis=0)
        return avg_color


def scan_folder(path: str, pool) -> tuple[list[str], int]:
    """Return the list of colour-outlier images in ``path`` and a file count."""

    files = [f for f in os.listdir(path) if isfile(join(path, f))]
    files.sort()
    only_jpegs = [jpg for jpg in files if jpg.lower().endswith(".jpg")]
    if len(only_jpegs) < 1:
        return [], 0

    proc = Processor(path)
    color_average = pool.map(proc, only_jpegs)
    mean_values = numpy.array(color_average).mean(axis=0)

    problem_index = []
    for index, item in enumerate(color_average):
        distance = numpy.array(item) - mean_values
        if not all(abs(i) <= 20 for i in distance):
            problem_index.append(index)

    problem_files = [only_jpegs[i] for i in problem_index]
    return problem_files, 0


def scan_core(folder: str, pool, echo: MessageCallback | None = None) -> None:
    """Scan all child capture folders of ``folder`` and report problems."""

    emit = echo or print
    children_cores = [f for f in os.listdir(folder) if isdir(join(folder, f))]
    children_cores.sort()
    file_count_list: list[int] = []

    output_text = ""
    output_text += "Scanning for problems in: " + folder + "\n"
    output_text += "------------------------------------" + "\n"
    for core in children_cores:
        (problem_list, file_count) = scan_folder(folder + "/" + core, pool)
        file_count_list.append(file_count)
        if len(problem_list) > 0:
            for problem_file in problem_list:
                output_text += (
                    "Problem detected in: " + folder + "/" + core + "/" + problem_file + "\n"
                )
    if len(file_count_list) < 2:
        output_text += "Empty Folder: " + folder + "/" + "\n"
    else:
        core_mode = max(set(file_count_list), key=file_count_list.count)
        for index, core_count in enumerate(file_count_list):
            if core_count != core_mode:
                output_text += (
                    "File count mismatch in: " + folder + "/" + children_cores[index] + "\n"
                )
    output_text += "------------------------------------" + "\n" + "\n"
    emit(output_text)
