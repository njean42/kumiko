#!/usr/bin/env python



import os
import cv2 as cv



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
		
		self.gutterThreshold = sum(infos['size']) / 2 / 20
		
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
			
			panel = Panel([x,y,w,h], self.gutterThreshold)
			infos['panels'].append(panel)
		
		if len(infos['panels']) == 0:
			infos['panels'].append( Panel([0,0,infos['size'][0],infos['size'][1]], self.gutterThreshold) );
		
		# Number infos['panels'] comics-wise (left to right for now)
		infos['panels'].sort()
		
		# Simplify panels back to lists (x,y,w,h)
		infos['panels'] = list(map(lambda p: p.toarray(), infos['panels']))
		
		# write panel numbers on debug img
		fontRatio = sum(infos['size']) / 2 / 400
		font      = cv.FONT_HERSHEY_SIMPLEX
		fontScale = 1 * fontRatio
		fontColor = (0,0,255)
		lineType  = 5
		n = 0
		for panel in infos['panels']:
			n += 1
			position  = ( int(panel[0]+panel[2]/2), int(panel[1]+panel[3]/2))
			cv.putText(img,str(n),position,font,fontScale,fontColor,lineType)
		
		if (self.options['debug']):
			cv.imwrite(os.path.join('debug',os.path.basename(filename)+'-040-contours-numbers.jpg'),img)
		
		return infos


class Panel:
	def __init__(self, xywh, gutterThreshold):
		[self.x, self.y, self.w, self.h] = xywh
		self.b = self.y + self.h # panel's bottom
		self.r = self.x + self.w # panel's right side
		self.gutterThreshold = gutterThreshold
	
	def toarray(self):
		return [self.x, self.y, self.w, self.h]
	
	def __eq__(self, other):
		return self.x == other.x and self.y == other.y and self.w == other.w and self.h == other.h  # TODO: include gutterThreshold
	
	def __lt__(self, other):
		# panel is above other
		if other.y >= self.b - self.gutterThreshold and other.y >= self.y - self.gutterThreshold:
			return True
		
		# panel is below other
		if self.y >= other.b - self.gutterThreshold and self.y >= other.y - self.gutterThreshold:
			return False
		
		# panel is left from other
		if other.x >= self.r - self.gutterThreshold and other.x >= self.x - self.gutterThreshold:
			return True
		
		# panel is right from other
		if self.x >= other.r - self.gutterThreshold and self.x >= other.x - self.gutterThreshold:
			return False
		
		return True  # should not happen, TODO: raise an exception?
	
	def __le__(self, other):
		return self.__lt__(other)
	
	def __gt__(self, other):
		return not self.__lt__(other)
	
	def __ge__(self, other):
		return self.__gt__(other)
