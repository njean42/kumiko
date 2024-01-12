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

		self.temp_folder = tempfile.TemporaryDirectory()

		i = 0
		nbdigits = len(str(len(urls)))
		for url in urls:
			filename = 'img' + ('0' * nbdigits + str(i))[-nbdigits:]

			if self.options['progress']:
				print('\t', url, (' -> ' + filename) if urls else '', file = sys.stderr)

			i += 1
			parts = urlparse(url)
			if not parts.netloc or not parts.path:
				continue

			r = requests.get(url, timeout = 5)
			with open(os.path.join(self.temp_folder.name, filename), 'wb') as f:
				f.write(r.content)

		self.parse_dir(self.temp_folder.name, urls = urls)

	def parse_pdf_file(self, pdf_filename):
		try:
			import pdf2image
		except ModuleNotFoundError:
			print("Please `pip install pdf2image` if you give PDF --input files to Kumiko", file = sys.stderr)
			sys.exit(1)

		self.temp_folder = tempfile.TemporaryDirectory()
		for image in pdf2image.convert_from_path(file_or_folder):
			image_output_path = os.path.join(self.temp_folder.name, f"page_{i}.jpg")
			image.save(image_output_path, "JPEG")

		return self.parse_dir(self.temp_folder.name)

	def parse_dir(self, directory, urls = None):
		filenames = []
		for filename in os.scandir(directory):
			filenames.append(filename.path)
		return self.parse_images(filenames, urls)

	def parse_images(self, filenames, urls = None):
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

	def save_panels(self, output_format = "jpg"):
		output_path = "/tmp/kumiko-out"  # TODO
		if not os.path.exists(output_path):
			os.makedirs(output_path)

		for page in self.page_list:
			for i, (x, y, width, height) in enumerate(panels):
				panel = page.img[y:y + height, x:x + width]
				output_file = os.path.join(output_path, f"panel_{i}.{output_format}")
				cv.imwrite(output_file, panel)
