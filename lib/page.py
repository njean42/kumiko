import math
import os
import json
import sys
import time
import cv2 as cv
import numpy as np

from lib.panel import Panel
from lib.debug import Debug


class NotAnImageException(Exception):
	pass


class Page:

	DEFAULT_MIN_PANEL_SIZE_RATIO = 1 / 15

	def get_infos(self):
		actual_gutters = self.actual_gutters()

		return {
			'filename': self.url if self.url else os.path.basename(self.filename),
			'size': self.img_size,
			'numbering': self.numbering,
			'gutters': [actual_gutters['x'], actual_gutters['y']],
			'license': self.license,
			'panels': list(map(lambda p: p.to_xywh(), self.panels)),
			'processing_time': self.processing_time
		}

	def __init__(self, filename, numbering = None, debug = False, url = None, min_panel_size_ratio = None):
		self.filename = filename
		self.panels = []
		self.background_color = '?'

		self.processing_time = None
		t1 = time.time_ns()

		self.img = cv.imread(filename)
		if not isinstance(self.img, np.ndarray) or self.img.size == 0:
			raise NotAnImageException(f"File {filename} is not an image")

		self.numbering = numbering or "ltr"
		if not (numbering in ['ltr', 'rtl']):
			raise Exception('Fatal error, unknown numbering: ' + str(numbering))

		self.small_panel_ratio = min_panel_size_ratio or Page.DEFAULT_MIN_PANEL_SIZE_RATIO
		self.url = url

		self.img_size = list(self.img.shape[:2])
		self.img_size.reverse()  # get a [width,height] list

		Debug.contourSize = 3

		# get license for this file
		self.license = None
		if os.path.isfile(filename + '.license'):
			with open(filename + '.license', encoding = "utf8") as fh:
				try:
					self.license = json.load(fh)
				except json.decoder.JSONDecodeError:
					print(f"License file {filename+'.license'} is not a valid JSON file")
					sys.exit(1)

		Debug.set_base_img(self.img)

		Debug.add_step('Initial state', self.get_infos())
		Debug.add_image('Input image')

		self.gray = cv.cvtColor(self.img, cv.COLOR_BGR2GRAY)
		Debug.add_image('Shades of gray', img = self.gray)

		# https://docs.opencv.org/3.4/d2/d2c/tutorial_sobel_derivatives.html
		ddepth = cv.CV_16S
		grad_x = cv.Sobel(self.gray, ddepth, 1, 0, ksize = 3, scale = 1, delta = 0, borderType = cv.BORDER_DEFAULT)
		# Gradient-Y
		# grad_y = cv.Scharr(self.gray,ddepth,0,1)
		grad_y = cv.Sobel(self.gray, ddepth, 0, 1, ksize = 3, scale = 1, delta = 0, borderType = cv.BORDER_DEFAULT)

		abs_grad_x = cv.convertScaleAbs(grad_x)
		abs_grad_y = cv.convertScaleAbs(grad_y)

		self.sobel = cv.addWeighted(abs_grad_x, 0.5, abs_grad_y, 0.5, 0)
		Debug.add_image('Sobel filter applied', img = self.sobel)

		self.get_contours()
		self.get_segments()
		self.get_initial_panels()
		self.group_small_panels()
		self.split_panels()
		self.exclude_small_panels()
		self.merge_panels()
		self.deoverlap_panels()
		self.exclude_small_panels()

		self.panels.sort()  # TODO: move this below before panels sort-fix, when panels expansion is smarter
		self.expand_panels()

		if len(self.panels) == 0:
			self.panels.append(Panel(page = self, xywh = [0, 0, self.img_size[0], self.img_size[1]]))

		self.fix_panels_numbering()

		self.processing_time = int((time.time_ns() - t1) / 10**7) / 100

	def get_contours(self):
		# Black background: values above 100 will be black, the rest white
		_, thresh = cv.threshold(self.sobel, 100, 255, cv.THRESH_BINARY)
		self.contours, _ = cv.findContours(thresh, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)[-2:]

		Debug.add_image("Thresholded image", img=thresh)

	def get_segments(self):
		self.segments = []

		seg = np.copy(self.img)
		lsd = cv.createLineSegmentDetector(0)
		dlines = lsd.detect(self.gray)
		for dline in dlines[0]:
			x0 = int(round(dline[0][0]))
			y0 = int(round(dline[0][1]))
			x1 = int(round(dline[0][2]))
			y1 = int(round(dline[0][3]))

			a = x0 - x1
			b = y0 - y1
			dist = math.sqrt(a**2 + b**2)
			if dist >= 100:
				self.segments.append([[x0,y0],[x1,y1]])
				Debug.draw_line((x0, y0), (x1,y1), Debug.colours['green'])

		Debug.add_image("Segment Detector")

	# Get (square) panels out of initial contours
	def get_initial_panels(self):
		self.panels = []
		for contour in self.contours:
			arclength = cv.arcLength(contour, True)
			epsilon = 0.001 * arclength
			approx = cv.approxPolyDP(contour, epsilon, True)

			panel = Panel(page = self, polygon = approx)
			if panel.is_very_small():
				continue

			Debug.draw_contours([approx], Debug.colours['red'])

			self.panels.append(panel)

		Debug.add_image('Initial contours')
		Debug.add_step('Panels from initial contours', self.get_infos())

	# Group small panels that are close together, into bigger ones
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

			for j in range(i + 1, len(self.panels)):
				p2 = self.panels[j]

				if j == i or not p2.is_small():
					continue

				if p2.is_close(big_panel):
					grouped.append(j)

					# build up bigger panel for current group
					big_panel = big_panel.group_with(p2)

			if len(grouped) <= 1:
				del self.panels[i]
				continue  # continue from same index i, which is a new panel (previous panel at index i has just been removed)

			else:
				# add new grouped panel, if not small
				if not big_panel.is_small():
					panels_to_add.append(big_panel)

					Debug.draw_panels(list(map(lambda k: self.panels[k], grouped)), Debug.colours['lightblue'])
					Debug.draw_panels([big_panel], Debug.colours['green'])
					Debug.add_image('Group small panels')

				# remove all panels in group
				for k in reversed(grouped):
					del self.panels[k]

			i += 1

		for p in panels_to_add:
			self.panels.append(p)

		Debug.add_step('Group small panels', self.get_infos())

	# See if panels can be cut into several (two non-consecutive points are close)
	def split_panels(self):
		did_split = True
		t1 = None
		while did_split:
			self.merge_panels()

			if t1:
				print(f"took {(time.time_ns() - t1) / 10**9} seconds")
			t1 = time.time_ns()

			did_split = False
			for p in sorted(self.panels, key=lambda p: p.area(), reverse=True):
				new = p.split()
				if new is not None:
					did_split = True
					self.panels.remove(p)
					self.panels += new

					print(f"panel {p} was split into {new[0]} and {new[1]}")

					Debug.draw_contours(list(map(lambda n: n.polygon, new)), Debug.colours['blue'])
					break

		Debug.add_image('Split contours (blue contours, green polygon dots, purple nearby dots)')
		Debug.add_step('Panels from split contours', self.get_infos())

	# def dot_on_edge_of_panels(self, dot, max_gutter):
	# 	on_panels = set()
	# 	for p in self.panels:
	# 		# NOTE: this only works for vertical and horizontal gutters
	# 		if any([
	# 			abs(dot[0] - p.x) < max_gutter or abs(dot[0] - p.r) < max_gutter,
	# 			abs(dot[1] - p.y) < max_gutter or abs(dot[1] - p.b) < max_gutter,
	# 			]):
	# 			# print(f"dot {dot} is on panel {p.x}x{p.y}")
	# 			on_panels.add(p)
 #
	# 	return on_panels

	def exclude_small_panels(self):
		self.panels = list(filter(lambda p: not p.is_small(), self.panels))

		Debug.add_step('Exclude small panels', self.get_infos())

	# Splitting polygons may result in panels slightly overlapping, de-overlap them
	def deoverlap_panels(self):
		for p1 in self.panels:
			for p2 in self.panels:
				if p1 == p2:
					continue

				opanel = p1.overlap_panel(p2)
				if not opanel:
					continue

				if opanel.w() < opanel.h() and p1.r == opanel.r:
					p1.r = opanel.x
					p2.x = opanel.r
					continue

				if opanel.w() > opanel.h() and p1.b == opanel.b:
					p1.b = opanel.y
					p2.y = opanel.b
					continue

		Debug.add_step('Deoverlap panels', self.get_infos())

	# Merge panels that shouldn't have been split (speech bubble diving into a panel)
	def merge_panels(self):
		panels_to_remove = []
		for i, p1 in enumerate(self.panels):
			for j, p2 in enumerate(self.panels[i+1:]):
				if p1.contains(p2):
					panels_to_remove.append(p2)
					p1 = p1.merge(p2)
				elif p2.contains(p1):
					panels_to_remove.append(p1)
					p2 = p2.merge(p1)

		for p in set(panels_to_remove):
			self.panels.remove(p)

		Debug.add_step('Merge panels', self.get_infos())

	# Find out actual gutters between panels
	def actual_gutters(self, func = min):
		gutters_x = []
		gutters_y = []
		for p in self.panels:
			left_panel = p.find_left_panel()
			if left_panel:
				gutters_x.append(p.x - left_panel.r)

			top_panel = p.find_top_panel()
			if top_panel:
				gutters_y.append(p.y - top_panel.b)

		if not gutters_x:
			gutters_x = [1]
		if not gutters_y:
			gutters_y = [1]

		return {'x': func(gutters_x), 'y': func(gutters_y), 'r': -func(gutters_x), 'b': -func(gutters_y)}

	def max_gutter(self):
		return max(self.actual_gutters().values())

	# Expand panels to their neighbour's edge, or page boundaries
	def expand_panels(self):
		gutters = self.actual_gutters()
		for p in self.panels:
			for d in ['x', 'y', 'r', 'b']:  # expand in all four directions
				newcoord = -1
				neighbour = p.find_neighbour_panel(d)
				if neighbour:
					# expand to that neighbour's edge (minus gutter)
					newcoord = getattr(neighbour, {'x': 'r', 'r': 'x', 'y': 'b', 'b': 'y'}[d]) + gutters[d]
				else:
					# expand to the furthest known edge (frame around all panels)
					min_panel = min(self.panels, key = lambda p: getattr(p, d)) if d in [
						'x', 'y'
					] else max(self.panels, key = lambda p: getattr(p, d))
					newcoord = getattr(min_panel, d)

				if newcoord != -1:
					if d in ['r', 'b'] and newcoord > getattr(p, d) or d in ['x', 'y'] and newcoord < getattr(p, d):
						setattr(p, d, newcoord)

		Debug.add_step('Expand panels', self.get_infos())

	# Fix panels simple sorting (issue #12)
	def fix_panels_numbering(self):
		changes = 1
		while (changes):
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
