#!/usr/bin/env python



import os
import cv2 as cv
import numpy as np



class Kumiko:
	
	options = {}
	img = False
	
	def __init__(self,options={}):
		
		self.options['debug_dir'] = 'debug_dir' in options and options['debug_dir']
		self.options['progress']  = 'progress'  in options and options['progress']
		
		self.options['reldir'] = options['reldir'] if 'reldir' in options else os.getcwd()
		
		self.options['min_panel_size_ratio'] = 1/15
		if 'min_panel_size_ratio' in options and options['min_panel_size_ratio']:
			self.options['min_panel_size_ratio'] = options['min_panel_size_ratio']
	
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
		
		if self.options['progress']:
			print(len(filenames),'files')
		
		for filename in filenames:
			
			if self.options['progress']:
				print("\t",filename)
			
			infos.append(self.parse_image(filename))
		
		return infos
	
	
	def dots_are_close(self,dot1,dot2):
		max_dist = self.gutterThreshold * 2
		return abs(dot1[0]-dot2[0]) < max_dist and abs(dot1[1]-dot2[1]) < max_dist
	
	
	def split_polygon(self,polygon):
		
		close_dots = []
		for i in range(len(polygon)-1):
			all_close = True
			for j in range(i+1,len(polygon)):
				dot1 = polygon[i][0]
				dot2 = polygon[j][0]
				
				if self.dots_are_close(dot1,dot2):
					if not all_close:	
						close_dots.append([i,j])
				else:
					all_close = False
		
		if len(close_dots) == 0:
			return [polygon]
		
		# take the dots that shouldn't be close, i.e. those with the most hops in between (other dots)
		best_cut = max(close_dots, key=lambda i: abs(i[1]-i[0]) % (len(polygon)-1))
		# NOTE: The first (i=0) and last dots are connected. There's at most len(polygon)-1 hops between two dots
		
		poly1len = len(polygon) - best_cut[1] + best_cut[0]
		poly2len = best_cut[1] - best_cut[0]
		poly1 = np.zeros(shape=(poly1len,1,2), dtype=int)
		poly2 = np.zeros(shape=(poly2len,1,2), dtype=int)
		
		x = y = 0
		for i in range(len(polygon)):
			if i <= best_cut[0] or i > best_cut[1]:
				poly1[x][0] = polygon[i]
				x += 1
			else:
				poly2[y][0] = polygon[i]
				y += 1
		
		return [poly1,poly2]  # TODO: recurse?
	
	
	def merge_panels(self, panels):
		panels_to_remove = []
		for i in range(len(panels)):
			for j in range(i+1,len(panels)):
				if panels[i].contains(panels[j]):
					panels_to_remove.append(j)
				elif panels[j].contains(panels[i]):
					panels_to_remove.append(i)
		
		for i in reversed(panels_to_remove):
			del panels[i]
	
	
	def getGutterThreshold(size):
		return sum(size) / 2 / 20
	
	
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
		
		self.gutterThreshold = Kumiko.getGutterThreshold(infos['size'])
		
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
			
			# See if this panel can be cut into several (two non-consecutive points are close)
			polygons = self.split_polygon(approx)
			
			for p in polygons:
				x,y,w,h = cv.boundingRect(p)
				
				# exclude very small panels
				if w < infos['size'][0] * self.options['min_panel_size_ratio'] or h < infos['size'][1] * self.options['min_panel_size_ratio']:
					continue
				
				contourSize = int(sum(infos['size']) / 2 * 0.004)
				cv.drawContours(img, [p], 0, (0,0,255), contourSize)
				
				panel = Panel([x,y,w,h], self.gutterThreshold)
				infos['panels'].append(panel)
		
		# Merge every two panels where one contains the other
		self.merge_panels(infos['panels'])
		
		if len(infos['panels']) == 0:
			infos['panels'].append( Panel([0,0,infos['size'][0],infos['size'][1]], self.gutterThreshold) );
		
		# Number infos['panels'] comics-wise (left to right for now)
		infos['panels'].sort()
		
		# Simplify panels back to lists (x,y,w,h)
		infos['panels'] = list(map(lambda p: p.toarray(), infos['panels']))
		
		# write panel numbers on debug image
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
		
		if (self.options['debug_dir']):
			cv.imwrite(os.path.join(self.options['debug_dir'],os.path.basename(filename)+'-contours.jpg'),img)
		
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
		return abs(self.x-other.x) < self.gutterThreshold and abs(self.y == other.y) < self.gutterThreshold and abs(self.r == other.r) < self.gutterThreshold and abs(self.b == other.b) < self.gutterThreshold
	
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
	
	def area(self):
		return self.w * self.h
	
	def __str__(self):
		return "[[{0},{1}],[{2},{3}],[{4},{5}],[{6},{7}]]".format(self.x,self.y, self.r,self.y, self.r,self.b, self.x,self.b)
	
	# returns an overlapping percentage
	def contains(self,other):
		if self.x > other.r or other.x > self.r:  # panels are left and right from one another
			return 0
		if self.y > other.b or other.y > self.b:  # panels are above and below one another
			return 0
		
		# if we're here, panels overlap at least a bit
		x = max(self.x,other.x)
		y = max(self.y,other.y)
		r = min(self.r,other.r)
		b = min(self.b,other.b)
		
		overlap_panel = Panel([x,y,r-x,b-y], self.gutterThreshold)
		
		# panels overlap if the overlapping area is more than 75% of the smallest one's area
		return overlap_panel.area() / other.area() > 0.75
