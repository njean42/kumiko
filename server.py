#!/usr/bin/env python3

import os
import json
from bottle import route, run, request, static_file, abort
from kumikolib import Kumiko
from lib.html import HTML

static_files = {
	'jquery-3.2.1.min.js': True,
	'reader.js': True,
	'style.css': True,
}


@route('/html', method = 'GET')
def html():
	url = request.query.url
	name, ext = os.path.splitext(url)
	if ext.lower() not in ('.png', '.jpg', '.jpeg'):
		return "File extension not allowed."

	k = Kumiko()
	k.parse_url_list([url])

	infos = json.dumps(k.get_infos())

	return f"""
		{HTML.header(reldir = '/static/')}
		{HTML.reader(infos, images_dir = 'urls')}
		{HTML.footer}
		"""


@route('/static/<filename>', method = 'GET')
def static(filename):
	if filename not in static_files:
		abort(404, "Not Found")

	return static_file(filename, root = './')


run(host = '127.0.0.1', port = 8091)
