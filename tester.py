#!/usr/bin/env python


import os, subprocess, json, argparse, re, tempfile
from kumikolib import Kumiko,Panel
from lib.html import HTML



class Tester:
	
	files = []
	git_repo = 'https://framagit.org/nicooo/kumiko'
	git_versions = [
		# 'v1.0', 'v1.1', 'v1.11',
		'v1.2',
		'current',
	]
	
	def __init__(self, options):
		self.savedir = os.path.join('tests','results')
		if not os.path.isdir(self.savedir):
			raise Exception("'%s' is not a directory" % self.savedir)
		
		self.options = {
			'browser': options['browser'] if 'browser' in options and options['browser'] else False,
			'html': options['html'] if 'html' in options else False
		}
		
		# Test all files in tests/images/$folder/
		if len(self.files) == 0:
			for d in os.scandir('tests/images'):
				 if d.is_dir():
					 self.files.append(d)
			self.files.sort(key=lambda d: d.name)
	
	
	def run_all(self):
		for git_version in self.git_versions:
			self.run(git_version)
	
	
	def run(self, git_version):
		print('\n########## Finding speech bubbles with kumiko version',git_version,'##########')
		kumiko_bin = './kumiko'
		
		# Kumiko would not accept non-image files before v1.2, special case for .licence files
		accepts_license_files = git_version >= 'v1.2' or not re.match('^v\d+.\d+$', git_version)
		tmpfolder = None if accepts_license_files else tempfile.TemporaryDirectory(dir='./tests')
		
		# Get that Kumiko version
		if git_version != 'current':
			tempgit = '/tmp/kumikogit'
			subprocess.run(['rm','-rf',tempgit])
			subprocess.run(['git', 'clone', self.git_repo, tempgit], capture_output=True)
			subprocess.run(['git', 'checkout', git_version], cwd=tempgit, capture_output=True)
			kumiko_bin = os.path.join(tempgit,'kumiko')
		
		for f in self.files:
			# move .license files to tempdir (<v1.2 compatibility)
			if tmpfolder and os.path.isdir(f):
				for g in os.scandir(f):
					if re.search('\.license$',g.name):
						os.rename(g,os.path.join(tmpfolder.name,os.path.basename(g)))
			
			print("##### Kumiko-cutting",f if isinstance(f,str) else f.name,"#####")
			
			subprocess.run(['mkdir','-p',os.path.join(self.savedir,git_version)])
			jsonfile = os.path.join(self.savedir,git_version,os.path.basename(f)+'.json')
			subprocess.run(args=[kumiko_bin, '-i', f, '-o', jsonfile, '--progress'])
			
			if tmpfolder and os.path.isdir(f):
				for g in os.scandir(tmpfolder.name):
					if re.search('\.license$',g.name):
						os.rename(g,os.path.join(f,os.path.basename(g)))
	
	
	def compare_all(self):
		self.max_diffs = 20
		
		for i in range(len(self.git_versions)-1):
			v1 = self.git_versions[i]
			v2 = self.git_versions[i+1]
			print('\n########## Comparing kumiko results between versions',v1,'and',v2,'##########')
			
			files_diff = {}
			
			for f in self.files:
				
				if len(files_diff) > 20:
					print('The maximum number of differences in files (20) has been reached, stopping')
					break
				
				with open(os.path.join(self.savedir,v1,os.path.basename(f)+'.json')) as fh:
					json1 = json.load(fh)
				with open(os.path.join(self.savedir,v2,os.path.basename(f)+'.json')) as fh:
					json2 = json.load(fh)
				
				for p in range(len(json1)):  # for each page
					
					# check both images' filename and size, should be the same
					if os.path.basename(json1[p]['filename']) != os.path.basename(json2[p]['filename']):
						print('error, filenames are not the same',json1[p]['filename'],json2[p]['filename'])
						continue
					if json1[p]['size'] != json2[p]['size']:
						print('error, image sizes are not the same',json1[p]['size'],json2[p]['size'])
						continue
					
					gutterThreshold = Kumiko.getGutterThreshold(json1[p]['size'])
					panels_v1 = list(map(lambda p: Panel(p, gutterThreshold/2), json1[p]['panels']))
					panels_v2 = list(map(lambda p: Panel(p, gutterThreshold/2), json2[p]['panels']))
					
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
					
					images_dir = f if os.path.isdir(f) else os.path.dirname(f)
					images_dir = os.path.relpath(images_dir,'tests/results')+'/'
					
					if len(known_panels[0]) != len(panels_v1) or len(known_panels[1]) != len(panels_v2):
						files_diff[json1[p]['filename']] = {
							'jsons': [json.dumps([json1[p]]),json.dumps([json2[p]])],
							'images_dir': images_dir,
							'known_panels': [json.dumps(known_panels[0]),json.dumps(known_panels[1])]
						}
			
			print('Found',len(files_diff),'differences')
			
			if not self.options['html']:
				return
			
			print('Generating HTML diff file')
			
			html_diff_file = os.path.join(self.savedir,'diff-'+v1+'-'+v2+'.html')
			diff_file = open(html_diff_file, 'w')
			diff_file.write(HTML.header('Comparing Kumiko results','../../'))
			
			diff_file.write(HTML.nbdiffs(files_diff))
			
			for img in files_diff:
				diff_file.write(HTML.side_by_side_panels(img,files_diff[img]['jsons'],v1,v2,images_dir=files_diff[img]['images_dir'], known_panels=files_diff[img]['known_panels']))
			
			diff_file.write(HTML.footer)
			diff_file.close()
			
			if self.options['browser']:
				subprocess.run([self.options['browser'],html_diff_file])
	


parser = argparse.ArgumentParser(description='Kumiko Tester')

parser.add_argument('action', nargs='?', help="Just 'run' (compute information about files), 'compare' two versions of the code, or both", choices=['run','compare','run_compare'], default='run_compare')

parser.add_argument('-b', '--browser', nargs=1, help='Opens given browser to view the differences when ready (implies --html)', choices=['firefox','konqueror','chromium'])
parser.add_argument('--html', action='store_true', help='Generates an HTML file showing the differences between code versions')

args = parser.parse_args()

tester = Tester({
	'html': args.html or args.browser,
	'browser': args.browser[0] if args.browser != None else False,
})

if args.action in ['run','run_compare']:
	tester.run_all()
if args.action in ['compare','run_compare']:
	tester.compare_all()


