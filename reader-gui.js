

$('.menu').toggleClass('hidden');

$(document).ready( function () {
	if (localStorage.debug == 'true')
		$('#result').addClass('debug');
});

// Add tools buttons
$('#result').css({position: 'relative'});
$('#result').append($('<i class="tools prevPanel">←</i>'));
$('#result').append($('<i class="tools nextPanel">→</i>'));
$('#result .nextPanel').css({right:0});
$('#result').append($('<select class="tools pagesel"></select>'));
$('#result .pagesel').css({position: 'absolute', bottom: 0, right:0, 'font-size': '3vmin'});

$('#result').append('<label class="panelpages tools"><input type="checkbox" name="panelview" checked="checked"/><span>□</span><span>▦</span></label>');
$('#result .panelpages').css({position: 'absolute', bottom: 0, left:0});

var reader = new Reader({
	container: $('#result'),
	comicsPath: json_file,
	imageURLs: img_urls,
});
reader.loadPage();

// PREVIOUS AND NEXT PAGE
$(document).delegate( '#result', 'click touch', function() {
	if ($('input[name=panelview]').is(':checked'))
		reader.nextPanel();
	else
		reader.loadNextPage();
});

$(document).delegate( '#result .prevPanel', 'click touch', function(event) {
	if ($('input[name=panelview]').is(':checked'))
		reader.prevPanel();
	else
		reader.loadPrevPage();
	event.stopPropagation();
});

$(document).delegate( '#result .nextPanel', 'click touch', function(event) {
	if ($('input[name=panelview]').is(':checked'))
		reader.nextPanel();
	else
		reader.loadNextPage();
	event.stopPropagation();
});

$(document).keydown(function(e) {
	switch(e.which) {
		case 37: // left
		case 38: // up
			$('#result .prevPanel').click();
			break;

		case 39: // right
		case 40: // down
			$('#result').click();
			break;
		
		case 80: // 'p' key
			$('input[name=panelview]').click();
			break;
		
		default:
			console.log(e.which);
			return; // exit this handler for other keys
	}
	e.preventDefault(); // prevent the default action (scroll / move caret)
});


// PAGE SELECTION
$(document).delegate( '.pagesel', 'change', function(event) {
	if ($(this).val())
		reader.loadPage(parseInt($(this).val()));
	$('.menu').toggleClass('hidden');
});
$(document).delegate( '.tools', 'click', function(event) {
	event.stopPropagation();
});

$(document).delegate('input[name=panelview]', 'change', function() {
	$('.menu').toggleClass('hidden');
	if ($(this).is(':checked'))
		reader.zoomOn($('.panel').eq(0));
	else
		reader.dezoom();
});

$(document).on('kumiko-ready', function () {
	var pages = reader.getPages();
	if (!pages)
		return;
	
	$('.pagesel option').remove();
	for (var page in pages) {
		var sel = page == reader.getCurrentPage() ? 'selected="selected"' : '';
		$('.pagesel').append('<option value="'+page+'" '+sel+'>'+(parseInt(page)+1)+'/'+pages.length+(page == reader.getCurrentPage() ? ' *' : '')+'</option>');
	}
});
