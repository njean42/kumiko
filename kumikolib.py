#!/usr/bin/env python


import os, json, sys, tempfile, requests
import cv2 as cv
import numpy as np
from urllib.parse import urlparse

from lib.panel import Panel



class NotAnImageException (Exception):
	pass

class Kumiko:
	
	options = {}
	img = False
	
	def __init__(self,options={}):
		
		self.options['debug_dir'] = 'debug_dir' in options and options['debug_dir']
		self.options['progress']  = 'progress'  in options and options['progress']
		
		self.options['min_panel_size_ratio'] = 1/15
		if 'min_panel_size_ratio' in options and options['min_panel_size_ratio']:
			self.options['min_panel_size_ratio'] = options['min_panel_size_ratio']
	
	
	def parse_url_list(self,urls):
		tempdir = tempfile.TemporaryDirectory()
		i = 0
		for url in urls:
			i += 1
			parts = urlparse(url)
			if not parts.netloc or not parts.path:
				continue
			
			r = requests.get(url)
			with open(os.path.join(tempdir.name,'img'+str(i)), 'wb') as f:
				f.write(r.content)
		
		return self.parse_dir(tempdir.name,urls=urls)
	
	
	def parse_dir(self,directory,urls=None):
		filenames = []
		for filename in os.scandir(directory):
			filenames.append(filename.path)
		return self.parse_images(filenames,urls)
	
	
	def parse_images(self,filenames=[],urls=None):
		infos = []
		
		if self.options['progress']:
			print(len(filenames),'files')
		
		i = -1
		for filename in sorted(filenames):
			i += 1
			if self.options['progress']:
				print("\t",urls[i] if urls else filename)
			
			try:
				infos.append(self.parse_image(filename,url=urls[i] if urls else None))
			except NotAnImageException:
				print("Not an image, will be ignored: {}".format(filename), file=sys.stderr) 
				pass  # this file is not an image, will not be part of the results
		
		return infos
	
	
	subpanel_colours = [(0,255,0),(255,0,0),(200,200,0),(200,0,200),(0,200,200),(150,150,150)]
	def split_panels(self,panels,img,contourSize):
		new_panels = []
		old_panels = []
		for p in panels:
			new = p.split()
			if new != None:
				old_panels.append(p)
				new_panels += new
				
				if self.options['debug_dir']:
					for i in range(len(new)):
						cv.drawContours(img, [new[n].polygon], 0, self.subpanel_colours[i % len(self.subpanel_colours)], contourSize)
		
		for p in old_panels:
			panels.remove(p)
		panels += new_panels
	
	
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
	
	
	def parse_image(self,filename,url=None):
		img = cv.imread(filename)
		if not isinstance(img,np.ndarray) or img.size == 0:
			raise NotAnImageException('File {} is not an image'.format(filename))
		
		size = list(img.shape[:2])
		size.reverse()  # get a [width,height] list
		
		infos = {
			'filename': url if url else os.path.basename(filename),
			'size': size
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
		contourSize = int(sum(infos['size']) / 2 * 0.004)
		panels = []
		for contour in contours:
			arclength = cv.arcLength(contour,True)
			epsilon = 0.001 * arclength
			approx = cv.approxPolyDP(contour,epsilon,True)
			
			
			panel = Panel(polygon=approx)
			
			# exclude very small panels
			if panel.w < infos['size'][0] * self.options['min_panel_size_ratio'] or panel.h < infos['size'][1] * self.options['min_panel_size_ratio']:
				continue
			
			if self.options['debug_dir']:
				cv.drawContours(img, [approx], 0, (0,0,255), contourSize)
			
			panels.append(Panel(polygon=approx))
		
		# See if panels can be cut into several (two non-consecutive points are close)
		self.split_panels(panels,img,contourSize)
		
		# Merge panels that shouldn't have been split (speech bubble diving in a panel)
		self.merge_panels(panels)
		
		# splitting polygons may result in panels slightly overlapping, de-overlap them
		self.deoverlap_panels(panels)
		
		# get actual gutters before expanding panels
		actual_gutters = Kumiko.actual_gutters(panels)
		infos['gutters'] = [actual_gutters['x'],actual_gutters['y']]
		
		panels.sort()  # TODO: remove
		self.expand_panels(panels)
		
		if len(panels) == 0:
			panels.append( Panel([0,0,infos['size'][0],infos['size'][1]]) );
		
		# Number panels comics-wise (left to right for now)
		panels.sort()
		
		# Simplify panels back to lists (x,y,w,h)
		panels = list(map(lambda p: p.to_xywh(), panels))
		
		infos['panels'] = panels
		
		# write panel numbers on debug image
		if (self.options['debug_dir']):
			cv.imwrite(os.path.join(self.options['debug_dir'],os.path.basename(filename)+'-contours.jpg'),img)
		
		return infos
