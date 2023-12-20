import math
import cv2 as cv
import numpy as np

from lib.debug import Debug


class Panel:

	@staticmethod
	def from_xyrb(page, x, y, r, b):
		return Panel(page, xywh=[x, y, r-x, b-y])

	def __init__(self, page, xywh = None, polygon = None):
		self.page = page

		if xywh is None and polygon is None:
			raise Exception('Fatal error: no parameter to define Panel boundaries')

		if xywh is None:
			xywh = cv.boundingRect(polygon)

		self.x = xywh[0]  # panel's left edge
		self.y = xywh[1]  # panel's top edge
		self.r = self.x + xywh[2]  # panel's right edge
		self.b = self.y + xywh[3]  # panel's bottom edge

		self.polygon = polygon

	def w(self):
		return self.r - self.x

	def h(self):
		return self.b - self.y

	def wt(self):
		return self.w() / 10
		# wt = width threshold (under which two edge coordinates are considered equal)

	def ht(self):
		return self.h() / 10
		# ht = height threshold

	def to_xywh(self):
		return [self.x, self.y, self.w(), self.h()]

	def __eq__(self, other):
		return all(
			[
				abs(self.x - other.x) < self.wt(),
				abs(self.y - other.y) < self.ht(),
				abs(self.r - other.r) < self.wt(),
				abs(self.b - other.b) < self.ht(),
			]
		)

	def __lt__(self, other):
		# panel is above other
		if other.y >= self.b - self.ht() and other.y >= self.y - self.ht():
			return True

		# panel is below other
		if self.y >= other.b - self.ht() and self.y >= other.y - self.ht():
			return False

		# panel is left from other
		if other.x >= self.r - self.wt() and other.x >= self.x - self.wt():
			return True if self.page.numbering == 'ltr' else False

		# panel is right from other
		if self.x >= other.r - self.wt() and self.x >= other.x - self.wt():
			return False if self.page.numbering == 'ltr' else True

		return True  # should not happen, TODO: raise an exception?

	def __le__(self, other):
		return self.__lt__(other)

	def __gt__(self, other):
		return not self.__lt__(other)

	def __ge__(self, other):
		return self.__gt__(other)

	def area(self):
		return self.w() * self.h()

	def __str__(self):
		return f"{self.x}x{self.y}-{self.r}x{self.b}"

	def __hash__(self):
		return hash(self.__str__())

	def is_small(self, extra_ratio = 1):
		return any(
			[
				self.w() < self.page.img_size[0] * self.page.small_panel_ratio * extra_ratio,
				self.h() < self.page.img_size[1] * self.page.small_panel_ratio * extra_ratio,
			]
		)

	def is_very_small(self):
		return self.is_small(1 / 10)

	def overlap_panel(self, other):
		if self.x > other.r or other.x > self.r:  # panels are left and right from one another
			return None
		if self.y > other.b or other.y > self.b:  # panels are above and below one another
			return None

		# if we're here, panels overlap at least a bit
		x = max(self.x, other.x)
		y = max(self.y, other.y)
		r = min(self.r, other.r)
		b = min(self.b, other.b)

		return Panel(self.page, [x, y, r - x, b - y])

	def overlaps(self, other):
		opanel = self.overlap_panel(other)
		if opanel is None:
			return False

		area_ratio = 0.1
		result = opanel.area() / min(self.area(), other.area()) > area_ratio

		# print(f"{opanel.area()} ({opanel}) / {min(self.area(), other.area())} (min({self},{other})) = {opanel.area() / min(self.area(), other.area())} >? {area_ratio} => {result}")

		return result

	def contains(self, other):
		o_panel = self.overlap_panel(other)
		if not o_panel:
			return False

		# self contains other if their overlapping area is more than 50% of other's area
		return o_panel.area() / other.area() > 0.50

		return self.contains(segment_panel)

	def same_row(self, other):
		return other.y <= self.y <= other.b or self.y <= other.y <= self.b

	def same_col(self, other):
		return other.x <= self.x <= other.r or self.x <= other.x <= self.r

	def find_top_panel(self):
		all_top = list(filter(lambda p: p.b <= self.y and p.same_col(self), self.page.panels))
		return max(all_top, key = lambda p: p.b) if all_top else None

	def find_left_panel(self):
		all_left = list(filter(lambda p: p.r <= self.x and p.same_row(self), self.page.panels))
		return max(all_left, key = lambda p: p.r) if all_left else None

	def find_bottom_panel(self):
		all_bottom = list(filter(lambda p: p.y >= self.b and p.same_col(self), self.page.panels))
		return min(all_bottom, key = lambda p: p.y) if all_bottom else None

	def find_right_panel(self):
		all_right = list(filter(lambda p: p.x >= self.r and p.same_row(self), self.page.panels))
		return min(all_right, key = lambda p: p.x) if all_right else None

	def find_neighbour_panel(self, d):
		return {
			'x': self.find_left_panel,
			'y': self.find_top_panel,
			'r': self.find_right_panel,
			'b': self.find_bottom_panel,
		}[d]()

	def group_with(self, other):
		min_x = min(self.x, other.x)
		min_y = min(self.y, other.y)
		max_r = max(self.r, other.r)
		max_b = max(self.b, other.b)
		return Panel(self.page, [min_x, min_y, max_r - min_x, max_b - min_y])

	def merge(self, other):
		possible_panels = [self]

		# expand self in all four directions where other is
		if other.x < self.x:
			possible_panels.append(Panel.from_xyrb(self.page, other.x, self.y, self.r, self.b))

		if other.r > self.r:
			for pp in possible_panels.copy():
				possible_panels.append(Panel.from_xyrb(self.page, pp.x, pp.y, other.r, pp.b))

		if other.y < self.y:
			for pp in possible_panels.copy():
				possible_panels.append(Panel.from_xyrb(self.page, pp.x, other.y, pp.r, pp.b))

		if other.b > self.b:
			for pp in possible_panels.copy():
				possible_panels.append(Panel.from_xyrb(self.page, pp.x, pp.y, pp.r, other.b))

		# don't take a merged panel that bumps into other panels on page
		other_panels = [p for p in self.page.panels if p not in [self, other]]
		possible_panels = list(filter(lambda p: not p.bumps_into(other_panels), possible_panels))

		# take the largest merged panel
		return max(possible_panels, key=lambda p: p.area()) if len(possible_panels) > 0 else self

	def is_close(self, other):
		c1x = self.x + self.w() / 2
		c1y = self.y + self.h() / 2
		c2x = other.x + other.w() / 2
		c2y = other.y + other.h() / 2

		return all(
			[
				abs(c1x - c2x) <= (self.w() + other.w()) * 0.75,
				abs(c1y - c2y) <= (self.h() + other.h()) * 0.75,
			]
		)

	def bumps_into(self, other_panels):
		for other in other_panels:
			if self.overlaps(other):
				return True

		return False

	def is_nearby(self, other):
		c1x = self.x + self.w() / 2
		c1y = self.y + self.h() / 2
		c2x = other.x + other.w() / 2
		c2y = other.y + other.h() / 2

		return all(
			[
				abs(c1x - c2x) <= (self.w() + other.w()) * 0.75,
				abs(c1y - c2y) <= (self.h() + other.h()) * 0.75,
			]
		)

	@staticmethod
	def dist(dot1, dot2):
		return math.sqrt(pow(dot1[0] - dot2[0], 2) + pow(dot1[1] - dot2[1], 2))

	# def max_distance_between_nearby_dots(self):
	# 	# elements that join panels together (e.g. speech bubbles) will be ignored (cut out)
	# 	# if their width and height is < min(panelwidth * ratio, panelheight * ratio)
	# 	ratio = 0.25
	# 	return min(self.w() * ratio, self.h() * ratio)

	# def split_by_segment(self, dot1, dot2, max_gutter):
	# 	p1 = p2 = None
	# 	if abs(dot1[0] - dot2[0]) < abs(dot1[1] - dot2[1]):  # vertical line
	# 		x = dot1[0]
	# 		p1 = Panel(self.page, xywh = [self.x, self.y, x - self.x, self.h()])
	# 		p2 = Panel(self.page, xywh = [x, self.y, self.r - x, self.h()])
	# 	else:  # horizontal line
	# 		y = dot1[1]
	# 		p1 = Panel(self.page, xywh = [self.x, self.y, self.r, y - self.y])
	# 		p2 = Panel(self.page, xywh = [self.x, y, self.r, self.b - y])
	# 		return []
 #
	# 	return [p1, p2]

	def segments_coverage(self):
		pass

	def max_distance_between_nearby_dots(self):
		return int(max(self.page.img_size) * self.page.small_panel_ratio)

	def split(self):
		if self.polygon is None:
			return None

		if self.is_small():
			return None

		split_dist = self.max_distance_between_nearby_dots() / 2

		# add dots along straight edges, so that a dot can be "nearby an edge"
		polygon = np.ndarray(shape = (0, 1, 2), dtype = int, order = 'F')
		for i in range(len(self.polygon)):
			j = i + 1
			dot1 = self.polygon[i][0]
			dot2 = self.polygon[j % len(self.polygon)][0]

			polygon = np.append(polygon, [[dot1]], axis = 0)
			Debug.draw_dot(dot1[0], dot1[1], Debug.colours['green'])

			if Panel.dist(dot1, dot2) < split_dist:
				continue

			while (Panel.dist(dot1, dot2) > split_dist):
				alpha_x = math.acos((dot2[0] - dot1[0]) / Panel.dist(dot1, dot2))
				alpha_y = math.asin((dot2[1] - dot1[1]) / Panel.dist(dot1, dot2))
				dist_x = int(math.cos(alpha_x) * split_dist)
				dist_y = int(math.sin(alpha_y) * split_dist)

				dot1 = [dot1[0] + dist_x, dot1[1] + dist_y]

				polygon = np.append(polygon, [[dot1]], axis = 0)
				Debug.draw_dot(dot1[0], dot1[1], Debug.colours['green'])

		# Find dots nearby to one another
		nearby_dots = []
		min_dots_between_nearby_dots = round(len(polygon) / 4)

		print(f"\tmax_distance_between_nearby_dots={self.max_distance_between_nearby_dots()}, min_dots_between_nearby_dots={min_dots_between_nearby_dots}, split_dist={split_dist}, panel={self}")

		for i in range(len(polygon) - min_dots_between_nearby_dots):
			for j in range(i + min_dots_between_nearby_dots, len(polygon)):
				dot1 = polygon[i][0]
				dot2 = polygon[j][0]

				if Panel.dist(dot1, dot2) < self.max_distance_between_nearby_dots():
					nearby_dots.append([i, j])

		if len(nearby_dots) == 0:
			return None

		print(f"\t{len(nearby_dots)} nearby_dots")

		splits = []
		for dots in nearby_dots:
			for i in dots:
				dot = polygon[i][0]
				Debug.draw_dot(dot[0], dot[1], Debug.colours['lightpurple'])

			poly1len = len(polygon) - dots[1] + dots[0]
			poly2len = dots[1] - dots[0]

			# A panel should have at least three edges
			if min(poly1len, poly2len) <= 2:
				continue

			# Construct two subpolygons by distributing the dots around our nearby dots
			poly1 = np.zeros(shape = (poly1len, 1, 2), dtype = int)
			poly2 = np.zeros(shape = (poly2len, 1, 2), dtype = int)

			x = y = 0
			for i in range(len(polygon)):
				if i <= dots[0] or i > dots[1]:
					poly1[x][0] = polygon[i]
					x += 1
				else:
					poly2[y][0] = polygon[i]
					y += 1

			panel1 = Panel(self.page, polygon = poly1)
			panel2 = Panel(self.page, polygon = poly2)

			for i in dots:
				dot = polygon[i][0]
				Debug.draw_dot(dot[0], dot[1], Debug.colours['lightpurple'])

			if panel1.is_small() or panel2.is_small():
				continue

			if panel1 == self or panel2 == self:
				continue

			if panel1.overlaps(panel2):
				continue

			print(f"\t{len(splits)} splits (panel {self})")

			splits.append([panel1, panel2])

		# for s in splits:
		# 	print(f"{self} => {s[0]} + {s[1]}")

		# return the split that creates the two most size-similar panels
		return None if len(splits) == 0 else max(splits, key=lambda split: abs(split[0].area() - split[1].area()))
