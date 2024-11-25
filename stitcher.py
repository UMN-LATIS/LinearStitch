# © 2024 Regents of the University of Minnesota. All rights reserved.
# This program is shared under the terms and conditions of the GNU General Public License 3.0, License. Further details about the GNU GPL 3.0 license are available in the license.txt file

from __future__ import print_function
import numpy as np
import cv2
import os
import platform
import pyopencl as cl
import ctypes
import ctypes.util
# if (ctypes.util.find_library('libvips-42') or ctypes.util.find_library('libvips')):
import pyvips


CONFIG={}
CONFIG['max_features'] = 500
CONFIG['scale_factor'] = 0.25
CONFIG['flann_checks'] = 12

class Stitcher:
    maxOffset = 0;
    overlap = 0.35;


    def __init__(self, overlapValue):
        self.overlap = overlapValue

    def calculate_offset(self,img1, img2, enableMask):
        # Calculate rough overlap in pixels
        overlap_px = img2.shape[1] * self.overlap

        # Convert images to grayscale and reduce size to scale_factor
        i1 = cv2.cvtColor(cv2.resize(img1[:, -int(overlap_px):, :], (0, 0), fx=CONFIG['scale_factor'], fy=CONFIG['scale_factor']), cv2.COLOR_BGR2GRAY)
        i2 = cv2.cvtColor(cv2.resize(img2[:, :int(overlap_px), :], (0, 0), fx=CONFIG['scale_factor'], fy=CONFIG['scale_factor']), cv2.COLOR_BGR2GRAY)


        if(enableMask):
            height, width = i1.shape[:2]
            mask = np.zeros(i1.shape[:2], np.uint8)
            rounded = round(height/4);
            mask[rounded:height-rounded, 0:width] = 255
        else:
            mask = None;

        # Find SIFT keypoints and descriptors
        sift = cv2.SIFT_create(nfeatures=CONFIG['max_features'])
        self.logMessage('\t- Finding keypoints and descriptors for image 1')
        kp1, des1 = sift.detectAndCompute(i1, mask)
        self.logMessage('\t- Finding keypoints and descriptors for image 2')
        kp2, des2 = sift.detectAndCompute(i2, mask)

        # Use FLANN to determine matches
        self.logMessage('\t- Finding matches')

        # As of 10/11/2016, Flann is broken on binary builds of opencv for windows.  Fall back to BF in those cases.
        # if(platform.system() != 'Windows'):
        flann = cv2.FlannBasedMatcher({'algorithm': 0, 'trees': 5}, {'checks': CONFIG['flann_checks']})
        matches = flann.knnMatch(des1, des2, k=2)
        # else:
        # bfMatch = cv2.BFMatcher(cv2.NORM_L2)
        # matches = bfMatch.knnMatch(des1, des2, k=2)

        # Limit to reasonable matches
        good_matches = [m for m, n in matches if m.distance < 0.7 * n.distance]
        src_pts = np.float32([kp1[match.queryIdx].pt for match in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[match.trainIdx].pt for match in good_matches]).reshape(-1, 1, 2)

        # We're not doing any robust analyses of outliers, so let's just take the median and see how it works
        x_offset = int(np.median([elem[0][0] for elem in np.subtract(src_pts, dst_pts)]))
        y_offset = int(np.median([elem[0][1] for elem in np.subtract(src_pts, dst_pts)]))


        # Rescale offset for original size and return
        self.logMessage('\t- X Offset found: {} px'.format(x_offset * (1/CONFIG['scale_factor'])))
        self.logMessage('\t- Y Offset found: {} px'.format(y_offset * (1/CONFIG['scale_factor'])))
        return (x_offset * (1/CONFIG['scale_factor']),y_offset * (1/CONFIG['scale_factor']))


    def stitch_images(self,img1, img2, enableMask):
        # Find the offset between the images and calcuate where the seam lies
        x_offset, y_offset = self.calculate_offset(img1, img2, enableMask)

        # we want to seam the images such that we crop the left and right equally.  So use roughly have the overlap betwen them.
        x_seam = int(img1.shape[1] - (img2.shape[1] * self.overlap*.5) + x_offset)
        
        # how much of the new image should we crop out?
        partialImage = int(img2.shape[1] * self.overlap*.5);

        self.maxOffset = max(self.maxOffset, y_offset);

        # Create the composite image and return
        width = x_seam + (img2.shape[1]-partialImage)
        height = img2.shape[0] + abs(int(self.maxOffset))

        if(y_offset < 0.0):
            comp_img = np.zeros((height+int(abs(y_offset)), width, 3), np.uint8)
            self.maxOffset += int(abs(y_offset))
            comp_img[int(abs(y_offset)):img1.shape[0]+int(abs(y_offset)), 0:x_seam] = img1[0:img1.shape[0], 0:x_seam]
            comp_img[0:img2.shape[0], x_seam:(x_seam+img2.shape[1]-partialImage)] = img2[0:img2.shape[0], partialImage:img2.shape[1]]
        else:
            comp_img = np.zeros((height, width, 3), np.uint8)
            comp_img[0:img1.shape[0], 0:x_seam] = img1[0:img1.shape[0], 0:x_seam]
            comp_img[int(y_offset):img2.shape[0]+int(y_offset), x_seam:(x_seam+img2.shape[1]-partialImage)] = img2[0:img2.shape[0], partialImage:img2.shape[1]]
        
        return comp_img

    def logMessage(self, message):
        self.logFile.write(message + "\n")
        print(message)


    def removeVignette(self, img, vignetteMagicNumber):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # apply the vignette correction algorithm using OpenCL
        rows, cols = gray.shape
        center = (cols//2, rows//2)
        mask = np.zeros(gray.shape, dtype=np.float32)

        # define an OpenCL kernel that computes the mask for a given row
        mask_kernel = f'''
        __kernel void compute_mask(__global float *mask, int rows, int cols, int center_x, int center_y)
        \u007b
            int row = get_global_id(1);
            int col = get_global_id(0);
            if (row < rows && col < cols)
                mask[row * cols + col] = 1 + {vignetteMagicNumber}*(pow((float)(row - center_y), 2) + pow((float)(col - center_x), 2))/(rows*rows + cols*cols);
        \u007d
        '''

        # create an OpenCL context and queue
        platform = cl.get_platforms()
        my_gpu_devices = platform[0].get_devices(device_type=cl.device_type.GPU)
        ctx = cl.Context(devices=my_gpu_devices)
        queue = cl.CommandQueue(ctx)

        # create an OpenCL buffer for the mask
        mask_buf = cl.Buffer(ctx, cl.mem_flags.WRITE_ONLY, mask.nbytes)

        # compile and run the OpenCL kernel
        prg = cl.Program(ctx, mask_kernel).build()
        prg.compute_mask(queue, (cols, rows), None, mask_buf, np.int32(rows), np.int32(cols), np.int32(center[0]), np.int32(center[1]))

        # copy the result from the OpenCL buffer to the NumPy array
        cl.enqueue_copy(queue, mask, mask_buf)

        corrected = np.clip(img * mask[:,:,np.newaxis], 0, 255)
        return np.rint(corrected).astype(np.uint8)

    def rotateAndCrop(self, image):
        scale_percent = 2.5 # percent of original size
        width = int(image.shape[1] * scale_percent / 100)
        height = int(image.shape[0] * scale_percent / 100)
        dim = (width, height)
        
        # resize image
        resized = cv2.resize(image, dim, interpolation = cv2.INTER_AREA)

        # write the scaled image to disk
        cv2.imwrite('scaled_image.jpg', resized)

        # Convert the image to grayscale
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        (thresh, blackAndWhiteImage) = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        # blur the image with a guassian blur
        blurred = cv2.GaussianBlur(blackAndWhiteImage, (5, 5), 0)

        # Find contours
        contours, _ = cv2.findContours(blurred, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Find largest contour
        max_area = 0
        largest_contour = None
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > max_area:
                max_area = area
                largest_contour = contour

        if largest_contour is not None:
            # Get moments of the largest contour
            M = cv2.moments(largest_contour)

            # Get center of mass of the largest contour
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

            # Get angle of the largest contour
            (x, y), (MA, ma), angle = cv2.fitEllipse(largest_contour)

        x = pyvips.Image.new_from_array(image[...,::-1])
        x = x.rotate((90-angle), interpolate=pyvips.Interpolate.new("bicubic"))
        
        print(angle)
        # get the height of the area that we want to crop by using the inverse sign of the rotation angle and the width of the image
        height = int(image.shape[1] * np.abs(np.sin(np.radians(90-angle))))

        # crop the height of the image to 2x height center crop
        x = x.crop(0, height, x.width, x.height - (height * 2))

        # mask = (x.median(3) - [0.0, 0.0, 0.0]).abs() > 10
        # columns, rows = mask.project()

        # left = columns.profile()[1].min()
        # right = columns.width - columns.flip("horizontal").profile()[1].min()
        # top = rows.profile()[0].min()
        # bottom = rows.height - rows.flip("vertical").profile()[0].min()

        # x = x.crop(left, top, right - left, bottom - top)

        # find the rectangle which crops all of the black area from the image



        result = x.numpy()
        return result[...,::-1]

    def stitchFileList(self,images, outputPath,scaledPreviewFile, logFile, callback, enableMask, scaleImage, verticalCore, removeVignette, vignetteMagicNumber=1.1, rotateImage = False, cropImage = False):
        composite = None;
        # Starting from the left, stitch the next image in the sequence to the intermediate file.
        
        self.logFile = open(logFile, 'w');

        self.logMessage("Beginning batch processing for: " + outputPath);
        self.logMessage("Masking is: " + str(enableMask));
        if(scaleImage):
            self.logMessage("Scale File Is: " + scaleImage);

        firstImage = True;
        for i in range(0, len(images) - 1):
            if i == 0:
                img1 = cv2.imread(images[i])
                img2 = cv2.imread(images[i + 1])
                if(removeVignette):
                    img1 = self.removeVignette(img1, vignetteMagicNumber)
                    img2 = self.removeVignette(img2, vignetteMagicNumber)
                if(verticalCore):
                    img1 = cv2.rotate(img1, cv2.ROTATE_90_COUNTERCLOCKWISE)
                    img2 = cv2.rotate(img2, cv2.ROTATE_90_COUNTERCLOCKWISE)
            else:
                img1 = composite
                img2 = cv2.imread(images[i + 1])
                if(removeVignette):
                    img2 = self.removeVignette(img2, vignetteMagicNumber)
                if(verticalCore):
                    img2 = cv2.rotate(img2, cv2.ROTATE_90_COUNTERCLOCKWISE)


            try:
                self.logMessage("Stitching Image {} and {}".format(images[i], images[i + 1]))
                composite = self.stitch_images(img1, img2, enableMask)
                if(firstImage):
                    firstImage = False;
                    if(scaleImage):
                        img1 = cv2.imread(scaleImage);
                        h1, w1 = img1.shape[:2]
                        h2, w2 = composite.shape[:2]
                        vis = np.zeros((max(h1, h2), w1+w2, 3), np.uint8)
                        vis[:h1, :w1] = img1
                        vis[:h2, w1:w1+w2] = composite
                        composite = vis
                self.logMessage("Size of Composite: " + str(composite.shape))
                if(callback):
                    callback(1, round(i / len(images) * 100));
            except Exception as e:
                print(e)
                self.logMessage("Error stitching {} and {}".format(images[i], images[i + 1]))


        if(cropImage and not rotateImage):
            self.logMessage("Cropping Image")
            composite = composite[int(self.maxOffset):(composite.shape[0]-int(self.maxOffset)), 0:composite.shape[1]]

        if(rotateImage):
            self.logMessage("Rotating Image")
            composite = self.rotateAndCrop(composite)

        
        # crop image based on max offset
        

        # scale_percent = 5 # percent of original size
        # width = int(composite.shape[1] * scale_percent / 100)
        # height = int(composite.shape[0] * scale_percent / 100)
        # dim = (width, height)
        
        # # resize image
        # resized = cv2.resize(composite, dim, interpolation = cv2.INTER_AREA)

        # # Convert the image to grayscale
        # gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        # (thresh, blackAndWhiteImage) = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        # # Find contours
        # contours, _ = cv2.findContours(blackAndWhiteImage, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # # Find largest contour
        # max_area = 0
        # largest_contour = None
        # for contour in contours:
        #     area = cv2.contourArea(contour)
        #     if area > max_area:
        #         max_area = area
        #         largest_contour = contour

        # #draw the largest contour to screen
        # cv2.drawContours(resized, [largest_contour], 0, (0, 255, 0), 3)
        # # display on screen
        # cv2.imshow('Largest Contour', resized)
        

        self.logMessage("Size of Composite: " + str(composite.shape))
        if(composite is not None):
            cv2.imwrite(outputPath, composite)

        # resize the image to a max 1000pixel wide by 1000pixel high
        if composite.shape[0] > 1000 or composite.shape[1] > 1000:
            self.logMessage("Writing preview image")
            if composite.shape[0] > composite.shape[1]:
                scale_percent = 1000 / composite.shape[0] * 100
            else:
                scale_percent = 1000 / composite.shape[1] * 100
            width = int(composite.shape[1] * scale_percent / 100)
            height = int(composite.shape[0] * scale_percent / 100)
            dim = (width, height)
            # resize image
            resized = cv2.resize(composite, dim, interpolation = cv2.INTER_AREA)
            cv2.imwrite(scaledPreviewFile, resized)

        self.logMessage("Finished")
        if(callback):
            callback(1, 100);

        self.logFile.close();
