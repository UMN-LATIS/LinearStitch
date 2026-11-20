# LinearStitch #

LinearStitch is a very simple image stitcher designed for images show in a single horizontal line, from left to right, using something like a [Gigamacro](http://www.gigamacro.com).  

LinearStitch uses SIFT to identify matches between the likely-overlap regions of two images.  It then directly concatenates those images together (without blending).  The goal is to ensure that the original images are undistorted, even if that means the stitch seam itself is imperfect.

## Installation

The latest version of LinearStitch is available on the [Latest Release](https://github.com/UMN-LATIS/LinearStitch/releases/tag/latest) page. 

These releases are automatically generated as the code is updated. MacOS and Windows will not directly allow you to execute LinearStitch because they're not "signed" applications. On the Mac, right click on the application and select "open". It'll display a warning. Click "open anyways". You should only need to do that once.

On Windows, you'll similarly need to double click the icon and then click through to allow LinearStitch to run.

In order to use the built in FocusStack support, you'll need to download [FocusStack](https://github.com/PetteriAimonen/focus-stack) and place it in a folder on your computer. You'll need to follow the same steps above to authorize it.

## Rotation

The packaged macOS app includes libvips for rotation (straightening the image). For other installations, you'll need [Libvips](https://www.libvips.org). On macOS, this can be installed via Brew. For Windows users, you should install the prebuilt version of the libvips website and save it in c:\vips-dev. If you understand dylibs on Windows and can explain a better way to do that, I'm all ears.

## Configuration
The "Preferences" button allows you to set the input and output paths you'll be using. Be sure to set the path to FocusStack. 

Before stitching each core (after stacking, if enabled), LinearStitch checks for
gaps in numbered JPG filenames, such as `0001.jpg`, `0003.jpg`. If a gap is
found, an alert says "<core folder name> is potentially missing a file" and
lists the likely missing filenames. Long lists have a **Show Details** button;
very large consecutive gaps are shown as filename ranges.
Choose **Skip this core** to leave it unstitched and unarchived, or **Continue**
to stitch it anyway. To process without pausing, turn off **Pause on Missing
Files** in Preferences. Suspected missing filenames and reported processing errors are
then summarized in the log after all cores in the batch finish, including
archiving. This preference applies to batches queued after it is saved; each
externally submitted core is a separate batch.

Numbering can start anywhere and use any padding width.
The check compares matching filename patterns with one varying numeric field;
unnumbered or ambiguous names are left alone. It cannot detect missing images
before the first or after the last available number.

## Development

LinearStitch is a [PySide6](https://doc.qt.io/qtforpython/) desktop application managed with [uv](https://docs.astral.sh/uv/). The source lives under `src/linearstitch/`.

### Setup

```sh
uv venv
uv pip install -e ".[dev]"
```

### Run

```sh
uv run linearstitch          # launch the GUI
uv run linearstitch-fixstack --help   # stack-fixer CLI
```

The application can also be launched as a module: `python -m linearstitch`.

### Tests, linting & types

```sh
uv run pytest        # unit + golden + GUI smoke tests
uv run ruff check src tests
uv run mypy
```

The golden tests in `tests/` compare the refactored core against the original
algorithms (preserved verbatim under `tests/_legacy/`) to guarantee identical
stitching output.

### Project layout

```
src/linearstitch/
  app.py            # QApplication bootstrap
  branding.py       # LinearStitch
  config/           # typed settings (config.ini, unchanged format)
  core/             # GUI-free image processing + pipeline
  workers/          # background worker threads
  ipc/              # localhost:6234 job listener
  gui/              # PySide6 windows, dialogs, widgets, stylesheet
  cli/              # console entry points
```

## Packaging

Native bundles are built with [Briefcase](https://briefcase.readthedocs.io/)
(configured in `pyproject.toml`). The same codebase ships under two brands:

```sh
uv run briefcase build linearstitch   # LinearStitch.app
```

