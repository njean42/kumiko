# import unittest
import subprocess
import json
import re
import os
from tests.base import BaseTest


class TestKumiko(BaseTest):

	simple_image = './tests/images/000-common-page-templates/simple.png'
	simple_image_panels = [
		[36, 56, 268, 248],
		[336, 56, 468, 248],
		[36, 336, 768, 328],
		[36, 696, 328, 188],
		[36, 916, 328, 248],
		[396, 696, 408, 468],
	]

	def test_simple_run(self):
		res = subprocess.run(['./kumiko', '-i', self.simple_image], capture_output = True)
		out = json.loads(res.stdout)
		panels = out[0].get("panels", [])

		self.assertPanelsEqual(panels, self.simple_image_panels)

	def test_panels_saving(self):
		res = subprocess.run(
			['./kumiko', '-i', self.simple_image, '--save-panels',
				BaseTest.results_dir()], capture_output = True
		)

		res_stderr = res.stderr.decode("utf-8").strip()
		stderr_re = r'^Saved \d+ panel images to (.*)$'

		self.assertRegex(res_stderr, stderr_re)
		match = re.search(stderr_re, res_stderr)

		out_dir = os.path.join(match[1], 'simple.png')
		self.assertEqual(len(os.listdir(out_dir)), len(self.simple_image_panels))


if __name__ == '__main__':
	BaseTest.run_all()
