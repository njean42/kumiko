# import unittest
import subprocess
import json
from tests.base import BaseTest


class TestKumiko(BaseTest):

	def test_simple_run(self):
		res = subprocess.run(
			['./kumiko', '-i', './tests/images/000-common-page-templates/simple.png'], capture_output = True
		)
		out = json.loads(res.stdout)
		panels = out[0].get("panels", [])

		self.assertPanelsEqual(
			panels, [
				[36, 56, 268, 248],
				[336, 56, 468, 248],
				[36, 336, 768, 328],
				[36, 696, 328, 188],
				[36, 916, 328, 248],
				[396, 696, 408, 468],
			]
		)


if __name__ == '__main__':
	unittest.main()
