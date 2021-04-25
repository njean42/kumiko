

import os, json
import cv2 as cv

from lib.html import HTML
from lib.panel import Panel


class Debug:
	
	colours = {
		'white':       (255,255,255),
		'red':         (0,0,255),
		'green':       (0,255,0),
		'blue':        (255,0,0),
		'lightblue':   (200,200,0),
		'lightpurple': (200,0,200),
		'yellow':      (0,200,200),
		'gray':        (150,150,150),
	}
	subpanel_colours = list(colours.values())[3:]  # white, red and green are used to display main and split panels
	
	
	def __init__(self, debug):
		self.debug = debug
		self.contourSize = None
		self.steps = []
		self.images = {}
		self.infos = {}
	
	
	def add_step(self, name, panels):
		if not self.debug:
			return
		
		self.steps.append({
			'name': name,
			'panels': panels.copy()
		})
	
	
	imgID = 0
	def add_image(self,img,label):
		if not self.debug:
			return
		
		currstep = 'init'
		if len(self.steps) > 0:
			currstep = list(reversed(self.steps))[0]['name']
		
		filename = str(Debug.imgID) + label+'.jpg'
		Debug.imgID += 1
		cv.imwrite(os.path.join('tests/results',filename),img)
		
		if not(currstep in self.images):
			self.images[currstep] = []
		self.images[currstep].append({'filename': filename, 'label': label})
	
	
	def html(self, images_dir, reldir):
		html = ''
		html += HTML.header(title='Debugging - Kumiko processing steps', reldir=reldir)
		
		for i in range(len(self.steps)-1):
			j = i + 1
			
			# Display debug images
			if i == 0:
				html += HTML.imgbox(self.images['init'])
			
			if self.steps[i]['name'] in self.images:
				html += HTML.imgbox(self.images[self.steps[i]['name']])
			
			# Display panels diffs
			self.infos['panels'] = list(map(lambda p: p.to_xywh(), self.steps[i]['panels']))
			json1 = self.infos.copy()
			self.infos['panels'] = list(map(lambda p: p.to_xywh(), self.steps[j]['panels']))
			json2 = self.infos.copy()
			
			files_diff = Debug.get_files_diff(images_dir, [json1], [json2])
			
			step_name = str(i+1) + '. ' +self.steps[j]['name']
			
			if len(files_diff) == 0:
				html += "<h2>{} - no change</h2>".format(step_name);
			
			for filename in files_diff:
				html += HTML.side_by_side_panels(
					step_name,
					files_diff[filename]['jsons'],
					'BEFORE - {} panels'.format(len(files_diff[filename]['jsons'][0][0]['panels'])),
					'AFTER  - {} panels'.format(len(files_diff[filename]['jsons'][1][0]['panels'])),
					images_dir=files_diff[filename]['images_dir'],
					known_panels=files_diff[filename]['known_panels'],
				)
		
		html += HTML.footer
		return html
	
	
	def get_files_diff(file_or_dir,json1,json2):
		files_diff = {}
		
		for p in range(len(json1)):  # for each page
			
			# check both images' filename and size, should be the same
			if os.path.basename(json1[p]['filename']) != os.path.basename(json2[p]['filename']):
				print('error, filenames are not the same',json1[p]['filename'],json2[p]['filename'])
				continue
			if json1[p]['size'] != json2[p]['size']:
				print('error, image sizes are not the same',json1[p]['size'],json2[p]['size'])
				continue
			
			Panel.img_size = json1[p]['size']
			Panel.small_panel_ratio = Panel.DEFAULT_MIN_PANEL_SIZE_RATIO
			
			panels_v1 = list(map(lambda p: Panel(p), json1[p]['panels']))
			panels_v2 = list(map(lambda p: Panel(p), json2[p]['panels']))
			
			known_panels = [[],[]]
			j = -1
			for p1 in panels_v1:
				j += 1
				if p1 in panels_v2:
					known_panels[0].append(j)
			j = -1
			for p2 in panels_v2:
				j += 1
				if p2 in panels_v1:
					known_panels[1].append(j)
			
			images_dir = 'urls'
			if file_or_dir != 'urls':
				images_dir = file_or_dir if os.path.isdir(file_or_dir) else os.path.dirname(file_or_dir)
				images_dir = os.path.relpath(images_dir,'tests/results')+'/'
			
			if len(known_panels[0]) != len(panels_v1) or len(known_panels[1]) != len(panels_v2):
				files_diff[json1[p]['filename']] = {
					'jsons': [[json1[p]],[json2[p]]],
					'images_dir': images_dir,
					'known_panels': [json.dumps(known_panels[0]),json.dumps(known_panels[1])]
				}
		
		return files_diff
	
	
	def draw_contours(self, img, contours, colour='auto'):
		if not self.debug:
			return
		if self.contourSize is None:
			raise Exception("Fatal error, Debug.contourSize has not been defined");
		
		for i in range(len(contours)):
			if colour == 'auto':
				colour = Debug.subpanel_colours[i % len(Debug.subpanel_colours)]
			
			cv.drawContours(img, [contours[i]], 0, colour, self.contourSize)
	
	
	def draw_panels(self, img, panels, colour):
		if not self.debug:
			return
		if self.contourSize is None:
			raise Exception("Fatal error, Debug.contourSize has not been defined");
		
		img = img.copy()
		
		for p in panels:
			cv.rectangle(img, (p.x,p.y), (p.r,p.b), colour, self.contourSize)
		
		# + draw inner white border
		for p in panels:
			cv.rectangle(img, (p.x+self.contourSize,p.y+self.contourSize), (p.r-self.contourSize,p.b-self.contourSize), Debug.colours['white'], int(self.contourSize/2))
		
		return img
