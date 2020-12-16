


class HTML:
	def header(title='',reldir=''):
		return """<!DOCTYPE html>
<html>

<head>
	<title>Kumiko Reader</title>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<script type="text/javascript" src="{reldir}jquery-3.2.1.min.js"></script>
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
	def side_by_side_panels(img,jsons,v1,v2,images_dir,known_panels):
		html = '<h2>{0}</h2><div class="sidebyside"><div class="version">{1}</div><div class="version">{2}</div></div><div class="sidebyside">'.format(img,v1,v2)
		
		oneside = """
			<div id="page{id}" class="kumiko-reader debug"></div>
			<script type="text/javascript">
				var reader = new Reader({{
					container: $('#page{id}'),
					comicsJson: {json},
					images_dir: '{images_dir}',
					known_panels: {known_panels}
				}});
				reader.loadPage(0);
			</script>
			"""
		i = -1
		for js in jsons:
			i += 1
			html += oneside.format(id=HTML.pageId,json=js,images_dir=images_dir,known_panels=known_panels[i])
			HTML.pageId += 1
		
		html += '</div>'
		return html
	
	
	def reader(js,images_dir):
		return """
			<div id="reader" class="kumiko-reader fullpage"></div>
			<script type="text/javascript">
				var reader = new Reader({{
					container: $('#reader'),
					comicsJson: {json},
					images_dir: '{images_dir}',
					controls: true
				}});
				reader.loadPage(0);
			</script>
			""".format(json=js,images_dir=images_dir)
	
	
	footer = """

</body>
</html>
""" 
