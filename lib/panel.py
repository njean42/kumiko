

import sys
import cv2 as cv
import numpy as np


class Panel:
	def __init__(self, xywh=None, polygon=None):
		if xywh is None and polygon is None:
			raise Exception('Fatal error: no parameter to define Panel boundaries')
		
		if xywh is None:
			xywh = cv.boundingRect(polygon)
		
		for d in ['x','y','r','b']: super().__setattr__(d,0)  # dummy init so that all four edges have a value (see __setattr__)
		self.x = xywh[0]           # panel's left edge
		self.y = xywh[1]           # panel's top edge
		self.r = self.x + xywh[2]  # panel's right edge
		self.b = self.y + xywh[3]  # panel's bottom edge
		
		self.polygon = polygon
	
	def to_xywh(self):
		return [self.x, self.y, self.w, self.h]
	
	def __eq__(self, other):
		return \
			abs(self.x-other.x) < self.wt and \
			abs(self.y-other.y) < self.ht and \
			abs(self.r-other.r) < self.wt and \
			abs(self.b-other.b) < self.ht
	
	def __lt__(self, other):
		# panel is above other
		if other.y >= self.b - self.ht and other.y >= self.y - self.ht:
			return True
		
		# panel is below other
		if self.y >= other.b - self.ht and self.y >= other.y - self.ht:
			return False
		
		# panel is left from other
		if other.x >= self.r - self.wt and other.x >= self.x - self.wt:
			return True
		
		# panel is right from other
		if self.x >= other.r - self.wt and self.x >= other.x - self.wt:
			return False
		
		return True  # should not happen, TODO: raise an exception?
	
	def __le__(self, other): return self.__lt__(other)
	def __gt__(self, other): return not self.__lt__(other)
	def __ge__(self, other): return self.__gt__(other)
	def area(self): return self.w * self.h
	
	def __str__(self): return "[left: {}, right: {}, top: {}, bottom: {} ({}x{})]".format(self.x,self.r,self.y,self.b,self.w,self.h)
	
	def __setattr__(self,name,value):
		if name in ['w','h','wt','ht']:
			raise Exception("Fatal error, setting a panel's width or height is not allowed");
		super().__setattr__(name, value)
		
		# update width and height
		if name in ['x','y','r','b']:
			super().__setattr__('w',self.r - self.x)
			super().__setattr__('wt',self.w / 10)
			super().__setattr__('h',self.b - self.y)
			super().__setattr__('ht',self.h / 10)
	
	
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
		
		return Panel([x,y,r-x,b-y])
	
	
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
	
	
	def split(self):
		if self.polygon is None:
			raise Exception('Fatal error, trying to split a Panel with no polygon (not the result of opencv.findContours)')
		
		close_dots = []
		for i in range(len(self.polygon)-1):
			all_close = True
			for j in range(i+1,len(self.polygon)):
				dot1 = self.polygon[i][0]
				dot2 = self.polygon[j][0]
				
				# elements that join panels together (e.g. speech bubbles) will be ignored (cut out) if their width and height is < min(panelwidth * ratio, panelheight * ratio)
				ratio = 0.25
				max_dist = min(self.w * ratio, self.h * ratio)
				if abs(dot1[0]-dot2[0]) < max_dist and abs(dot1[1]-dot2[1]) < max_dist:
					if not all_close:
						close_dots.append([i,j])
				else:
					all_close = False
		
		if len(close_dots) == 0:
			return None
		
		# take the close dots that are closest from one another
		cuts = sorted(close_dots, key=lambda d:
			abs(self.polygon[d[0]][0][0]-self.polygon[d[1]][0][0]) +  # dot1.x - dot2.x
			abs(self.polygon[d[0]][0][1]-self.polygon[d[1]][0][1])    # dot1.y - dot2.y
		)
		
		for cut in cuts:
			poly1len = len(self.polygon) - cut[1] + cut[0]
			poly2len = cut[1] - cut[0]
			
			# A panel should have at least three edges
			if min(poly1len,poly2len) <= 2:
				continue
			
			# Construct two subpolygons by distributing the dots around our cut (our close dots)
			poly1 = np.zeros(shape=(poly1len,1,2), dtype=int)
			poly2 = np.zeros(shape=(poly2len,1,2), dtype=int)
			
			x = y = 0
			for i in range(len(self.polygon)):
				if i <= cut[0] or i > cut[1]:
					poly1[x][0] = self.polygon[i]
					x += 1
				else:
					poly2[y][0] = self.polygon[i]
					y += 1
			
			panel1 = Panel(polygon=poly1)
			panel2 = Panel(polygon=poly2)
			
			# Check that subpanels' width and height are not too small
			wh_ok = True
			for p in [panel1,panel2]:
				if p.h / self.h < 0.1:
					wh_ok = False
				if p.w / self.w < 0.1:
					wh_ok = False
			
			if not wh_ok:
				continue
			
			# Check that subpanels' area is not too small
			area1 = cv.contourArea(poly1)
			area2 = cv.contourArea(poly2)
			
			areaRatio = min(area1,area2) / max(area1,area2)
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
