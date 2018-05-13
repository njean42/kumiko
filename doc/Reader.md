

# Example of a panel-by-panel reader application


## Concept

We provide an example implementation of a *panel-by-panel reader* as an example of what *Kumiko* can be used for.
Once the command-line tool has generated a complete JSON representation (see the [usage doc](Usage.md)) of a page panels, our example reader can provide an interface that shows only the first (zoomed) panel of a page, and allows to jump forward to the next panel(s).

Try reading [an *xkcd* episode](../xkcd.html) panel by panel. :)

Use the left and right arrow keys or click-touch the screen to navigate through panels.



## Reader implementation details

See the `reader.js` file for use in a browser or application webview.

Some event bindings are defined in the `xkcd.html` file.
