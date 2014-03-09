# MarkupViewer :sad:
MarkupViewer is a simple previewer for various markup formats. The view will be refreshed when the opened file is saved, allowing you to use whatever editor you’d like and see the results immediately.

## Features
* Cross Platform (tested only on Windows though)
* Updates when the file is changed
* Stylesheet support
* View various markup formats (asterisk determines formats require Pandoc to be installed):
    * Creole
    * DocBook<b>\*</b>
    * Markdown, Pandoc-flavour<b>\*</b>, GitHub-flavour<b>\*</b>
    * reStructuredText
    * LaTeX<b>\*</b>
    * OPML<b>\*</b>
    * Textile
* Linked table of content
* Statistics — words, characters and lines count

## Dependencies
* [Python](http://python.org/) 2.7
* [PyQt4](http://www.riverbankcomputing.com/software/pyqt/download)
* Optional dependencies (any single one of them will be enough for correct support of appropriate format(s); asterisk determines packages are required for support of all declared formats):
    * [python-creole](https://pypi.python.org/pypi/python-creole/1.1.1)<b>\*</b>
    * [pandoc](http://johnmacfarlane.net/pandoc/installing.html)<b>\*</b>
    * [Markdown](http://pypi.python.org/pypi/Markdown)
    * [docutils](https://pypi.python.org/pypi/docutils/0.11)
    * [textile](https://pypi.python.org/pypi/textile/)

## Usage
```
$ python MarkupViewer.py <file>
```

To automatically open a file with this viewer in Windows, associate the filetype with the included `.bat` file.

You can apply styles by dropping your stylesheets in the `stylesheets\` directory next to this script and selecting one from the Style menu.

## Settings
`settings.yaml` offers many options to fiddle with — simply open that file in any plain text editor.  
*NOTE*, options without description are not implemented yet, they’re drafts… tbh, even some with descriptions are still drafts.

## Contributing
Feel free to make improvements. Fork and send me a pull request.

## Credit
The bundled style came from [here](https://github.com/simonlc/Markdown-CSS).


## Licence
© 2013 Matthew Borgerson <mborgerson@gmail.com>  
© 2014 Vova Kolobok <vovkkk@ya.ru>  
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.  
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
