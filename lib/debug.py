

import os
import cv2 as cv


class Debug:
	
	colours = {
		'white':       (255,255,255),
		'red':         (0,0,255),
		'green':       (0,255,0),
		'blue':        (255,0,0),
		'lightblue':   (200,200,0),
		'lightpurple': (200,0,200),
		'yellow':      (0,200,200),
		'gray':        (150,150,150),
	}
	subpanel_colours = list(colours.values())[3:]  # white, red and green are used to display other infos
	
	
	def __init__(self, debug_dir):
		self.debug_dir = debug_dir
	
	
	def write_image(self, img, filename):
		if not self.debug_dir:
			return
		
		cv.imwrite(os.path.join(self.debug_dir, os.path.basename(filename)),img)
	
	
	def draw_contours(self, img, contours, contourSize, colour='auto'):
		if not self.debug_dir:
			return
		
		for i in range(len(contours)):
			if colour == 'auto':
				colour = Debug.subpanel_colours[i % len(Debug.subpanel_colours)]
			
			cv.drawContours(img, [contours[i]], 0, colour, contourSize)
	
	
	def draw_panels(self, img, panels, contourSize, colour):
		if not self.debug_dir:
			return
		
		img = img.copy()
		
		for p in panels:
			cv.rectangle(img, (p.x,p.y), (p.r,p.b), colour, contourSize)
		
		# + draw inner white border
		for p in panels:
			cv.rectangle(img, (p.x+contourSize,p.y+contourSize), (p.r-contourSize,p.b-contourSize), Debug.colours['white'], int(contourSize/2))
		
		return img
