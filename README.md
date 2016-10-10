# LinearStitch #

LinearStitch is a very simple image stitcher designed for images show in a single horizontal line, from left to right, using something like a [Gigamacro](http://www.gigamacro.com).  

LinearStitch uses SIFT to identify matches between the likely-overlap regions of two images.  It then directly concatenates those images together (without blending).  The goal is to ensure that the original images are undistorted, even if that means the stitch seam itself is imperfect.

To run LinearStitch, you'll need to have Python3 and OpenCV 3, along with a few python dependencies.  For instructions for installtion Python3 and OpenCV3 on the Mac, visit [http://seeb0h.github.io/howto/howto-install-homebrew-python-opencv-osx-el-capitan/](http://seeb0h.github.io/howto/howto-install-homebrew-python-opencv-osx-el-capitan/).  Windows instructions will follow shortly.

In additon to OpenCV, you'll need tkinter and numpy installed.  Both of these can be installed via pip.

For more information on this software, please visit [labs.latis.umn.edu](http://labs.latis.umn.edu).