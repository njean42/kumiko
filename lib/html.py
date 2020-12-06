

from lib.panel import Panel


class HTML:
	def header(title='',reldir=''):
		return """<!DOCTYPE html>
<html>

<head>
	<meta charset="utf-8">
	<script type="text/javascript" src="{reldir}jquery-3.2.1.min.js"></script>
	<script type="text/javascript" src="{reldir}jquery.touchSwipe.min.js"></script>
	<script type="text/javascript" src="{reldir}reader.js"></script>
	<link rel="stylesheet" media="all" href="{reldir}style.css" />
	<style type="text/css">
		h2 {{ text-align: center; }}
		.sidebyside {{ display: flex; justify-content: space-around; }}
		.sidebyside > div {{ width: 45%; }}
		.version {{ text-align: center; }}
		.kumiko-reader {{ height: 90vh; }}
		.kumiko-reader.fullpage {{ height: 100%; width: 100%; }}
	</style>
</head>

<body>
<h1>{title}</h1>

""".format(title=title,reldir=reldir)
	
	
	def nbdiffs(files_diff):
		return "<p>{0} differences found in files</p>".format(len(files_diff))
	
	
	pageId = 0
	def side_by_side_panels(img,jsons,v1,v2,images_dir):
		html = '<h2>{0}</h2><div class="sidebyside"><div class="version">{1}</div><div class="version">{2}</div></div><div class="sidebyside">'.format(img,v1,v2)
		
		oneside = """
			<div id="page{id}" class="kumiko-reader debug"></div>
			<script type="text/javascript">
				var reader = new Reader({{
					container: $('#page{id}'),
					comicsJson: {json},
					images_dir: '{images_dir}'
				}});
				reader.loadPage(0);
			</script>
			"""
		for js in jsons:
			html += oneside.format(id=HTML.pageId,json=js,images_dir=images_dir)
			HTML.pageId += 1
		
		html += '</div>'
		return html
	
	
	def reader(js,images_dir,debug):
		debug = 'debug' if debug else ''
		return """
			<div id="reader" class="kumiko-reader {debug} fullpage"></div>
			<script type="text/javascript">
				var reader = new Reader({{
					container: $('#reader'),
					comicsJson: {json},
					images_dir: '{images_dir}'
				}});
				reader.loadPage(0);
			</script>
			""".format(json=js,images_dir=images_dir,debug=debug)
	
	
	footer = """

</body>
</html>
""" 
