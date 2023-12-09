

import json


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
		h2, h3 {{ text-align: center; margin-top: 3em; }}
		.sidebyside {{ display: flex; justify-content: space-around; }}
		.sidebyside > div {{ width: 45%; }}
		.version, .step-info {{ text-align: center; }}
		.kumiko-reader.halfwidth {{ max-width: 45%; }}
		.kumiko-reader.fullpage {{ width: 100%; height: 100%; }}
	</style>
</head>

<body>
<h1>{title}</h1>

""".format(title=title,reldir=reldir)
	
	
	def nbdiffs(files_diff):
		return "<p>{0} differences found in files</p>".format(len(files_diff))
	
	
	pageId = 0
	def side_by_side_panels(title,step_info,jsons,v1,v2,images_dir,known_panels,diff_numbering_panels):
		html = """
			<h2>{0}</h2>
			<p class="step-info">{1}</p>
			<div class="sidebyside">
				<div class="version">{2}</div>
				<div class="version">{3}</div>
			</div>
			<div class="sidebyside">
		""".format(title,step_info,v1,v2)
		
		oneside = """
			<div id="page{id}" class="kumiko-reader halfwidth debug"></div>
			<script type="text/javascript">
				var reader = new Reader({{
					container: $('#page{id}'),
					comicsJson: {json},
					images_dir: '{images_dir}',
					known_panels: {known_panels},
					diff_numbering_panels: {diff_numbering_panels},
				}});
				reader.start();
			</script>
			"""
		i = -1
		for js in jsons:
			i += 1
			html += oneside.format(id=HTML.pageId,json=json.dumps(js),images_dir=images_dir,known_panels=known_panels[i],diff_numbering_panels=diff_numbering_panels)
			HTML.pageId += 1
		
		html += '</div>'
		return html
	
	
	def imgbox(images):
		html = "<h3>Debugging images</h3>\n<div class='imgbox'>\n";
		for img in images:
			html += "\t<div><p>{}</p><img src='{}' /></div>\n".format(img['label'],img['filename'])
		
		return html + "</div>\n\n"
	
	
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
				reader.start();
			</script>
			""".format(json=js,images_dir=images_dir)
	
	
	footer = """

</body>
</html>
""" 
