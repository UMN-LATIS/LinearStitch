# LinearStitch #

LinearStitch is a very simple image stitcher designed for images show in a single horizontal line, from left to right, using something like a [Gigamacro](http://www.gigamacro.com).  

LinearStitch uses SIFT to identify matches between the likely-overlap regions of two images.  It then directly concatenates those images together (without blending).  The goal is to ensure that the original images are undistorted, even if that means the stitch seam itself is imperfect.

## Installation

The latest version of LinearStitch is available on the [Latest Release](https://github.com/UMN-LATIS/LinearStitch/releases/tag/latest) page. 

These releases are automatically generated as the code is updated. MacOS and Windows will not directly allow you to execute LinearStitch because they're not "signed" applications. On the Mac, right click on the application and select "open". It'll display a warning. Click "open anyways". You should only need to do that once.

On Windows, you'll similarly need to double click the icon and then click through to allow LinearStitch to run.

In order to use the built in FocusStack support, you'll need to download [FocusStack](https://github.com/PetteriAimonen/focus-stack) and place it in a folder on your computer. You'll need to follow the same steps above to authorize it.

## Configuration
The "prefs" button allows you to set the input and output paths you'll be using. Be sure to set the path to FocusStack. 