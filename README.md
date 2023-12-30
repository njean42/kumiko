

# Introduction

![Kumiko mascot by Cthulhulumaid](artwork/kumiko-big.png "Kumiko mascot by Cthulhulumaid")

> Kumiko mascot by [Hurluberlue](https://www.twitch.tv/hurluberlue "twitch link"), [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/ "Creative Commons License")

*Kumiko, the Comics Cutter* is a set of tools to compute useful information about comic book pages, panels, and more.
Its main strength is to find out the **locations of panels** within a comic's page (image file).
*Kumiko* can also compile information about panels for all pages in a comic book, and present it as one piece of data (JSON-formatted object).

*Kumiko* makes use of the great (freely licensed) [opencv](https://opencv.org/) library, which provides image processing algorithms of all sorts.
Mainly, the contour detection algorithm is used to detect panels within an image.


# Demo

*TL;WR* Too Long; Won't Read the whole doc?

A **live demo** is [available here](https://kumiko.njean.me/demo), where you can try *Kumiko* out and cut your own comic pages into panels.


# Philosophy

*Kumiko* aims at being a functional library to extract information from comic pages / books.
The goal is to provide a set of tools that is usable beforehand, to extract all needed information.

External programs can later use the generated information for different purposes: panel-by-panel viewing, actual splitting of an image down into panels, etc.


## Panel-by-panel comic reading

Being able to jump from one panel to the next was the original idea behind *Kumiko*.

![xkcd #208](doc/img/xkcd.png "xkcd #208")

> [xkcd](https://www.xkcd.com) by Randall Munroe, [#208](https://www.xkcd.com/208/), [CC BY-NC 2.5](https://creativecommons.org/licenses/by-nc/2.5/)

Comic viewers usually imply a very common *page-by-page reading paradigm*.
You read a page, possibly zooming on it to be able to read speech bubbles, then click, tap, press a key or swipe to the next page.

With knowledge about panels locations, we can imagine a comic reader that also offers *panel-by-panel reading*.
This is especially interesting for **small screens**, on which you probably can't read the texts if a whole page is displayed.

Just run `kumiko -i /path/to/comicpage.jpg -b firefox` on your *comicpage.jpg* file, and read it panel-by-panel in your browser!


# Requirements

`apt-get install python3-opencv` will install the only necessary library needed: *opencv*.

This should do the trick for Debian distros and derivatives (Ubuntu, Linux Mint...).
If you successfully use *Kumiko* on any other platform, please let us know!


# Usage & Testing

See the [usage doc](doc/Usage.md) for details on how to use the *Kumiko* tools.

Also check the [testing doc](doc/Testing.md) if you want to test modified versions of the code.


# Numbering

The numbering is left-to-right, or right-to-left if requested.

Here is an example of how *Kumiko* is going to number panels by default (numbers and red lines not in the original picture).

![Pepper&Carrot](doc/img/numbering.png "Pepper&Carrot")

> [Pepper & Carott](https://www.peppercarrot.com/) by [David Revoy](https://www.davidrevoy.com), [episode 2](https://www.peppercarrot.com/en/article237/episode-2-rainbow-potions), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)


# Contributing

Feature requests and PR are welcome!

*Kumiko* python code if formatted with [yapf](https://github.com/google/yapf).
Config file is committed [here](.style.yapf).

To format all your code, simply run:
```bash
yapf3 --recursive --in-place .
```


# Short- and longer-term features (roadmap)

## Kumiko library

* detect panels on a growing range of comic page layouts
	* detect non-framed panels (without clear boundaries/borders)
	* separate intertwined panels

* ~~be able to detect panel contours on pages with non-white, non-black background~~ done in v1.5

## Back-office (validation / edition tool)

Let's face it: we probably can't ensure that *Kumiko* can perfectly find out the panels in *any* image.
There is a huge diversity of panel boundaries, layouts and whatnot.

This is why there could be some kind of back-office / editing tool that lets a human editor:

* validate pages
* add, delete, move or resize incorrect panels
* report bugs
* ...

Such a tool would edit the JSON file representing a comic book information, for later use by other programs relying on it.
