# Linear Stitch
## An automated photo stitching tool by the UMN-LATIS team.

Linear Stitch is a utility to automatically combine photos into a
single larger image for analysis.

### Introduction

Linear stitch was built to combine photos of tree ring core samples
for study. Tree cores tell a detailed story about the environment that
the tree was exposed to throughout its life, but studying tree cores
is a manual and arduous process. To help in this process, hundreds of
photos are taken of the core so that the sample can be digitized. The
sample is then studied in specialized software which can display,
navigate, and measure the sample.

The only way to capture an image of a sample which is detailed enough
for research is to take many photos using a macro lens—a lens capable
of extremely close shots. At the UMN, we rely on
[Gigamacro](https://www.gigamacro.com/) to take photos of our samples,
and Linear Stitch was designed with Gigamacro in mind. Each individual
photo only captures part of the sample, however, and so a larger
composit image must be created from the incomplete parts. This
involves two steps.

Macro photography has a small depth of field, which means only a small
part of the core can be in focus for any particular photo. To produce
a single in-focus image, several shots are taken which each focus on a
different part of the subject. The photos must then be "stacked,"
where the in-focus parts of each photo are combined to produce a
seemingly perfect image. Linear Stitch uses [Zerene
Stacker](http://zerenesystems.com/cms/stacker) for focus stacking,
which you must license and download sperately. Instructions for this
are included in the README file.

The next step is to identify which images belong next to each other
and merge them together, like solving a jigsaw puzzle. Linear Stitch
uses the overlap between images to find and align combinations. These
combinations are eventually spliced into a single, high-resolution
image and exported as a TIFF.

### Getting Started.

The project can be installed from github.com. You will need Python 3
installed. Detailed and up to date installation instructions can be
found in the README.md file at the root of the project folder. To
download Linear Stitch onto your machine with git, use the commands

```shell
git clone https://github.com/UMN-LATIS/LinearStitch.git
ls LinearStitch
```

To run the application you will need python 3 and Zerene Stacker
installed. You can then run

```shell
pip install -r requirements.txt
python LS_GUI.py
```

to start the application.

![A screenshot of the Linear Stitch application.](/app.png)

To queue a directory for stitching click the "+" button. You will be
prompted to select a directory from your pc. The "Start Processing"
button will begin to stitch the directories added. At first you should
see Zerene Stacker processes showing the progress on each stack of
images, then Linear Stitch will work to find matching pairs and merge
them together. This could take a while.