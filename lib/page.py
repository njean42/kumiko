

import os, json, sys
import time
import cv2 as cv
import numpy as np

from lib.panel import Panel
from lib.debug import Debug



class NotAnImageException (Exception):
	pass

class Page:

	DEFAULT_MIN_PANEL_SIZE_RATIO  = 1/15

	def get_infos(self):
		actual_gutters = self.actual_gutters()

		return {
			'filename': self.url if self.url else os.path.basename(self.filename),
			'size': self.img_size,
			'background': self.background_color,
			'numbering': self.numbering,
			'gutters': [actual_gutters['x'],actual_gutters['y']],
			'license': self.license,
			'panels': list(map(lambda p: p.to_xywh(), self.panels)),
			'processing_time': self.processing_time,
		}

	def __init__(self, filename, numbering=None, debug=False, url=None, min_panel_size_ratio=None):
		self.filename = filename
		self.panels = []
		self.background_color = '?'

		self.processing_time = None
		t1 = time.time_ns()

		self.img = cv.imread(filename)
		if not isinstance(self.img,np.ndarray) or self.img.size == 0:
			raise NotAnImageException(f"File {filename} is not an image")

		self.numbering = numbering or "ltr"
		if not (numbering in ['ltr','rtl']):
			raise Exception('Fatal error, unknown numbering: '+str(numbering))

		self.small_panel_ratio = min_panel_size_ratio or Page.DEFAULT_MIN_PANEL_SIZE_RATIO
		self.url = url

		self.img_size = list(self.img.shape[:2])
		self.img_size.reverse()  # get a [width,height] list

		# get license for this file
		self.license = None
		if os.path.isfile(filename+'.license'):
			with open(filename+'.license') as fh:
				try:
					self.license = json.load(fh)
				except json.decoder.JSONDecodeError:
					print('License file {} is not a valid JSON file'.format(filename+'.license'))
					sys.exit(1)

		Debug.add_step('Initial state', self.get_infos())
		Debug.add_image(self.img,'Input image')

		self.gray = cv.cvtColor(self.img,cv.COLOR_BGR2GRAY)
		Debug.add_image(self.gray,'Shades of gray')

		for bgcol in ['white','black']:
			self.parse_image_with_bgcol(bgcol)
			if len(self.panels) > 1:
				self.processing_time = int((time.time_ns() - t1) / 10**7) / 100
				return


	def parse_image_with_bgcol(self, bgcol):

		contours = self.get_contours(self.gray,bgcol)
		self.background_color = bgcol

		# Get (square) panels out of contours
		Debug.contourSize = int(sum(self.img_size) / 2 * 0.004)
		self.panels = []
		for contour in contours:
			arclength = cv.arcLength(contour,True)
			epsilon = 0.001 * arclength
			approx = cv.approxPolyDP(contour,epsilon,True)

			Debug.draw_contours(self.img, [approx], Debug.colours['red'])

			self.panels.append(Panel(page=self, polygon=approx))

		Debug.add_image(self.img, 'Initial contours')
		Debug.add_step('Panels from initial contours', self.get_infos())

		# Group small panels that are close together, into bigger ones
		self.group_small_panels()

		# See if panels can be cut into several (two non-consecutive points are close)
		self.split_panels()

		# Merge panels that shouldn't have been split (speech bubble diving in a panel)
		self.merge_panels()

		# splitting polygons may result in panels slightly overlapping, de-overlap them
		self.deoverlap_panels()

		# re-filter out small panels
		self.panels = list(filter(lambda p: not p.is_small(), self.panels))
		Debug.add_step('Exclude small panels', self.get_infos())

		self.panels.sort()  # TODO: move this below before panels sort-fix, when panels expansion is smarter
		self.expand_panels()

		if len(self.panels) == 0:
			self.panels.append( Panel(page=self, xywh=[0,0,self.img_size[0],self.img_size[1]]) );

		# Fix panels simple sorting (issue #12)
		changes = 1
		while(changes):
			changes = 0
			for i, p in enumerate(self.panels):
				neighbours_before = [p.find_top_panel()]
				neighbours_before.append(p.find_right_panel() if self.numbering == "rtl" else p.find_left_panel())
				for neighbour in neighbours_before:
					if neighbour is None:
						continue
					neighbour_pos = self.panels.index(neighbour)
					if i < neighbour_pos:
						changes += 1
						self.panels.insert(neighbour_pos, self.panels.pop(i))
						break
				if changes > 0:
					break  # start a new whole loop with reordered panels

		Debug.add_step('Numbering fixed', self.get_infos())


	def get_contours(self,gray,bgcol):

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

		Debug.add_image(thresh,'Thresholded image, supposed {} background'.format(bgcol))

		return contours


	def group_small_panels(self):
		i = 0
		panels_to_add = []
		while i < len(self.panels):
			p1 = self.panels[i]

			if not p1.is_small():
				i += 1
				continue

			# build up a group of panels that are close to one another
			big_panel = p1
			grouped = [i]

			for j in range(i+1, len(self.panels)):
				p2 = self.panels[j]

				if j == i or not p2.is_small():
					continue

				if p2.is_close(big_panel):
					grouped.append(j)

					# build up bigger panel for current group
					big_panel = Panel.merge(self,big_panel,p2)

			if len(grouped) <= 1:
				del self.panels[i]
				continue  # continue from same index i, which is a new panel (previous panel at index i has just been removed)

			else:
				# add new grouped panel, if not small
				if not big_panel.is_small():
					panels_to_add.append(big_panel)

					tmp_img = Debug.draw_panels(self.img, list(map(lambda k: self.panels[k], grouped)), Debug.colours['lightblue'])
					tmp_img = Debug.draw_panels(tmp_img,  [big_panel], Debug.colours['green'])
					Debug.add_image(tmp_img, 'Group small panels')

				# remove all panels in group
				for k in reversed(grouped):
					del self.panels[k]

			i += 1

		for p in panels_to_add:
			self.panels.append(p)

		Debug.add_step('Group small panels', self.get_infos())


	def split_panels(self):
		new_panels = []
		old_panels = []
		for p in self.panels:
			new = p.split()
			if new != None:
				old_panels.append(p)
				new_panels += new

				Debug.draw_contours(self.img, list(map(lambda n: n.polygon, new)))

		for p in old_panels:
			self.panels.remove(p)
		self.panels += new_panels

		Debug.add_image(self.img, 'Split contours (shown as non-red contours)')
		Debug.add_step('Panels from split contours', self.get_infos())

		self.panels = list(filter(lambda p: not p.is_small(), self.panels))

		Debug.add_step('Exclude small panels', self.get_infos())


	def deoverlap_panels(self):
		for p1 in self.panels:
			for p2 in self.panels:
				if p1 == p2: continue
				opanel = p1.overlap_panel(p2)
				if not opanel:
					continue

				if opanel.w < opanel.h and p1.r == opanel.r:
					p1.r = opanel.x
					p2.x = opanel.r
					continue

				if opanel.w > opanel.h and p1.b == opanel.b:
					p1.b = opanel.y
					p2.y = opanel.b
					continue

		Debug.add_step('Deoverlap panels', self.get_infos())


	# Merge every two panels where one contains the other
	def merge_panels(self):
		panels_to_remove = []
		for i in range(len(self.panels)):
			for j in range(i+1,len(self.panels)):
				if self.panels[i].contains(self.panels[j]):
					panels_to_remove.append(j)
					self.panels[i] = Panel.merge(self,self.panels[i],self.panels[j])
				elif self.panels[j].contains(self.panels[i]):
					panels_to_remove.append(i)
					self.panels[j] = Panel.merge(self,self.panels[i],self.panels[j])

		for i in reversed(sorted(list(set(panels_to_remove)))):
			del self.panels[i]

		Debug.add_step('Merge panels', self.get_infos())


	# Find out actual gutters between panels
	def actual_gutters(self,func=min):
		gutters_x = []
		gutters_y = []
		for p in self.panels:
			left_panel = p.find_left_panel()
			if left_panel: gutters_x.append(p.x - left_panel.r)

			top_panel = p.find_top_panel()
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
	def expand_panels(self):
		gutters = self.actual_gutters()
		for p in self.panels:
			for d in ['x','y','r','b']: # expand in all four directions
				pcoords = {'x':p.x, 'y':p.y, 'r':p.r, 'b':p.b}

				newcoord = -1
				neighbour = p.find_neighbour_panel(d)
				if neighbour:
					# expand to that neighbour's edge (minus gutter)
					newcoord = getattr(neighbour,{'x':'r','r':'x','y':'b','b':'y'}[d]) + gutters[d]
				else:
					# expand to the furthest known edge (frame around all panels)
					min_panel = min(self.panels,key=lambda p: getattr(p,d)) if d in ['x','y'] else max(self.panels,key=lambda p: getattr(p,d))
					newcoord = getattr(min_panel,d)

				if newcoord != -1:
					if d in ['r','b'] and newcoord > getattr(p,d) or d in ['x','y'] and newcoord < getattr(p,d):
						setattr(p,d,newcoord)

		Debug.add_step('Expand panels', self.get_infos())
