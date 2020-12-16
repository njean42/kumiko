


class Reader {
	
	constructor(options)
	{
		// Mandatory options
		if (!options.container || options.container.length == 0) {
			console.error('no container given in options');
			return;
		}
		this.gui = options.container;
		this.gui.data('reader',this);
		
		if (!options.images_dir) {
			console.error('no images_dir given in options');
			return;
		}
		this.images_dir = options.images_dir;
		
		if (!options.comicsJson || typeof options.comicsJson != 'object') {
			console.error('no comicsJson given in options, or not a javascript object');
			return;
		}
		this.comic = options.comicsJson;
		
		this.known_panels = options.known_panels ? options.known_panels : [];
		
		// init attributes
		this.currpage = 0;
		this.currpanel = 0;
		this.debug = this.gui.hasClass('debug') || window.location.hash == '#debug';
		if (this.debug)
			this.gui.addClass('debug');
		
		// add image sub-container
		this.container = $('<div class="container"/>');
		this.container.css({
			position: 'relative',
			width: '95%',
			height: '95%',
			margin: 'auto',
		});
		this.gui.append(this.container);
		
		if ('controls' in options && options['controls'])
			this.add_controls();
		
		window.addEventListener('orientationchange', function () {
			setTimeout( function () { this.gotoPanel(this.currpanel); }.bind(this), 500);  // slight delay to make it work better, not sure why :)
		}.bind(this));
	}
	
	next()
	{
		if (this.container.is('.zoomed'))
			this.nextPanel();
		else
			this.loadNextPage();
	}
	prev()
	{
		if (this.container.is('.zoomed'))
			this.prevPanel();
		else
			this.loadPrevPage();
	}
	
	loadNextPage() { return this.loadPage(this.currpage+1); }
	loadPrevPage() { return this.loadPage(this.currpage-1); }
	loadPage(page=0)
	{
		// don't go to a page below 0, or above the number of pages in this comic
		if (page < 0 || page >= this.comic.length)
			return false;
		
		this.currpage = page;
		
		$('.pagenb',this.gui).html('page '+(page+1)+' <small>/'+this.comic.length+'</small>')
		
		var imginfo = this.comic[page];
		var imgurl = this.images_dir == 'urls' ? imginfo.filename : this.images_dir + imginfo.filename.split('/').reverse()[0];
		
		var img = $('<img class="pageimg" src="'+imgurl+'"/>');
		img.css({
			position: 'absolute',
			'width': '100%',
			'height': '100%'
		});
		
		this.container.children('img').remove();
		this.container.prepend(img);
		
		// show license
		var license = this.get_license(imginfo);
		if (license)
		{
			this.gui.append('<span class="license"/>');
			this.gui.children('.license').html(license);
		}
		else
			$('.license',this.gui).remove();
		
		var was_zoomed = this.container.is('.zoomed');
		
		this.drawPanels(imginfo);
		this.dezoom();
		
		if (this.currpanel == 'last')
			this.currpanel = $('.panel').length-1;
		else
			this.currpanel = 0;
		
		if (was_zoomed)
			this.gotoPanel(this.currpanel);
		
		return true;
	}
	
	zoomOn (panel)
	{
		var growth = this.container.parent().width() / panel.width();
		var max = 'x';
		var ygrowth =  this.container.parent().height() / panel.height();
		
		if (ygrowth < growth) {
			growth = ygrowth;
			max = 'y';
		}
		
		var newcss = {
			top:  - panel.position().top  * growth,
			left: - panel.position().left * growth,
			height: this.container.height() * growth,
			width:  this.container.width()  * growth
		};
		
		// center panel horizontally or vertically within container's parent
		if (max == 'x')
			newcss.top  += (this.container.parent().height() - panel.height() * growth) / 2;
		else
			newcss.left += (this.container.parent().width()  - panel.width()  * growth) / 2;
		
		$('.panel.zoomTarget').removeClass('zoomTarget');
		panel.addClass('zoomTarget');
		
		this.container.addClass('zoomed');
		this.container.animate(newcss,300);
	}
	
	dezoom ()
	{
		var size = this.getImgSize();
		
		var newcss = {
			width: size.w,
			height: size.h,
			left: 0,
			top: 0
		};
		this.container.removeClass('zoomed');
		this.container.css(newcss);
	}
	
	getImgSize ()
	{
		var size = {
			w: this.container.parent().width(),
			h: this.container.parent().height()
		};
		
		var imgsize = this.comic[this.currpage]['size'];
		var ratio = imgsize[0] / imgsize[1];
		if (size.w > size.h * ratio)
			size.w = size.h * ratio;
		else if (size.h > size.w / ratio)
			size.h = size.w / ratio;
		
		return size;
	}
	
	gotoPanel (i)
	{
		if (i < 0) {
			this.currpanel = 'last';
			var prevpage = this.loadPrevPage();
			if (!prevpage)
				this.currpanel = 0;
			return;
		}
		var newPanel = $('.panel').eq(i);
		if (newPanel.length > 0)
			this.zoomOn(newPanel);
		else {
			var nextpage = this.loadNextPage();
			if (!nextpage)
				this.currpanel--;
		}
	}
	nextPanel () { this.currpanel++; this.gotoPanel(this.currpanel); }
	prevPanel () { this.currpanel--; this.gotoPanel(this.currpanel); }
	
	drawPanels (imginfo)
	{
		this.container.children('*:not(.pageimg)').remove();
		
		var [imgw,imgh] = imginfo['size'];
		
		var i = 1;
		for (var p in imginfo['panels'])
		{
			var unknown = !this.known_panels.includes(parseInt(p));
			p = imginfo['panels'][p];
			var [x,y,w,h] = p;
			
			var panel = $('<div class="panel"><!-- --></div>');
			if (unknown)
				panel.addClass('unknown');
			var panelcss = {
				top: '' + y/imgh*100 + '%',
				left: '' + x/imgw*100 + '%',
				height: '' + h/imgh*100 + '%',
				width: '' + w/imgw*100 + '%'
			};
			panel.css(panelcss);
			
			panel.append('<span class="panelnb">'+(i++)+'</span>');
			panel.append('<span class="top">'+y);
			panel.append('<span class="bottom">'+(y+h));
			panel.append('<span class="left">'+x);
			panel.append('<span class="right">'+(x+w));
			
			this.container.append(panel);
		}
	}
	
	add_controls()
	{
		var _reader = this;
		// add controls and page info
		this.gui.append('<span class="pagenb"/>');
		
		var burger = $('<i class="burger">☰</i>');
		burger.data('reader',this);
		burger.on('click touch', function (e) { $(this).data('reader').showMenu(); });
		this.gui.append(burger);
		
		var btprev = $('<i class="prev">←</i>');
		btprev.data('reader',this);
		btprev.on('click touch', function (e) { $(this).data('reader').prev(); });
		this.gui.append(btprev);
		
		var menu = $('<div class="menu"/>');
		var menuul = $('<ul/>');
		menuul.append('<li><label><input type="radio" name="viewmode" value="page"  autocomplete="off" />Page</label></li>');
		menuul.append('<li><label><input type="radio" name="viewmode" value="panel" autocomplete="off" />Panel</label></li>');
		menu.append(menuul);
		
		var btn_debug = $('<label><input type="checkbox" class="toggleDebug" autocomplete="off" />Show panels</label>');
		btn_debug.children('.toggleDebug').on('change', function () { _reader.gui.toggleClass('debug'); });
		menuul.append(btn_debug);
		
		menuul.append('<i class="exit">X</i>');
		menuul.children('.exit').on('click touch', function () { _reader.showMenu(false); })
		
		this.gui.append(menu);
		this.showMenu(false);
		
		$(document).ready( function () {
			var mode = _reader.debug ? 'page' : 'panel';
			$('input[name=viewmode][value='+mode+']',  _reader.gui).prop('checked',true).change();
		});
	}
	
	get_license(page)
	{
		if (!page.license)
			return '';
		
		var html = [];
		for (var i=0; i < 3; i++)
		{
			var k = ['title','author','license'][i];
			if (k in page.license)
			{
				var elt = page.license;
				html.push(
					{title:'',author:'by ',license:''}[k] +
					(elt[k+'_link'] ? '<a target="_blank" href="'+elt[k+'_link']+'">'+elt[k]+'</a>' : elt[k])
				);
			}
		}
		return html.join(', ');
	}
	
	showMenu(show=true)
	{
		if (show)
			this.gui.children('.menu').show();
		else
			this.gui.children('.menu').hide();
	}
}


// Change view mode
$(document).delegate( 'input[name=viewmode]', 'change', function () {
	if (!$(this).is(':checked'))
		return;
	
	var reader = $(this).parents('.kumiko-reader:eq(0)').data('reader');
	switch ($(this).val()) {
		case 'page':
			reader.dezoom();
			break;
		case 'panel':
			reader.gotoPanel(0);
			break;
	}
	reader.container.focus();
});

// Next panel on simple click
$(document).delegate( '.kumiko-reader', 'click touch', function (e) {
	if ($(e.target).is('.panel,.kumiko-reader'))
		$(this).data('reader').next();
});

// Prevent click on page when clicking on license links
$(document).delegate( '.license a', 'click touch', function (e) {
	e.stopPropagation();
});


/**** KEYBOARD NAVIGATION ****/

$(document).keydown(function(e) {
	if (e.altKey)  // alt+left is shortcut for previous page, don't  prevent it
		return;
	
	switch(e.which) {
		case 37: // left
			reader.prev();
			break;
			
		case 39: // right
			reader.next();
			break;
		
		case 80: // 'p' key: switch between page and panel reading
			$('input[name=viewmode]:not(:checked)').prop('checked',true).change();
			break;
		
		default:
			return; // exit this handler for other keys
	}
	e.preventDefault();
});
