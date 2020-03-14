


class Reader {
	
	constructor(options) {
		if (!options.comicsPath) {
			console.error('no comicsPath given in options');
			return;
		}
		if (!options.container || options.container.length == 0) {
			console.error('no container given in options');
			return;
		}
		if (!options.imageURLs) {
			console.error('no imageURLs given in options');
			return;
		}
		
		this.comicsPath = options.comicsPath;
		this.bigimgsize = 1080;
		
		this.imageURLs = options.imageURLs;
		
		// add image sub-container
		this.container = $('<div class="container"/>');
		this.container.css({
			position: 'relative',
			width: '90%',
			height: '90%',
			margin: 'auto',
		});
		options.container.append(this.container);
		
		try {
			this.currpage = JSON.parse(localStorage.currpage);
		} catch (e) {
			this.currpage = {};
		}
		
		if (!this.currpage[this.comicsPath])
			this.currpage[this.comicsPath] = 0;
		
		this.nbDigits = options.nbDigits ? options.nbDigits : 1;
		this.currpanel = 0;
		
		window.addEventListener('orientationchange', function () {
			setTimeout( function () { this.gotoPanel(this.currpanel); }.bind(this), 500);  // slight delay to make it work better, not sure why :)
		}.bind(this));
	}
	
	
	
	loadNextPage() { return this.loadPage(this.currpage[this.comicsPath]+1); }
	loadPrevPage() { return this.loadPage(this.currpage[this.comicsPath]-1); }
	getCurrentPage() { return this.currpage[this.comicsPath]; }
	getPages () {
		return this.comic;
	}
	
	loadPage(page=false) {
		
		// don't go to a page below 0, or above the number of pages in this comic
		if (page == -1)
			return false;
		if (this.comic && page == this.comic.length) {
			this.currpage[this.comicsPath] = this.comic.length-1;
			return false;
		}
		
		if (page === false)
			page = (this.comicsPath in this.currpage) ? this.currpage[this.comicsPath] : 0;
		
		this.currpage[this.comicsPath] = page;
		localStorage.currpage = JSON.stringify(this.currpage);
		
		if (this.comic) {
			this.kumikoReady();
			return true;
		}
		// else
		$.getJSON(this.comicsPath, function (comic) {
			this.comic = comic;
			this.kumikoReady();
		}.bind(this));
		
		return true;
	}
	
	kumikoReady ()
	{
		$(document).trigger('kumiko-ready');
		
		var page = this.currpage[this.comicsPath];
		var imginfo = this.comic[page];
		
		var img = $('<img class="pageimg" src="'+this.imageURLs[page]+'"/>');
		
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
		
		this.container.parent().trigger('page-changed');
	}
	
	zoomOn (panel,callback) {
		
		var growth = this.container.parent().width() / panel.width();
		var max = 'x';
		var ygrowth =  this.container.parent().height() / panel.height();
		
		if (ygrowth < growth) {
			growth = ygrowth;
			max = 'y';
		}
		
		// 			var margin = growth * 0.1;
		var newcss = {
			top:  - panel.position().top  * growth,
			left: - panel.position().left * growth,
			height: this.container.height() * growth,
			width:  this.container.width()  * growth
		};
		
		// center panel horizontally or vertically within container's parent?
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
		var imgsize = this.comic[this.currpage[this.comicsPath]]['size'];
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
	
	drawPanels (imginfo) {
		this.container.children('*:not(.pageimg)').remove();
		
		var [imgw,imgh] = imginfo['size'];
		
		for (var p in imginfo['panels']) {
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
			
			// uncomment the following line to have debug info on panels
			panel.append('<span class="panelnb">'+($('.panel').length + 1)+'</span>');
			// 		panel.append('<span class="top">'+p.top);
			// 		panel.append('<span class="bottom">'+p.bottom);
			// 		panel.append('<span class="left">'+p.left);
			// 		panel.append('<span class="right">'+p.right);
			
			this.container.append(panel);
		}
	}
	
}
