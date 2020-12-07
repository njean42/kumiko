#!/usr/bin/env python


import os, json, sys
import cv2 as cv
import numpy as np

from lib.panel import Panel



class Kumiko:
	
	options = {}
	img = False
	
	def __init__(self,options={}):
		
		self.options['debug_dir'] = 'debug_dir' in options and options['debug_dir']
		self.options['progress']  = 'progress'  in options and options['progress']
		
		self.options['min_panel_size_ratio'] = 1/15
		if 'min_panel_size_ratio' in options and options['min_panel_size_ratio']:
			self.options['min_panel_size_ratio'] = options['min_panel_size_ratio']
	
	
	def parse_dir(self,directory):
		filenames = []
		for root, dirs, files in os.walk(directory):
			for filename in files:
				filenames.append(os.path.join(root,filename))
		filenames.sort()
		return self.parse_images(filenames)
	
	
	def parse_images(self,filenames=[]):
		infos = []
		
		if self.options['progress']:
			print(len(filenames),'files')
		
		for filename in filenames:
			if self.options['progress']:
				print("\t",filename)
			
			try:
				infos.append(self.parse_image(filename))
			except Exception:
				pass  # this file is not an image, will not be part of the results
		
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
		
		# A panel should have at least three edges
		if min(poly1len,poly2len) <= 2:
			return [polygon]
		
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
	
	
	def deoverlap_panels(self,panels):
		for i in range(len(panels)):
			for j in range(len(panels)):
				if panels[i] == panels[j]: continue
				opanel = panels[i].overlap_panel(panels[j])
				if not opanel:
					continue
				
				if opanel.w < opanel.h and panels[i].r == opanel.r:
					panels[i].r = opanel.x
					panels[j].x = opanel.r
					continue
				
				if opanel.w > opanel.h and panels[i].b == opanel.b:
					panels[i].b = opanel.y
					panels[j].y = opanel.b
					continue
	
	
	# Merge every two panels where one contains the other
	def merge_panels(self, panels):
		panels_to_remove = []
		for i in range(len(panels)):
			for j in range(i+1,len(panels)):
				if panels[i].contains(panels[j]):
					panels_to_remove.append(j)
				elif panels[j].contains(panels[i]):
					panels_to_remove.append(i)
		
		for i in reversed(sorted(list(set(panels_to_remove)))):
			del panels[i]
	
	
	# Find out actual gutters between panels
	def actual_gutters(panels,func=min):
		gutters_x = []
		gutters_y = []
		for p in panels:
			left_panel = p.find_left_panel(panels)
			if left_panel: gutters_x.append(p.x - left_panel.r)
			
			top_panel = p.find_top_panel(panels)
			if top_panel: gutters_y.append(p.y - top_panel.b)
		
		if not gutters_x: gutters_x = [1]
		if not gutters_y: gutters_y = [1]
		
		return {
			'x': func(gutters_x),
			'y': func(gutters_y),
			'r': -func(gutters_x),
			'b': -func(gutters_y)
		}
	
	
	# Expand panels to their neighbour's edge, or page frame
	def expand_panels(self, panels):
		gutters = Kumiko.actual_gutters(panels)
		for i in range(len(panels)):
			for d in ['x','y','r','b']: # expand in all four directions
				pcoords = {'x':panels[i].x, 'y':panels[i].y, 'r':panels[i].r, 'b':panels[i].b}
				
				newcoord = -1
				neighbour = panels[i].find_neighbour_panel(d,panels)
				if neighbour:
					# expand to that neighbour's edge (minus gutter)
					newcoord = getattr(neighbour,{'x':'r','r':'x','y':'b','b':'y'}[d]) + gutters[d]
				else:
					# expand to the furthest known edge (frame around all panels)
					min_panel = min(panels,key=lambda p: getattr(p,d)) if d in ['x','y'] else max(panels,key=lambda p: getattr(p,d))
					newcoord = getattr(min_panel,d)
				
				if newcoord != -1:
					if d in ['r','b'] and newcoord > getattr(panels[i],d) or d in ['x','y'] and newcoord < getattr(panels[i],d):
						setattr(panels[i],d,newcoord)
	
	
	def getGutterThreshold(size):
		return sum(size) / 2 / 20
	
	
	def parse_image(self,filename):
		img = cv.imread(filename)
		if not isinstance(img,np.ndarray) or img.size == 0:
			raise Exception('File {} is not an image'.format(filename))
		
		size = list(img.shape[:2])
		size.reverse()  # get a [width,height] list
		
		infos = {
			'filename': os.path.basename(filename),
			'size': size,
			'panels': []
		}
		
		# get license for this file
		if os.path.isfile(filename+'.license'):
			with open(filename+'.license') as fh:
				try:
					infos['license'] = json.load(fh)
				except json.decoder.JSONDecodeError:
					print('License file {} is not a valid JSON file'.format(filename+'.license'))
					sys.exit(1)
		
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
			
			i = -1
			for p in polygons:
				i += 1
				x,y,w,h = cv.boundingRect(p)
				
				# exclude very small panels
				if w < infos['size'][0] * self.options['min_panel_size_ratio'] or h < infos['size'][1] * self.options['min_panel_size_ratio']:
					continue
				
				if self.options['debug_dir']:
					contourSize = int(sum(infos['size']) / 2 * 0.004)
					if len(polygons) == 1:
						cv.drawContours(img, [p], 0, (0,0,255), contourSize)
					else:
						cv.drawContours(img, [p], 0, [(0,255,0),(255,0,0)][i], contourSize)
				
				panel = Panel([x,y,w,h], self.gutterThreshold)
				infos['panels'].append(panel)
		
		# merge panels that shouldn't have been split (speech bubble diving in a panel)
		self.merge_panels(infos['panels'])
		
		# cutting polygons may result in panels slightly overlapping, de-overlap them
		self.deoverlap_panels(infos['panels'])
		
		infos['panels'].sort()  # TODO: remove
		self.expand_panels(infos['panels'])
		
		if len(infos['panels']) == 0:
			infos['panels'].append( Panel([0,0,infos['size'][0],infos['size'][1]], self.gutterThreshold) );
		
		# Number infos['panels'] comics-wise (left to right for now)
		infos['panels'].sort()
		
		# Simplify panels back to lists (x,y,w,h)
		infos['panels'] = list(map(lambda p: p.to_xywh(), infos['panels']))
		
		# write panel numbers on debug image
		if (self.options['debug_dir']):
			cv.imwrite(os.path.join(self.options['debug_dir'],os.path.basename(filename)+'-contours.jpg'),img)
		
		return infos
