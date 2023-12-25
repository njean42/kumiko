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

	def intersect(self, other):
		dbg = False

		# angle too big ?
		angle = self.angle_between_segments(other)
		if angle > 10 and abs(angle - 180) > 10:
			if dbg: print(f"angle too big {angle}")
			return None

		# from here, segments are almost parallel

		# segments are apart ?
		if any(
			[
				self.right() < other.left() - GUTTER,  # self left from other
				self.left() > other.right() + GUTTER,  # self right from other
				self.bottom() < other.top() - GUTTER,  # self above other
				self.top() > other.bottom() + GUTTER,  # self below other
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

		projected_c = point_on_line(np.array(self.a), np.array(self.b), np.array(other.a))
		dist_c_to_ab = Segment(other.a, projected_c).dist()

		projected_d = point_on_line(np.array(self.a), np.array(self.b), np.array(other.b))
		dist_d_to_ab = Segment(other.b, projected_d).dist()

		# segments are a bit too far from each other
		if (dist_c_to_ab + dist_d_to_ab) / 2 > GUTTER:
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

	def union(self, other):
		intersect = self.intersect(other)
		if intersect is None:
			return None

		dots = [tuple(self.a), tuple(self.b), tuple(other.a), tuple(other.b)]
		dots.remove(tuple(intersect.a))
		dots.remove(tuple(intersect.b))
		return Segment(dots[0], dots[1])

	def angle_between_segments(self, other):
		return math.degrees(abs(self.angle() - other.angle()))

	def angle(self):
		return math.atan(self.dist_y() / self.dist_x()) if self.dist_x() != 0 else math.pi / 2

	@staticmethod
	def union_all(segments):
		unioned_segments = True
		while unioned_segments:
			unioned_segments = False
			dedup_segments = []
			used = {}
			for i, s1 in enumerate(segments):
				for s2 in segments[i+1:]:
					if used.get(s2):
						continue

					s3 = s1.union(s2)
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


def point_on_line(a, b, p):
	ap = p - a
	ab = b - a
	result = a + np.dot(ap, ab) / np.dot(ab, ab) * ab
	return result


GUTTER = 10
