from __future__ import print_function
import numpy as np
import cv2
import os
import platform

CONFIG={}
CONFIG['overlap'] = 0.55
CONFIG['max_features'] = 500
CONFIG['scale_factor'] = 0.5
CONFIG['flann_checks'] = 12

class TwoDStitcher:
    maxOffset = 0;

    def calculate_offset(self,img1, img2, orientation):
        
        
        if(orientation == "vertical"):
            # Calculate rough overlap in pixels
            overlap_px = img2.shape[0] * CONFIG['overlap']
            # Convert images to grayscale and reduce size to scale_factor
            i1 = cv2.cvtColor(cv2.resize(img1[-int(overlap_px):, :, :], (0, 0), fx=CONFIG['scale_factor'], fy=CONFIG['scale_factor']), cv2.COLOR_BGR2GRAY)
            i2 = cv2.cvtColor(cv2.resize(img2[:int(overlap_px), :, :], (0, 0), fx=CONFIG['scale_factor'], fy=CONFIG['scale_factor']), cv2.COLOR_BGR2GRAY)     
        else:
            overlap_px = img2.shape[1] * CONFIG['overlap']
            # Convert images to grayscale and reduce size to scale_factor
            i1 = cv2.cvtColor(cv2.resize(img1[:, -int(overlap_px):, :], (0, 0), fx=CONFIG['scale_factor'], fy=CONFIG['scale_factor']), cv2.COLOR_BGR2GRAY)
            i2 = cv2.cvtColor(cv2.resize(img2[:, :int(overlap_px), :], (0, 0), fx=CONFIG['scale_factor'], fy=CONFIG['scale_factor']), cv2.COLOR_BGR2GRAY)

        # Find SIFT keypoints and descriptors
        sift = cv2.SIFT_create(nfeatures=CONFIG['max_features'])
        print('\t- Finding keypoints and descriptors for image 1')
        kp1, des1 = sift.detectAndCompute(i1, None)
        print('\t- Finding keypoints and descriptors for image 2')
        kp2, des2 = sift.detectAndCompute(i2, None)

        # Use FLANN to determine matches
        print('\t- Finding matches')

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
        print('\t- X Offset found: {} px'.format(x_offset * (1/CONFIG['scale_factor'])))
        print('\t- Y Offset found: {} px'.format(y_offset * (1/CONFIG['scale_factor'])))
        return (x_offset * (1/CONFIG['scale_factor']),y_offset * (1/CONFIG['scale_factor']))


    def stitch_images(self,img1, img2, orientation):
        # Find the offset between the images and calcuate where the seam lies
        x_offset, y_offset = self.calculate_offset(img1, img2, orientation)

        # we want to seam the images such that we crop the left and right equally.  So use roughly have the overlap betwen them.
        if(orientation == "vertical"):
            seam = int(img1.shape[0] - (img2.shape[0] * CONFIG['overlap']*.5) + y_offset)
            # how much of the new image should we crop out?
            partialImage = int(img2.shape[0] * CONFIG['overlap']*.5);

            self.maxOffset = max(self.maxOffset, x_offset);
            # Create the composite image and return
            height = seam + (img2.shape[0]-partialImage)
            width = img2.shape[1] + abs(int(self.maxOffset))
            if(x_offset < 0.0):
                comp_img = np.zeros((height, width+int(abs(x_offset)), 3), np.uint8)
                self.maxOffset += int(abs(x_offset))
                comp_img[0:seam,int(abs(x_offset)):img1.shape[1]+int(abs(x_offset))] = img1[0:seam,0:img1.shape[1]]
                comp_img[seam:(seam+img2.shape[0]-partialImage),0:img2.shape[1]] = img2[partialImage:img2.shape[0],0:img2.shape[1] ]
            else:
                comp_img = np.zeros((height, width, 3), np.uint8)
                comp_img[0:seam,0:img1.shape[1]] = img1[0:seam,0:img1.shape[1]]
                comp_img[seam:(seam+img2.shape[0]-partialImage),int(x_offset):img2.shape[1]+int(x_offset)] = img2[partialImage:img2.shape[0],0:img2.shape[1]]
        else:
            seam = int(img1.shape[1] - (img2.shape[1] * CONFIG['overlap']*.5) + x_offset)
            # how much of the new image should we crop out?
            partialImage = int(img2.shape[1] * CONFIG['overlap']*.5);

            self.maxOffset = max(self.maxOffset, y_offset);
            # Create the composite image and return
            width = seam + (img2.shape[1]-partialImage)
            height = max(img1.shape[0], img2.shape[0] + abs(int(self.maxOffset)))
            if(y_offset < 0.0):
                comp_img = np.zeros((height+int(abs(y_offset)), width, 3), np.uint8)
                self.maxOffset += int(abs(y_offset))
                comp_img[int(abs(y_offset)):img1.shape[0]+int(abs(y_offset)), 0:seam] = img1[0:img1.shape[0], 0:seam]
                comp_img[0:img2.shape[0], seam:(seam+img2.shape[1]-partialImage)] = img2[0:img2.shape[0], partialImage:img2.shape[1]]
            else:
                comp_img = np.zeros((height, width, 3), np.uint8)
                comp_img[0:img1.shape[0], 0:seam] = img1[0:img1.shape[0], 0:seam]
                comp_img[int(y_offset):img2.shape[0]+int(y_offset), seam:(seam+img2.shape[1]-partialImage)] = img2[0:img2.shape[0], partialImage:img2.shape[1]]

        
        return comp_img


    def stitchFileList(self,images, outputPath, orientation, callback):
        composite = None
        # Starting from the left, stitch the next image in the sequence to the intermediate file.
        for i in range(0, len(images) - 1):
            if i == 0:
                img1 = cv2.imread(images[i])
                img2 = cv2.imread(images[i + 1])
            else:
                img1 = composite
                img2 = cv2.imread(images[i + 1])

            print("Stitching Image {} and {}".format(i, i + 1))
            composite = self.stitch_images(img1, img2,orientation)
            print("SIZE OF COMPOSITE: {}".format(composite.shape))
            if(callback):
                callback(1, round(i / len(images) * 100));
        
        cv2.imwrite(outputPath, composite)
        if(callback):
            callback(1, 100);
