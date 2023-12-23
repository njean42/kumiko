import math
import cv2 as cv
import numpy as np

from lib.segment import Segment
from lib.debug import Debug


class Panel:

	@staticmethod
	def from_xyrb(page, x, y, r, b):
		return Panel(page, xywh = [x, y, r - x, b - y])

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
		self.coverage = None

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
		return max(possible_panels, key = lambda p: p.area()) if len(possible_panels) > 0 else self

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
			if other == self:
				continue
			if self.overlaps(other):
				return True

		return False

	def split(self):
		if self.polygon is None:
			return None

		if self.is_small():
			return None

		coverage = self.segments_coverage()
		if coverage['pct'] < 50 / 100:
			return None

		max_dist_nearby_dots_x = self.w() / 3
		max_dist_nearby_dots_y = self.h() / 3
		max_diagonal = math.sqrt(max_dist_nearby_dots_x**2 + max_dist_nearby_dots_y**2)
		dots_along_lines_dist = max_diagonal / 2

		# add dots along straight edges, so that a dot can be "nearby an edge"
		polygon = np.ndarray(shape = (0, 1, 2), dtype = int, order = 'F')
		for i in range(len(self.polygon)):
			j = i + 1
			dot1 = self.polygon[i][0]
			dot2 = self.polygon[j % len(self.polygon)][0]

			polygon = np.append(polygon, [[dot1]], axis = 0)
			Debug.draw_dot(dot1[0], dot1[1], Debug.colours['gray'])

			seg = Segment(dot1, dot2)
			while (seg.dist() > dots_along_lines_dist):
				alpha_x = math.acos((seg.dist_x()) / seg.dist())
				alpha_y = math.asin((seg.dist_y()) / seg.dist())
				dist_x = int(math.cos(alpha_x) * dots_along_lines_dist)
				dist_y = int(math.sin(alpha_y) * dots_along_lines_dist)

				dot1 = [dot1[0] + dist_x, dot1[1] + dist_y]

				polygon = np.append(polygon, [[dot1]], axis = 0)
				Debug.draw_dot(dot1[0], dot1[1], Debug.colours['gray'])

				seg = Segment(dot1, dot2)

		# Find dots nearby one another
		nearby_dots = []
		min_dots_between_nearby_dots = round(len(polygon) / 4)

		for i in range(len(polygon) - min_dots_between_nearby_dots):
			for j in range(i + min_dots_between_nearby_dots, len(polygon)):
				dot1 = polygon[i][0]
				dot2 = polygon[j][0]
				seg = Segment(dot1, dot2)

				if abs(seg.dist_x()) <= max_dist_nearby_dots_x and abs(seg.dist_y()) <= max_dist_nearby_dots_y:
					nearby_dots.append([i, j])
					# if dot1[0] == 674 and dot2[1] == 43:
					# 	print(f"{seg.dist_x()} <= {max_dist_nearby_dots_x} and {seg.dist_y()} <= {max_dist_nearby_dots_y}")

		if len(nearby_dots) == 0:
			return None

		splits = []
		for dots in nearby_dots:
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

			splits.append([panel1, panel2, (polygon[dots[0]][0], polygon[dots[1]][0])])

		# only consider splits that create panel with good segments coverage
		splits = list(filter(lambda split: self.coverage_ok(split), splits))

		if len(splits) == 0:
			return None

		# return the split that creates the two most size-similar panels
		best_split = max(
			splits, key = lambda split: split[0].segments_coverage()['pct'] + split[1].segments_coverage()['pct']
		)

		# split_panel1, split_panel2, nearby_dots = best_split
		# print(f"panel {self} ({self.segments_coverage()['pct']:.0%}) was split between dots {nearby_dots} into")
		# print(f"\t{split_panel1} {split_panel1.segments_coverage()['pct']:.0%}")
		# print(f"\tand\n\t{split_panel2} {split_panel2.segments_coverage()['pct']:.0%}")
		# print(f"\tmax_dist_nearby_dots = {max_dist_nearby_dots_x}, {max_dist_nearby_dots_y}")

		return best_split[0:2]

	# allow 10% loss in segments coverage
	def coverage_ok(self, split):
		return all(
			[
				split[0].segments_coverage()['pct'] >= self.segments_coverage()['pct'] - 10 / 100,
				split[1].segments_coverage()['pct'] >= self.segments_coverage()['pct'] - 10 / 100,
			]
		)

	def segments_coverage(self):
		if self.polygon is None:
			return -1

		if self.coverage is not None:
			return self.coverage

		hull = cv.convexHull(self.polygon)

		segments_match = []
		for i, dot1 in enumerate(hull):
			dot2 = hull[(i + 1) % len(hull)]
			hull_segment = Segment(dot1[0], dot2[0])

			for segment in self.page.segments:
				s3 = hull_segment.intersect(segment)
				if s3 is not None:
					segments_match.append(s3)

		unioned_segments = True
		while (unioned_segments):
			unioned_segments = False
			for i, s1 in enumerate(segments_match):
				for j, s2 in enumerate(segments_match):
					if j <= i:
						continue

					s3 = s1.union(s2)
					if s3 is None:
						continue

					unioned_segments = True
					segments_match.append(s3)
					del segments_match[j]
					del segments_match[i]
					break

				if unioned_segments:
					break

		segments_covered_distance = int(sum(map(lambda s: s.dist(), segments_match)))
		hull_perimeter = int(cv.arcLength(hull, True))

		self.coverage = {
			'segments_covered_distance': segments_covered_distance,
			'perimeter': hull_perimeter,
			'pct': segments_covered_distance / hull_perimeter,
			'segments': segments_match
		}

		return self.coverage
