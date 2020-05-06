#!/usr/bin/env python
import os
import sys
import cv2 as cv


def cmp_to_key(mycmp):
    'Convert a cmp= function into a key= function'
    class K:
        def __init__(self, obj, *args):
            self.obj = obj

        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0

        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0

        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0

        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0

        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0

        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K


class Kumiko:
	
	options = {}
	img = False
	
	def __init__(self,options={}):
		
		if 'debug' in options:
			self.options['debug'] = options['debug']
		else:
			self.options['debug'] = False
		
		if 'reldir' in options:
			self.options['reldir'] = options['reldir']
		else:
			self.options['reldir'] = os.getcwd()
	
	
	def read_image(self,filename):
		return cv.imread(filename)
	
	
	def parse_dir(self,directory):
		filenames = []
		for root, dirs, files in os.walk(directory):
			for filename in files:
				filenames.append(os.path.join(root,filename))
		filenames.sort()
		#filenames = filenames[0:10]
		return self.parse_images(filenames)
	
	
	def parse_images(self,filenames=[]):
		infos = []
		for filename in filenames:
			infos.append(self.parse_image(filename))
		return infos
	
	
	def parse_image(self,filename):
		img = self.read_image(filename)
		# TODO: handle error
		
		size = list(img.shape[:2])
		size.reverse()  # get a [width,height] list
		
		infos = {
			'filename': os.path.relpath(filename,self.options['reldir']),
			'size': size,
			'panels': []
		}
		
		gray = cv.cvtColor(img,cv.COLOR_BGR2GRAY)
		
		tmin = 220
		tmax = 255
		ret,thresh = cv.threshold(gray,tmin,tmax,cv.THRESH_BINARY_INV)
		
		contours = cv.findContours(thresh, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
		contours, hierarchy = cv.findContours(thresh, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)[-2:]
		
		# Get (square) panels out of contours
		for contour in contours:
			
			arclength = cv.arcLength(contour,True)
			
			epsilon = 0.01 * arclength
			approx = cv.approxPolyDP(contour,epsilon,True)
			
			x,y,w,h = cv.boundingRect(approx)
			
			# exclude very small panels
			if w < infos['size'][0]/15 or h < infos['size'][1]/15:
				continue
			
			contourSize = int(sum(infos['size']) / 2 * 0.004)
			cv.drawContours(img, [approx], 0, (0,0,255), contourSize)
			
			panel = [x,y,w,h]
			infos['panels'].append(panel)
		
		if len(infos['panels']) == 0:
			infos['panels'].append([0,0,infos['size'][0],infos['size'][1]]);
		
		for panel in infos['panels']:
			x,y,w,h = panel
			panel = {
				'x': x,
				'y': y,
				'w': w,
				'h': h
			}
		
		# Number infos['panels'] comics-wise (left to right for now)
		self.gutterThreshold = sum(infos['size']) / 2 / 20
		infos['panels'].sort(cmp=self.sort_panels)
		
		# write panel numbers on debug img
		fontRatio = sum(infos['size']) / 2 / 400
		font      = cv.FONT_HERSHEY_SIMPLEX
		fontScale = 1 * fontRatio
		fontColor = (0,0,255)
		lineType  = 2
		n = 0
		for panel in infos['panels']:
			n += 1
			position  = ( int(panel[0]+panel[2]/2), int(panel[1]+panel[3]/2))
			cv.putText(img,str(n),position,font,fontScale,fontColor,lineType)
		
		if (self.options['debug']):
			cv.imwrite(os.path.join('debug',os.path.basename(filename)+'-040-contours-numbers.jpg'),img)
		
		return infos
		
		
	def sort_panels (self,p1,p2):
		[p1x,p1y,p1w,p1h] = p1
		[p2x,p2y,p2w,p2h] = p2
		
		p1b = p1y+p1h # p1's bottom
		p2b = p2y+p2h # p2's bottom
		p1r = p1x+p1w # p1's right side
		p2r = p2x+p2w # p2's right side
		
		# p1 is above p2
		if p2y >= p1b - self.gutterThreshold and p2y >= p1y - self.gutterThreshold:
			return -1
		
		# p1 is below p2
		if p1y >= p2b - self.gutterThreshold and p1y >= p2y - self.gutterThreshold:
			return 1
		
		# p1 is left from p2
		if p2x >= p1r - self.gutterThreshold and p2x >= p1x - self.gutterThreshold:
			return -1
		
		# p1 is right from p2
		if p1x >= p2r - self.gutterThreshold and p1x >= p2x - self.gutterThreshold:
			return 1
		
		return 0  # should we really fall into this case?
