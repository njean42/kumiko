

import os
import cv2 as cv


class Debug:
	
	def __init__(self, debug_dir):
		self.debug_dir = debug_dir
	
	
	def write_image(self, img, filename):
		if not self.debug_dir:
			return
		
		cv.imwrite(os.path.join(self.debug_dir, os.path.basename(filename)),img)
	
	
	subpanel_colours = [(0,255,0),(255,0,0),(200,200,0),(200,0,200),(0,200,200),(150,150,150)]
	
	def write_contours(self, img, contours, contourSize, colour='auto'):
		if not self.debug_dir:
			return
		
		for i in range(len(contours)):
			if colour == 'auto':
				colour = Debug.subpanel_colours[i % len(Debug.subpanel_colours)]
			
			cv.drawContours(img, [contours[i]], 0, colour, contourSize)
