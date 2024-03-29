import unittest
import os
import shutil
from lib.panel import Panel


class BaseTest(unittest.TestCase):

	@staticmethod
	def run_all():
		unittest.main()

	def setUp(self):
		self.empty_tests_results()

	def tearDown(self):
		self.empty_tests_results()

	results_dir_id = 0

	@staticmethod
	def results_dir():
		BaseTest.results_dir_id += 1
		new_dir = f"./tests/results/kumiko-unittests-{BaseTest.results_dir_id}"
		os.makedirs(new_dir)
		return new_dir

	def empty_tests_results(self):
		with os.scandir('./tests/results') as it:
			for entry in it:
				if not entry.name.startswith('.'):
					if entry.is_file():
						os.remove(entry)
					elif entry.is_dir():
						shutil.rmtree(entry)

	def assertPanelsEqual(self, panels1, panels2):
		self.assertEqual(len(panels1), len(panels2))

		panels1 = list(map(lambda p: Panel(page = None, xywh = p), panels1))
		panels2 = list(map(lambda p: Panel(page = None, xywh = p), panels2))

		for i in range(len(panels1)):
			self.assertEqual(panels1[i], panels2[i], msg = f"{panels1[i].to_xywh()} != {panels2[i].to_xywh()}")
