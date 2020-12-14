
# Command-line usage


## Help

More detailed help can be found by running `kumiko --help`.


## Get panel information for one page (image file)

	kumiko -i /path/to/comicbook/page001.jpg

(Add `-b firefox` to view the panels, on top of given image, in your browser! 'Show panels' option is in the menu.)

The result would look like the following:

	[
		{
			"filename": "comicbook/page001.jpg",
			"size": [1920,2549],
			"panels": [
				[148,108,1628,874],
				[147,999,358,538],
				...
			]
		}
	]

(Note that the resulting JSON-formatted data is already a list, with just one object representing the extracted information about our image.
This is for compatibility with generating information for several pages in one directory, see next section.)

### Panels

The *size* gives us the *[width,height]* of our image, in pixels.

The panel details are also expressed in pixels.
The 4 values representing a panel are given in the following order: **[x,y,width,height]**, with *x* and *y* representing the **top-left corner** of the panel.

Note that, although Kumiko can detect panels with arbitrary shapes, it will return a rectangular bounding box for each one.
This is because in the end, many things are rectangular: image files, our screens to display them...
We may want an option in the future to get more accurate polygons instead.

### File names

The `filename`s in our JSON object are relative to the working directory from which we invoked the `./kumiko` command.


## Get panel information for all pages in one comic book

	kumiko -i /path/to/comicbook/

(Add `-b firefox` to view the panels for all pages, on top of your images, in your browser! 'Show panels' option is in the menu.)

The result of such a command would be a JSON-formatted array of all images in the folder:

	[
		{
			"filename": "comicbook/page001.jpg",
			"size": [1920,2549],
			"panels": [
				[148,108,1628,874],
				[147,999,358,538],
				...
			]
		},
		{
			"filename": "comicbook/page002.jpg",
			"size": [1920,2550],
			"panels": [
				[149,109,1631,737],
				...
			]
		}
		...
	]

The image order is alphabetical, which is based on a commonly encountered *page001, page002, ...* naming for pages.


## Debug

You can pass `kumiko` a `--debug-dir /path/to/debug-info` parameter that tells you are craving debugging information.

This will create an image for each page that Kumiko analysed, renamed `$filename-contours.jpg`.
These files will be found in the `/path/to/debug-info` folder (should exist and be writable).
Panel contours and image numbering is drawn onto every debugging image.


## License information

License information may be provided in a text file under the same directory as each image (named `myimage.jpg.license`).
It must be valid JSON data and will be available under a `license` key in the resulting JSON, for each image.

The fields known to our javascript reader are the following:

	{
		"title": "this image name",
		"title_link": "a link to where this file can be found",
		"author": "the author of this image",
		"author_link": "a link to the author's web page",
		"licence": "this image license",
		"licence_link": "a link to the license"
	}
