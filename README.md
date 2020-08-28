# LinearStitch #

LinearStitch is a very simple image stitcher designed for images show in a single horizontal line, from left to right, using something like a [Gigamacro](http://www.gigamacro.com).  

LinearStitch uses SIFT to identify matches between the likely-overlap regions of two images.  It then directly concatenates those images together (without blending).  The goal is to ensure that the original images are undistorted, even if that means the stitch seam itself is imperfect.

### Installation

Install the most recent version of python 3, which you can find [here](https://www.python.org/downloads/).

Install Zerene Stacker, which you can download from [here](https://zerenesystems.com/cms/stacker/softwaredownloads). It is recommended to use the default install folder.

To install all python dependencies using pip, run

```shell
pip install -r requirements.txt
```

You may then run the LinearStitch application using

```shell
python LS_GUI.py
```

tkinter is also required, but comes with most distributions of python. If it is missing you may install it using pip.

For more information on this software, please visit [labs.latis.umn.edu](http://labs.latis.umn.edu).
