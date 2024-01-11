import os
import sys
import tempfile
import cv2 as cv
import numpy as np
import requests
from urllib.parse import urlparse

from lib.page import Page, NotAnImageException
from lib.debug import Debug


class Kumiko:

	options = {}

	def __init__(self, options = None):
		options = options or {}

		for o in ['progress', 'rtl', 'debug']:
			self.options[o] = o in options and options[o]

		Debug.debug = self.options['debug']

		self.options['min_panel_size_ratio'
						] = options['min_panel_size_ratio'] if 'min_panel_size_ratio' in options else None

		self.page_list = []

	def parse_url_list(self, urls):
		if self.options['progress']:
			print(len(urls), 'files to download', file = sys.stderr)

		with tempfile.TemporaryDirectory() as tempdir:
			i = 0
			nbdigits = len(str(len(urls)))
			downloaded_files = []
			for url in urls:
				filename = 'img' + ('0' * nbdigits + str(i))[-nbdigits:]

				if self.options['progress']:
					print('\t', url, (' -> ' + filename) if urls else '', file = sys.stderr)

				i += 1
				parts = urlparse(url)
				if not parts.netloc or not parts.path:
					continue

				r = requests.get(url, timeout = 5)
				with open(os.path.join(tempdir, filename), 'wb') as f:
					f.write(r.content)

				downloaded_files.append(os.path.join(tempdir, filename))

			parsed_info = self.parse_dir(tempdir, urls = urls)
			return downloaded_files, parsed_info

	def parse_dir(self, directory, urls = None):
		filenames = []
		for filename in os.scandir(directory):
			filenames.append(filename.path)
		return self.parse_images(filenames, urls)

	def parse_images(self, filenames, urls = None):
		self.page_list = []
		infos = []

		if self.options['progress']:
			print(len(filenames), 'files to cut panels for', file = sys.stderr)

		i = -1
		for filename in sorted(filenames):
			i += 1
			if self.options['progress']:
				print("\t", urls[i] if urls else filename, file = sys.stderr)

			try:
				infos.append(self.parse_image(filename, url = urls[i] if urls else None))
			except NotAnImageException:
				if not filename.endswith(".license"):
					print(f"Not an image, will be ignored: {filename}", file = sys.stderr)
		return infos

	def parse_image(self, filename, url = None):
		self.page_list.append(
			Page(
				filename,
				numbering = "rtl" if self.options['rtl'] else "ltr",
				url = url,
				min_panel_size_ratio = self.options['min_panel_size_ratio']
			)
		)

	def get_infos(self):
		return list(map(lambda p: p.get_infos(), self.page_list))

	def save_panels(self, image_path, panels, output_path = None, output_format = "jpg"):
		# Set default output_dir if not specified
		if output_path is None:
			base_name = os.path.splitext(os.path.basename(image_path))[0]
			output_path = os.path.join("./output", base_name)

		# Ensure the output directory exists
		if not os.path.exists(output_path):
			os.makedirs(output_path)

		# Load the original image
		image = cv.imread(image_path)

		# Iterate over each panel and save it
		for i, (x, y, width, height) in enumerate(panels):
			panel = image[y:y + height, x:x + width]
			output_file = os.path.join(output_path, f"panel_{i}.{output_format}")
			cv.imwrite(output_file, panel)
