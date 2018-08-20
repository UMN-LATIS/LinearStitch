from __future__ import print_function
import numpy as np
import cv2
import os
import platform

CONFIG={}
CONFIG['overlap'] = 0.35
CONFIG['max_features'] = 500
CONFIG['scale_factor'] = 0.5
CONFIG['flann_checks'] = 12

class Stitcher:
    maxOffset = 0;

    def calculate_offset(self,img1, img2, enableMask):
        # Calculate rough overlap in pixels
        overlap_px = img2.shape[1] * CONFIG['overlap']

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
        sift = cv2.xfeatures2d.SIFT_create(nfeatures=CONFIG['max_features'])
        self.logMessage('\t- Finding keypoints and descriptors for image 1')
        kp1, des1 = sift.detectAndCompute(i1, mask)
        self.logMessage('\t- Finding keypoints and descriptors for image 2')
        kp2, des2 = sift.detectAndCompute(i2, mask)

        # Use FLANN to determine matches
        self.logMessage('\t- Finding matches')

        # As of 10/11/2016, Flann is broken on binary builds of opencv for windows.  Fall back to BF in those cases.
        if(platform.system() != 'Windows'):
            flann = cv2.FlannBasedMatcher({'algorithm': 0, 'trees': 5}, {'checks': CONFIG['flann_checks']})
            matches = flann.knnMatch(des1, des2, k=2)
        else:
            bfMatch = cv2.BFMatcher(cv2.NORM_L2)
            matches = bfMatch.knnMatch(des1, des2, k=2)

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
        x_seam = int(img1.shape[1] - (img2.shape[1] * CONFIG['overlap']*.5) + x_offset)
        
        # how much of the new image should we crop out?
        partialImage = int(img2.shape[1] * CONFIG['overlap']*.5);

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


    def stitchFileList(self,images, outputPath, logFile, callback, enableMask, scaleImage):
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
            else:
                img1 = composite
                img2 = cv2.imread(images[i + 1])


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

                if(callback):
                    callback(1, round(i / len(images) * 100));
            except:
                self.logMessage("Error stitching {} and {}".format(images[i], images[i + 1]))

        if(composite is not None):
            cv2.imwrite(outputPath, composite)

        if(callback):
            callback(1, 100);

        self.logFile.close();
