import cv2 as cv
import numpy as np


class Panel:

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
		return f"[left: {self.x}, right: {self.r}, top: {self.y}, bottom: {self.b} ({self.w()}x{self.h()})]"

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

	def contains(self, other):
		o_panel = self.overlap_panel(other)
		if not o_panel:
			return False

		# self contains other if their overlapping area is more than 50% of other's area
		return o_panel.area() / other.area() > 0.50

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

	@staticmethod
	def merge(page, p1, p2):
		min_x = min(p1.x, p2.x)
		min_y = min(p1.y, p2.y)
		max_r = max(p1.r, p2.r)
		max_b = max(p1.b, p2.b)
		return Panel(page, [min_x, min_y, max_r - min_x, max_b - min_y])

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

	def split(self):
		if self.polygon is None:
			return None

		close_dots = []
		for i in range(len(self.polygon) - 1):
			all_close = True
			for j in range(i + 1, len(self.polygon)):
				dot1 = self.polygon[i][0]
				dot2 = self.polygon[j][0]

				# elements that join panels together (e.g. speech bubbles) will be ignored (cut out) if their width and height is < min(panelwidth * ratio, panelheight * ratio)
				ratio = 0.25
				max_dist = min(self.w() * ratio, self.h() * ratio)
				if abs(dot1[0] - dot2[0]) < max_dist and abs(dot1[1] - dot2[1]) < max_dist:
					if not all_close:
						close_dots.append([i, j])
				else:
					all_close = False

		if len(close_dots) == 0:
			return None

		# take the close dots that are closest from one another
		cuts = sorted(
			close_dots,
			key = lambda d: abs(self.polygon[d[0]][0][0] - self.polygon[d[1]][0][0]) +  # dot1.x - dot2.x
			abs(self.polygon[d[0]][0][1] - self.polygon[d[1]][0][1])  # dot1.y - dot2.y
		)

		for cut in cuts:
			poly1len = len(self.polygon) - cut[1] + cut[0]
			poly2len = cut[1] - cut[0]

			# A panel should have at least three edges
			if min(poly1len, poly2len) <= 2:
				continue

			# Construct two subpolygons by distributing the dots around our cut (our close dots)
			poly1 = np.zeros(shape = (poly1len, 1, 2), dtype = int)
			poly2 = np.zeros(shape = (poly2len, 1, 2), dtype = int)

			x = y = 0
			for i in range(len(self.polygon)):
				if i <= cut[0] or i > cut[1]:
					poly1[x][0] = self.polygon[i]
					x += 1
				else:
					poly2[y][0] = self.polygon[i]
					y += 1

			panel1 = Panel(self.page, polygon = poly1)
			panel2 = Panel(self.page, polygon = poly2)

			# Check that subpanels' width and height are not too small
			wh_ok = True
			for p in [panel1, panel2]:
				if p.h() / self.h() < 0.1:
					wh_ok = False
				if p.w() / self.w() < 0.1:
					wh_ok = False

			if not wh_ok:
				continue

			# Check that subpanels' area is not too small
			area1 = cv.contourArea(poly1)
			area2 = cv.contourArea(poly2)

			if max(area1, area2) == 0:
				continue

			areaRatio = min(area1, area2) / max(area1, area2)
			if areaRatio < 0.1:
				continue

			subpanels1 = panel1.split()
			subpanels2 = panel2.split()

			# resurse (find subsubpanels in subpanels)
			split_panels = []
			split_panels += [panel1] if subpanels1 is None else subpanels1
			split_panels += [panel2] if subpanels2 is None else subpanels2

			return split_panels

		return None
