import os
import sys
import tempfile
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

		self.options['min_panel_size_ratio'] = options.get('min_panel_size_ratio', None)

		self.page_list = []

	def parse_url_list(self, urls):
		if self.options['progress']:
			print(len(urls), 'files to download', file = sys.stderr)

		with tempfile.TemporaryDirectory() as tempdir:
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
				with open(os.path.join(tempdir, filename), 'wb') as f:
					f.write(r.content)

			self.parse_dir(tempdir, urls = urls)

	def parse_dir(self, directory, urls = None):
		filenames = []
		for filename in os.scandir(directory):
			filenames.append(filename.path)
		self.parse_images(filenames, urls)

	def parse_images(self, filenames, urls = None):
		self.page_list = []

		if self.options['progress']:
			print(len(filenames), 'files to cut panels for', file = sys.stderr)

		i = -1
		for filename in sorted(filenames):
			i += 1
			if self.options['progress']:
				print("\t", urls[i] if urls else filename, file = sys.stderr)

			try:
				self.parse_image(filename, url = urls[i] if urls else None)
			except NotAnImageException:
				if not filename.endswith(".license"):
					print(f"Not an image, will be ignored: {filename}", file = sys.stderr)

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
