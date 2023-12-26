import math
import numpy as np


class Segment:

	def __init__(self, a, b):
		self.a = a
		self.b = b

	def __str__(self):
		return f"({self.a}, {self.b})"

	def dist(self):
		return math.sqrt(self.dist_x()**2 + self.dist_y()**2)

	def dist_x(self):
		return self.b[0] - self.a[0]

	def dist_y(self):
		return self.b[1] - self.a[1]

	def left(self):
		return min(self.a[0], self.b[0])

	def top(self):
		return min(self.a[1], self.b[1])

	def right(self):
		return max(self.a[0], self.b[0])

	def bottom(self):
		return max(self.a[1], self.b[1])

	def to_xyrb(self):
		return [self.left(), self.top(), self.right(), self.bottom()]

	def intersect(self, other, max_gutter):
		max_gutter = max(max_gutter, 10)  # hardcoded 10 pixels, find better
		dbg = False

		# angle too big ?
		if not self.angle_ok_with(other):
			if dbg: print(f"angle too big {self.angle_with(other)}")
			return None

		# from here, segments are almost parallel

		# segments are apart ?
		if any(
			[
				self.right() < other.left() - max_gutter,  # self left from other
				self.left() > other.right() + max_gutter,  # self right from other
				self.bottom() < other.top() - max_gutter,  # self above other
				self.top() > other.bottom() + max_gutter,  # self below other
			]
		):
			if dbg: print(f"segments apart")
			return None

		# segments overlap
		# self.sort(key=lambda d1: d1[0])
		# other.sort(key=lambda d1: d1[0])

		# left_segment, right_segment = sorted([self,other], key=lambda s: sum(s[0]))
		# del self, other

		# distance between segments
		# a, b = left_segment
		# c, d = right_segment

		projected_c = self.projected_point(other.a)
		dist_c_to_ab = Segment(other.a, projected_c).dist()

		projected_d = self.projected_point(other.b)
		dist_d_to_ab = Segment(other.b, projected_d).dist()

		# segments are a bit too far from each other
		if (dist_c_to_ab + dist_d_to_ab) / 2 > max_gutter:
			if dbg: print(f"segments too far − max({dist_c_to_ab},{dist_d_to_ab})")
			return None

		# segments overlap, or one contains the other
		#  A----B
		#     C----D
		# or
		#  A------------B
		#      C----D
		sorted_dots = sorted([self.a, self.b, other.a, other.b], key = sum)
		middle_dots = sorted_dots[1:3]
		b, c = middle_dots

		return Segment(b, c)

	def union(self, other, max_gutter):
		intersect = self.intersect(other, max_gutter)
		if intersect is None:
			return None

		dots = [tuple(self.a), tuple(self.b), tuple(other.a), tuple(other.b)]
		dots.remove(tuple(intersect.a))
		dots.remove(tuple(intersect.b))
		return Segment(dots[0], dots[1])

	def angle_with(self, other):
		return math.degrees(abs(self.angle() - other.angle()))

	def angle_ok_with(self, other):
		angle = self.angle_with(other)
		return angle < 10 or abs(angle - 180) < 10

	def angle(self):
		return math.atan(self.dist_y() / self.dist_x()) if self.dist_x() != 0 else math.pi / 2

	def intersect_all(self, segments, max_gutter):
		segments_match = []
		for segment in segments:
			s3 = self.intersect(segment, max_gutter)
			if s3 is not None:
				segments_match.append(s3)

		return Segment.union_all(segments_match, max_gutter)

	@staticmethod
	def along_polygon(polygon, i, j):
		debug = i == 7 and j == 39
		dot1 = polygon[i][0]
		dot2 = polygon[j][0]

		split_segment = Segment(dot1, dot2)

		if debug: print(f"original split segment: {split_segment}")

		while True:
			i = (i - 1) % len(polygon)
			add_segment = Segment(polygon[i][0], polygon[(i + 1) % len(polygon)][0])
			if add_segment.angle_ok_with(split_segment):
				split_segment = Segment(add_segment.a, split_segment.b)
				if debug:
					print(
						f"[i] add segment! {add_segment} (angle {add_segment.angle_with(split_segment)}) => {split_segment}"
					)
			else:
				break

		while True:
			j = (j + 1) % len(polygon)
			add_segment = Segment(polygon[(j - 1) % len(polygon)][0], polygon[j][0])
			if add_segment.angle_ok_with(split_segment):
				if debug:
					print(
						f"[j] add segment! {add_segment} (angle {add_segment.angle_with(split_segment)}) => {split_segment}"
					)
				split_segment = Segment(split_segment.a, add_segment.b)
			else:
				break

		return split_segment

	@staticmethod
	def union_all(segments, max_gutter):
		unioned_segments = True
		while unioned_segments:
			unioned_segments = False
			dedup_segments = []
			used = {}
			for i, s1 in enumerate(segments):
				for s2 in segments[i + 1:]:
					if used.get(s2):
						continue

					s3 = s1.union(s2, max_gutter)
					if s3 is not None:
						unioned_segments = True
						dedup_segments += [s3]
						used[s1] = True
						used[s2] = True
						break

				if not used.get(s1):
					dedup_segments += [s1]

			segments = dedup_segments

		return dedup_segments

	def projected_point(self, p):
		a = np.array(self.a)
		b = np.array(self.b)
		p = np.array(p)
		ap = p - a
		ab = b - a
		result = a + np.dot(ap, ab) / np.dot(ab, ab) * ab
		return result
