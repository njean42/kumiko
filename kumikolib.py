

import os, json, sys, tempfile, requests
import cv2 as cv
import numpy as np
from urllib.parse import urlparse
from functools import reduce

from lib.panel import Panel
from lib.debug import Debug



class NotAnImageException (Exception):
	pass

class Kumiko:
	
	options = {}
	img = False
	
	def __init__(self,options={}):
		
		self.dbg = Debug('debug' in options and options['debug'])
		
		for o in ['progress','rtl']:
			self.options[o] = o in options and options[o]
		
		if self.options['rtl']:
			Panel.set_numbering('rtl')
		
		self.options['min_panel_size_ratio'] = Panel.DEFAULT_MIN_PANEL_SIZE_RATIO
		if 'min_panel_size_ratio' in options and options['min_panel_size_ratio']:
			self.options['min_panel_size_ratio'] = options['min_panel_size_ratio']
	
	
	def parse_url_list(self,urls):
		if self.options['progress']:
			print(len(urls),'files to download')
		
		tempdir = tempfile.TemporaryDirectory()
		i = 0
		nbdigits = len(str(len(urls)))
		for url in urls:
			filename = 'img'+('0' * nbdigits + str(i))[-nbdigits:]
			
			if self.options['progress']:
				print('\t',url, (' -> '+filename) if urls else '')
			
			i += 1
			parts = urlparse(url)
			if not parts.netloc or not parts.path:
				continue
			
			r = requests.get(url)
			with open(os.path.join(tempdir.name,filename), 'wb') as f:
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
			print(len(filenames),'files to cut panels for')
		
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
	
	
	def get_contours(self,gray,filename,bgcol):
		
		thresh = None
		contours = None
		
		# White background: values below 220 will be black, the rest white
		if bgcol == 'white':
			ret,thresh = cv.threshold(gray,220,255,cv.THRESH_BINARY_INV)
			contours, hierarchy = cv.findContours(thresh, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)[-2:]
		
		elif bgcol == 'black':
			# Black background: values above 25 will be black, the rest white
			ret,thresh = cv.threshold(gray,25,255,cv.THRESH_BINARY)
			contours, hierarchy = cv.findContours(thresh, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)[-2:]
		
		else:
			raise Exception('Fatal error, unknown background color: '+str(bgcol)) 
		
		self.dbg.add_image(thresh,'Thresholded image, supposed {} background'.format(bgcol))
		
		return contours
	
	
	def group_small_panels(self, panels, filename):
		g = 0
		groups = {}  # panel: groups for this panel
		for p1 in panels:
			if not p1.is_small():
				continue
			
			for p2 in panels:
				if p2 == p1 or not p2.is_small():
					continue
				
				if p2.is_close(p1):
					if not (p1 in groups): groups[p1] = set()
					if not (p2 in groups): groups[p2] = set()
					
					grps = groups[p1].union(groups[p2])
					use_group = g
					if len(grps) > 0:
						use_group = min(grps)
					else:
						g += 1
					
					groups[p1].add(use_group)
					groups[p2].add(use_group)
		
		panels = set(panels)
		for g in range(g):
			panels_in_group = {p:grps for (p,grps) in groups.items() if g in grps}  # "dictionary comprehension"
			merged_big_panel = reduce(Panel.merge, panels_in_group.keys())
			
			# add big panel and remove small ones
			if not merged_big_panel.is_small():
				panels.add(merged_big_panel)
				
				tmp_img = self.dbg.draw_panels(self.img, panels_in_group,    Debug.colours['lightblue'])
				tmp_img = self.dbg.draw_panels(tmp_img,  [merged_big_panel], Debug.colours['green'])
				self.dbg.add_image(tmp_img, 'Group small panels')
			
			panels = panels - panels_in_group.keys()
		
		panels = list(filter(lambda p: not p.is_small(), panels))  # also remove small panels that were not part of groups
		
		self.dbg.add_step('Group small panels', panels)
		
		return panels
	
	
	def split_panels(self,panels):
		new_panels = []
		old_panels = []
		for p in panels:
			new = p.split()
			if new != None:
				old_panels.append(p)
				new_panels += new
				
				self.dbg.draw_contours(self.img, list(map(lambda n: n.polygon, new)))
		
		for p in old_panels:
			panels.remove(p)
		panels += new_panels
		
		self.dbg.add_image(self.img, 'Split contours (shown as non-red contours)')
		self.dbg.add_step('Panels from split contours', panels)
		
		panels = list(filter(lambda p: not p.is_small(), panels))
		
		self.dbg.add_step('Exclude small panels', panels)
	
	
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
		
		self.dbg.add_step('Deoverlap panels', panels)
	
	
	# Merge every two panels where one contains the other
	def merge_panels(self, panels):
		panels_to_remove = []
		for i in range(len(panels)):
			for j in range(i+1,len(panels)):
				if panels[i].contains(panels[j]):
					panels_to_remove.append(j)
					panels[i] = Panel.merge(panels[i],panels[j])
				elif panels[j].contains(panels[i]):
					panels_to_remove.append(i)
					panels[j] = Panel.merge(panels[i],panels[j])
		
		for i in reversed(sorted(list(set(panels_to_remove)))):
			del panels[i]
		
		self.dbg.add_step('Merge panels', panels)
	
	
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
	
	
	# Expand panels to their neighbour's edge, or page boundaries
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
		
		self.dbg.add_step('Expand panels', panels)
	
	
	def parse_image(self,filename,url=None):
		self.img = cv.imread(filename)
		if not isinstance(self.img,np.ndarray) or self.img.size == 0:
			raise NotAnImageException('File {} is not an image'.format(filename))
		
		size = list(self.img.shape[:2])
		size.reverse()  # get a [width,height] list
		
		infos = {
			'filename': url if url else os.path.basename(filename),
			'size': size
		}
		Panel.img_size = size
		Panel.small_panel_ratio = self.options['min_panel_size_ratio']
		
		# get license for this file
		if os.path.isfile(filename+'.license'):
			with open(filename+'.license') as fh:
				try:
					infos['license'] = json.load(fh)
				except json.decoder.JSONDecodeError:
					print('License file {} is not a valid JSON file'.format(filename+'.license'))
					sys.exit(1)
		
		self.gray = cv.cvtColor(self.img,cv.COLOR_BGR2GRAY)
		self.dbg.add_image(self.gray,'Shades of gray')
		
		for bgcol in ['white','black']:
			res = self.parse_image_with_bgcol(infos.copy(),filename,bgcol,url)
			if len(res['panels']) > 1:
				return res
		
		return res
	
	
	def parse_image_with_bgcol(self,infos,filename,bgcol,url=None):
		
		contours = self.get_contours(self.gray,filename,bgcol)
		infos['background'] = bgcol
		self.dbg.infos = infos.copy()
		
		# Get (square) panels out of contours
		self.dbg.contourSize = int(sum(infos['size']) / 2 * 0.004)
		panels = []
		for contour in contours:
			arclength = cv.arcLength(contour,True)
			epsilon = 0.001 * arclength
			approx = cv.approxPolyDP(contour,epsilon,True)
			
			self.dbg.draw_contours(self.img, [approx], Debug.colours['red'])
			
			panels.append(Panel(polygon=approx))
		
		self.dbg.add_step('Initial state', [])
		self.dbg.add_image(self.img, 'Initial contours')
		self.dbg.add_step('Panels from initial contours', panels)
		
		# Group small panels that are close together, into bigger ones
		panels = self.group_small_panels(panels,filename)
		
		# See if panels can be cut into several (two non-consecutive points are close)
		self.split_panels(panels)
		
		# Merge panels that shouldn't have been split (speech bubble diving in a panel)
		self.merge_panels(panels)
		
		# splitting polygons may result in panels slightly overlapping, de-overlap them
		self.deoverlap_panels(panels)
		
		# re-filter out small panels
		panels = list(filter(lambda p: not p.is_small(), panels))
		self.dbg.add_step('Exclude small panels', panels)
		
		# get actual gutters before expanding panels
		actual_gutters = Kumiko.actual_gutters(panels)
		infos['gutters'] = [actual_gutters['x'],actual_gutters['y']]
		
		panels.sort()  # TODO: remove when panels expansion is smarter
		self.expand_panels(panels)
		
		if len(panels) == 0:
			panels.append( Panel([0,0,infos['size'][0],infos['size'][1]]) );
		
		# Number panels comics-wise (ltr/rtl)
		panels.sort()
		
		# Simplify panels back to lists (x,y,w,h)
		panels = list(map(lambda p: p.to_xywh(), panels))
		
		infos['panels'] = panels
		return infos
