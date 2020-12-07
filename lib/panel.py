

import sys


class Panel:
	def __init__(self, xywh, gutterThreshold):
		for d in ['x','y','r','b']: super().__setattr__(d,0)  # dummy init so that all four edges have a value (see __setattr__)
		self.x = xywh[0]           # panel's left edge
		self.y = xywh[1]           # panel's top edge
		self.r = self.x + xywh[2]  # panel's right edge
		self.b = self.y + xywh[3]  # panel's bottom edge
		self.gutterThreshold = gutterThreshold
	
	def to_xywh(self):
		return [self.x, self.y, self.w, self.h]
	
	def __eq__(self, other):
		return \
			abs(self.x-other.x) < self.gutterThreshold and \
			abs(self.y-other.y) < self.gutterThreshold and \
			abs(self.r-other.r) < self.gutterThreshold and \
			abs(self.b-other.b) < self.gutterThreshold
	
	def __lt__(self, other):
		# panel is above other
		if other.y >= self.b - self.gutterThreshold and other.y >= self.y - self.gutterThreshold:
			return True
		
		# panel is below other
		if self.y >= other.b - self.gutterThreshold and self.y >= other.y - self.gutterThreshold:
			return False
		
		# panel is left from other
		if other.x >= self.r - self.gutterThreshold and other.x >= self.x - self.gutterThreshold:
			return True
		
		# panel is right from other
		if self.x >= other.r - self.gutterThreshold and self.x >= other.x - self.gutterThreshold:
			return False
		
		return True  # should not happen, TODO: raise an exception?
	
	def __le__(self, other): return self.__lt__(other)
	def __gt__(self, other): return not self.__lt__(other)
	def __ge__(self, other): return self.__gt__(other)
	def area(self): return self.w * self.h
	
	def __str__(self): return "[left: {}, right: {}, top: {}, bottom: {} ({}x{})]".format(self.x,self.r,self.y,self.b,self.w,self.h)
	
	def __setattr__(self,name,value):
		if name in ['w','h']:
			print("Fatal error, setting a panel's width or height is not allowed")
			sys.exit(1)
		super().__setattr__(name, value)
		
		# update width and height
		if name in ['x','y','r','b']:
			super().__setattr__('w',self.r - self.x)
			super().__setattr__('h',self.b - self.y)
	
	
	def overlap_panel(self,other):
		if self.x > other.r or other.x > self.r:  # panels are left and right from one another
			return None
		if self.y > other.b or other.y > self.b:  # panels are above and below one another
			return None
		
		# if we're here, panels overlap at least a bit
		x = max(self.x,other.x)
		y = max(self.y,other.y)
		r = min(self.r,other.r)
		b = min(self.b,other.b)
		
		return Panel([x,y,r-x,b-y], self.gutterThreshold)
	
	
	def contains(self,other):
		o_panel = self.overlap_panel(other)
		if not o_panel:
			return False
		
		# self contains other if their overlapping area is more than 75% of other's area
		return o_panel.area() / other.area() > 0.75 
	
	
	def same_row(self,other): return other.y <= self.y <= other.b or self.y <= other.y <= self.b
	def same_col(self,other): return other.x <= self.x <= other.r or self.x <= other.x <= self.r
	
	
	def find_top_panel(self,panels):
		all_top = list(filter(lambda p: p.b <= self.y and p.same_col(self), panels))
		return max(all_top, key=lambda p: p.b) if all_top else None
	
	
	def find_left_panel(self,panels):
		all_left = list(filter(lambda p: p.r <= self.x and p.same_row(self), panels))
		return max(all_left, key=lambda p: p.r) if all_left else None
	
	
	def find_bottom_panel(self,panels):
		all_bottom = list(filter(lambda p: p.y >= self.b and p.same_col(self), panels))
		return min(all_bottom, key=lambda p: p.y) if all_bottom else None
	
	
	def find_right_panel(self,panels):
		all_right = list(filter(lambda p: p.x >= self.r and p.same_row(self), panels))
		return min(all_right, key=lambda p: p.x) if all_right else None
	
	
	def find_neighbour_panel(self,d,panels):
		return {
			'x': self.find_left_panel,
			'y': self.find_top_panel,
			'r': self.find_right_panel,
			'b': self.find_bottom_panel,
		}[d](panels)
