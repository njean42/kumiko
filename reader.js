


class Reader {
	
	constructor(options)
	{
		// Mandatory options
		if (!options.container || options.container.length == 0) {
			console.error('no container given in options');
			return;
		}
		
		if (!options.images_dir) {
			console.error('no images_dir given in options');
			return;
		}
		this.images_dir = options.images_dir
		
		if (!options.comicsJson || typeof options.comicsJson != 'object') {
			console.error('no comicsJson given in options, or not a javascript object');
			return;
		}
		this.comic = options.comicsJson;
		
		// add image sub-container
		this.container = $('<div class="container"/>');
		this.container.css({
			position: 'relative',
			width: '95%',
			height: '95%',
			margin: 'auto',
		});
		options.container.append(this.container);
		
		this.currpage = 0;
		this.currpanel = 0;
		
		window.addEventListener('orientationchange', function () {
			setTimeout( function () { this.gotoPanel(this.currpanel); }.bind(this), 500);  // slight delay to make it work better, not sure why :)
		}.bind(this));
	}
	
	
	loadNextPage() { return this.loadPage(this.currpage+1); }
	loadPrevPage() { return this.loadPage(this.currpage-1); }
	loadPage(page=0)
	{
		// don't go to a page below 0, or above the number of pages in this comic
		if (page < 0 || page >= this.comic.length)
		{
			console.error('Willing to go to page',page,'but is does not exist');
			return false;
		}
		
		var imginfo = this.comic[page];
		var imgurl = this.images_dir + imginfo.filename.split('/').reverse()[0];
		
		var img = $('<img class="pageimg" src="'+imgurl+'"/>');
		img.css({
			position: 'absolute',
			'width': '100%',
			'height': '100%'
		});
		
		this.container.children('img').remove();
		this.container.prepend(img);
		
		this.drawPanels(imginfo);
		this.dezoom();
		
		if (this.currpanel == 'last')
			this.currpanel = $('.panel').length-1;
		else
			this.currpanel = 0;
		
		if ($('input[name=panelview]').is(':checked'))
			this.gotoPanel(this.currpanel);
	}
	
	zoomOn (panel,callback)
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
		this.container.animate(newcss,300,callback);
	}
	
	dezoom () {
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
	
	getImgSize () {
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
	
	gotoPanel (i) {
		$(window).scrollTop( $('#result').position().top )
		
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
		
		var i =1;
		for (var p in imginfo['panels'])
		{
			p = imginfo['panels'][p];
			var [x,y,w,h] = p;
			
			var panel = $('<div class="panel"><!-- --></div>');
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
	
}
