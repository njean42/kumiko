import os
import json
import copy
import time
import cv2 as cv

from lib.html import HTML


class Debug:

	colours = {
		'white': (255, 255, 255),
		'red': (0, 0, 255),
		'green': (0, 255, 0),
		'blue': (255, 0, 0),
		'lightblue': (200, 200, 0),
		'lightpurple': (200, 0, 200),
		'yellow': (0, 200, 200),
		'gray': (150, 150, 150),
	}

	# white, red and green are used to display main panels
	subpanel_colours = list(colours.values())[3:]

	debug = False
	contourSize = None
	steps = []
	images = {}
	time = time.time_ns()

	@staticmethod
	def add_step(name, infos):
		if not Debug.debug:
			return

		Debug.prev_time = Debug.time
		Debug.time = time.time_ns()

		elapsed = Debug.time - Debug.prev_time
		print(f"{name} ({len(infos['panels'])} panels) -- time elapsed: {elapsed/pow(10,9):.2f} seconds")

		Debug.steps.append({
			'name': name,
			'elapsed_since_last_step': elapsed,
			'infos': copy.deepcopy(infos),
		})

	imgID = 0

	@staticmethod
	def add_image(img, label):
		if not Debug.debug:
			return

		currstep = 'init'
		if len(Debug.steps) > 0:
			currstep = list(reversed(Debug.steps))[0]['name']

		filename = str(Debug.imgID) + '-' + label + '.jpg'
		Debug.imgID += 1
		cv.imwrite(os.path.join('tests/results', filename), img)

		if currstep not in Debug.images:
			Debug.images[currstep] = []
		Debug.images[currstep].append({'filename': filename, 'label': label})

	@staticmethod
	def html(images_dir, reldir):
		html = ''
		html += HTML.header(title = 'Debugging - Kumiko processing steps', reldir = reldir)

		for i in range(len(Debug.steps) - 1):
			j = i + 1

			# Display debug images
			if Debug.steps[i]['name'] in Debug.images:
				html += HTML.imgbox(Debug.images[Debug.steps[i]['name']])

			# Display panels diffs
			files_diff = Debug.get_files_diff(images_dir, [Debug.steps[i]['infos']], [Debug.steps[j]['infos']])

			step_name = str(i + 1) + '. ' + Debug.steps[j]['name']

			if len(files_diff) == 0:
				html += f"<h2>{step_name} - no change</h2>"

			for _, diffs in files_diff.items():
				html += HTML.side_by_side_panels(
					step_name,
					f"took {Debug.steps[j]['elapsed_since_last_step']/pow(10,9):.2f} seconds",
					diffs['jsons'],
					f"BEFORE - {len(diffs['jsons'][0][0]['panels'])} panels",
					f"AFTER  - {len(diffs['jsons'][1][0]['panels'])} panels",
					images_dir = diffs['images_dir'],
					known_panels = diffs['known_panels'],
					diff_numbering_panels = diffs['diff_numbering_panels'],
				)

		html += HTML.footer
		return html

	@staticmethod
	def get_files_diff(file_or_dir, json1, json2):
		from lib.panel import Panel

		files_diff = {}

		for p in range(len(json1)):  # for each page

			# check both images' filename and size, should be the same
			if os.path.basename(json1[p]['filename']) != os.path.basename(json2[p]['filename']):
				print('error, filenames are not the same', json1[p]['filename'], json2[p]['filename'])
				continue
			if json1[p]['size'] != json2[p]['size']:
				print('error, image sizes are not the same', json1[p]['size'], json2[p]['size'])
				continue

			panels_v1 = list(map(lambda p: Panel(None, p), json1[p]['panels']))
			panels_v2 = list(map(lambda p: Panel(None, p), json2[p]['panels']))

			known_panels = [[], []]
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
				images_dir = os.path.relpath(images_dir, 'tests/results') + '/'

			diff_numbering = []
			diff_panels = False
			if len(known_panels[0]) != len(panels_v1) or len(known_panels[1]) != len(panels_v2):
				diff_panels = True
			else:
				for i in range(len(panels_v1)):
					if panels_v1[i] != panels_v2[i]:
						diff_numbering.append(i + 1)

			if diff_panels or len(diff_numbering) > 0:
				files_diff[json1[p]['filename']] = {
					'jsons': [[json1[p]], [json2[p]]],
					'images_dir': images_dir,
					'known_panels': [json.dumps(known_panels[0]),
										json.dumps(known_panels[1])],
					'diff_numbering_panels': diff_numbering,
				}

		return files_diff

	@staticmethod
	def draw_contours(img, contours, colour = 'auto'):
		if not Debug.debug:
			return
		if Debug.contourSize is None:
			raise Exception("Fatal error, Debug.contourSize has not been defined")

		for i in range(len(contours)):
			if colour == 'auto':
				colour = Debug.subpanel_colours[i % len(Debug.subpanel_colours)]

			cv.drawContours(img, [contours[i]], 0, colour, Debug.contourSize)

	@staticmethod
	def draw_panels(img, panels, colour):
		if not Debug.debug:
			return None

		if Debug.contourSize is None:
			raise Exception("Fatal error, Debug.contourSize has not been defined")

		img = img.copy()

		for p in panels:
			cv.rectangle(img, (p.x, p.y), (p.r, p.b), colour, Debug.contourSize)

		# + draw inner white border
		for p in panels:
			cv.rectangle(
				img, (p.x + Debug.contourSize, p.y + Debug.contourSize),
				(p.r - Debug.contourSize, p.b - Debug.contourSize), Debug.colours['white'], int(Debug.contourSize / 2)
			)

		return img
