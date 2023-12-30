#!/usr/bin/env python

import os
import subprocess
import json
import argparse
import re
import tempfile
import time
from lib.debug import Debug
from lib.html import HTML


class Tester:

	files = []
	git_repo = '.'
	git_versions = [
		'v1.4.2',
		'current',
	]

	def __init__(self, browser = None, html = False, folder = None):
		self.browser = browser
		self.html = html or bool(browser)
		if folder:
			self.files = [folder]

		self.max_diffs = 20

		self.savedir = os.path.join('tests', 'results')
		if not os.path.isdir(self.savedir):
			raise Exception(f"'{self.savedir}' is not a directory")

		# Test all files in tests/images/$folder/
		if len(self.files) == 0:
			with os.scandir('tests/images') as it:
				for d in it:
					if d.is_dir() and re.match(r'^\d{3}-', d.name):
						self.files.append(d)
			self.files.sort(key = lambda d: d.name)

	def run_all(self):
		elapsed = {}
		for git_version in self.git_versions:
			elapsed[git_version] = self.run(git_version)

		print("\n\n########## Elapsed time for each version: ##########")
		for version, time in elapsed.items():
			print(f"{version}: {time:.0f} seconds")

	def run(self, git_version):
		print('\n\n########## Finding panels with kumiko version', git_version, '##########')
		kumiko_bin = './kumiko'

		with tempfile.TemporaryDirectory() as tempgit:
			# Get that Kumiko version
			if git_version != 'current':
				subprocess.run(['git', 'clone', self.git_repo, tempgit], capture_output = True, check = True)
				subprocess.run(['git', 'checkout', git_version], cwd = tempgit, capture_output = True, check = True)
				kumiko_bin = os.path.join(tempgit, 'kumiko')

			t1 = time.time()

			for f in self.files:
				file_or_dir = f if isinstance(f, str) else f.name
				print(f"\n##### Kumiko-cutting {file_or_dir} ({git_version}) #####")

				subprocess.run(['mkdir', '-p', os.path.join(self.savedir, git_version)], check = True)
				jsonfile = os.path.join(self.savedir, git_version, os.path.basename(f) + '.json')

				subprocess.run(args = [kumiko_bin, '-i', f, '-o', jsonfile, '--progress'], check = True)

			return time.time() - t1

	def compare_all(self):
		for i in range(len(self.git_versions) - 1):
			v1 = self.git_versions[i]
			v2 = self.git_versions[i + 1]
			print('\n\n########## Comparing kumiko results between versions', v1, 'and', v2, '##########')

			files_diff = {}

			for file_or_dir in self.files:
				if len(files_diff) > 20:
					print('The maximum number of differences in files (20) has been reached, stopping')
					break

				with open(
					os.path.join(self.savedir, v1,
									os.path.basename(file_or_dir) + '.json'), encoding = "utf8"
				) as fh:
					json1 = json.load(fh)
				with open(
					os.path.join(self.savedir, v2,
									os.path.basename(file_or_dir) + '.json'), encoding = "utf8"
				) as fh:
					json2 = json.load(fh)

				files_diff.update(Debug.get_files_diff(file_or_dir, json1, json2))

			print('Found', len(files_diff), 'differences')

			if not self.html:
				return

			print('Generating HTML diff file')

			html_diff_file = os.path.join(self.savedir, 'diff-' + v1 + '-' + v2 + '.html')
			with open(html_diff_file, 'w', encoding = "utf8") as diff_file:
				diff_file.write(HTML.header('Comparing Kumiko results', '../../'))

				diff_file.write(HTML.nbdiffs(files_diff))

				for img, diffs in files_diff.items():
					diff_file.write(
						HTML.side_by_side_panels(
							img,
							'',
							diffs['jsons'],
							v1,
							v2,
							images_dir = diffs['images_dir'],
							known_panels = diffs['known_panels'],
							diff_numbering_panels = diffs['diff_numbering_panels'],
						)
					)

				diff_file.write(HTML.footer)

			if self.browser:
				subprocess.run([self.browser, html_diff_file], check = True)


parser = argparse.ArgumentParser(description = 'Kumiko Tester')

parser.add_argument(
	'action',
	nargs = '?',
	help = "Just 'run' (compute information about files), 'compare' two versions of the code, or both",
	choices = ['run', 'compare', 'run_compare'],
	default = 'run_compare'
)

parser.add_argument(
	'-b',
	'--browser',
	nargs = '?',
	help = 'Opens given browser to view the differences when ready (implies --html)',
	choices = ['firefox', 'konqueror', 'chromium'],
	const = 'firefox'
)

parser.add_argument(
	'--html', action = 'store_true', help = 'Generates an HTML file showing the differences between code versions'
)

parser.add_argument(
	'-f',
	'--folder',
	nargs = 1,
	help = 'A folder ton run kumiko versions against',
)

args = parser.parse_args()

tester = Tester(
	html = args.html,
	browser = args.browser if args.browser else None,
	folder = args.folder[0] if args.folder else None,
)

if args.action in ['run', 'run_compare']:
	tester.run_all()
if args.action in ['compare', 'run_compare']:
	tester.compare_all()
