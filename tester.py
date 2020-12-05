#!/usr/bin/env python


import os, subprocess, json, argparse
from kumikolib import Kumiko,Panel
from lib.html import HTML



class Tester:
	
	files = []
	git_repo = 'https://framagit.org/nicooo/kumiko'
	git_versions = [
		#'v1.0',
		#'v1.1',
		'v1.11',
		'current',
	]
	
	def __init__(self, options):
		self.savedir = os.path.join('tests','results')
		if not os.path.isdir(self.savedir):
			raise Exception("'%s' is not a directory" % self.savedir)
		
		self.options = {
			'browser': options['browser'] if 'browser' in options and options['browser'] else False
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
		
		if git_version != 'current':
			tempgit = '/tmp/kumikogit'
			subprocess.run(['rm','-rf',tempgit])
			subprocess.run(['git', 'clone', self.git_repo, tempgit], capture_output=True)
			subprocess.run(['git', 'checkout', git_version], cwd=tempgit, capture_output=True)
			kumiko_bin = os.path.join(tempgit,'kumiko')
		
		subprocess.run(['mkdir','-p',self.savedir])
		
		for f in self.files:
			print("##### Kumiko-cutting",f if isinstance(f,str) else f.name,"#####")
			
			f_savedir = os.path.join(self.savedir,git_version,os.path.basename(f))
			subprocess.run(['mkdir','-p',f_savedir])
			
			jsonfile = os.path.join(self.savedir,git_version,os.path.basename(f)+'.json')
			subprocess.run(args=[kumiko_bin, '-i', f, '-o', jsonfile, '--debug-dir', f_savedir, '--progress'])
	
	
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
					
					is_diff = False
					if len(json1[p]['panels']) != len(json2[p]['panels']):
						is_diff = True
					else:
						gutterThreshold = Kumiko.getGutterThreshold(json1[p]['size'])
						for pan in range(len(json1[p]['panels'])):
							p1 = Panel(json1[p]['panels'][pan], gutterThreshold/2)
							p2 = Panel(json2[p]['panels'][pan], gutterThreshold/2)
							if p1 != p2:
								is_diff = True
								break
					
					images_dir = f if os.path.isdir(f) else os.path.dirname(f)
					images_dir = os.path.relpath(images_dir,'tests/results')+'/'
					
					if is_diff:
						files_diff[json1[p]['filename']] = {
							'jsons': [json.dumps([json1[p]]),json.dumps([json2[p]])],
							'images_dir': images_dir
						}
			
			html_diff_file = os.path.join(self.savedir,'diff-'+v1+'-'+v2+'.html')
			diff_file = open(html_diff_file, 'w')
			diff_file.write(HTML.header('Comparing Kumiko results','../../'))
			
			print('Found',len(files_diff),'differences')
			diff_file.write(HTML.nbdiffs(files_diff))
			
			for img in files_diff:
				diff_file.write(HTML.side_by_side_panels(img,files_diff[img]['jsons'],v1,v2,images_dir=files_diff[img]['images_dir']))
			
			diff_file.write(HTML.footer)
			diff_file.close()
			
			if self.options['browser']:
				subprocess.run([self.options['browser'],html_diff_file])
	


parser = argparse.ArgumentParser(description='Kumiko Tester')

parser.add_argument('-b', '--browser', nargs=1, help='Opens given browser to view the differences when ready', choices=['firefox','konqueror','chromium'])
parser.add_argument('action', nargs='?', help="Just 'run' (compute information about files), 'compare' two versions of the code, or both", choices=['run','compare','run_compare'], default='run_compare')

args = parser.parse_args()

tester = Tester({
	'browser': args.browser[0] if args.browser != None else False,
})

if args.action in ['run','run_compare']:
	tester.run_all()
if args.action in ['compare','run_compare']:
	tester.compare_all()


