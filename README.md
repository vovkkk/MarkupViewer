# MarkupViewer
MarkupViewer is a simple previewer for various markup formats. The view will be refreshed when the opened file is saved, allowing you to use whatever editor you’d like and see the results immediately.

![](http://storage6.static.itmages.ru/i/14/0630/h_1404128604_3549738_b3b8c55834.png)


## Features
* Cross Platform (tested only on Windows though)
* Updates when the file is changed
* Auto scroll to changed part
* Stylesheet support
* View various markup formats (asterisk determines formats require Pandoc to be installed):
    * AsciiDoc
    * Creole
    * DocBook<b>\*</b>
    * EPUB<b>\*</b>
    * Markdown, Pandoc-flavour<b>\*</b>, GitHub-flavour<b>\*</b>, PHP Markdown Extra<b>\*</b>
    * MediaWiki<b>\*</b>
    * reStructuredText
    * LaTeX<b>\*</b>
    * Office Open XML<b>\*</b> (aka docx)
    * OPML<b>\*</b>
    * OrgMode<b>\*</b>
    * Textile
    * txt2tags<b>\*</b>
* Linked table of content as a menu or in sidebar (you can filter headers to find one)
* Statistics — words, characters and lines count  
    It, also, tries to count amount of the unique words in a document. However, take the results with a grain of salt — the application has no clue about grammatical cases.
* Drag and drop any file on an existing MV window to preview the file
* Print


## Dependencies
* [Python](https://www.python.org/downloads/) 2.7
* [PyQt4](http://www.riverbankcomputing.com/software/pyqt/download)
* Optional dependencies (any single one of them will be enough for correct support of appropriate format(s); asterisk determines packages are required for support of all declared formats):
    * [PyYAML](https://pypi.python.org/pypi/PyYAML) is needed to read settings, if not installed MV will work using default settings
    * [asciidoc](http://sourceforge.net/projects/asciidoc/)<b>\*</b> (see [`.\asciidoc\README.asciidoc`](asciidoc/README.asciidoc) for details)
    * [python-creole](https://pypi.python.org/pypi/python-creole)<b>\*</b>
    * [pandoc](http://johnmacfarlane.net/pandoc/installing.html)<b>\*</b>
    * [docutils](https://pypi.python.org/pypi/docutils)
    * [Markdown](http://pypi.python.org/pypi/Markdown)
    * [textile](https://pypi.python.org/pypi/textile)


## Usage
```
$ python MarkupViewer.py <file>
```

To automatically open a file with this viewer in Windows, associate the filetype with the included `.bat` file.

You can apply styles by dropping your stylesheets in the `stylesheets\` directory next to this script and selecting one from the Style menu.

### Unicode support
MarkupViewer does support Unicode [and only Unicode] as much as Python2 and PyQt4 allow:

#### Text encoding
Since some of 3rd party software, used for conversion, support _only_ UTF8 encoding (Pandoc, Markdown Python library, etc.) MarkupViewer assumes that file encoding is UTF8, although some software support other encodings (e.g. AsciiDoc, docutils)—MV _ignores_ it.


## Contributing
Feel free to make improvements. Fork and send me a pull request.

### Building standalone app using [PyInstaller](https://github.com/pyinstaller/pyinstaller#installation)
```
$ pyinstaller build.spec
```

Though, docutils and textile packages need to be copied by hand into root of resulted folder `dist\MarkupViewer`
`..\Python27\Lib\site-packages\docutils-0.11-py2.7.egg\docutils`  
`..\Python27\Lib\site-packages\textile-2.1.5-py2.7.egg\textile`


## Credit
The bundled style came from [here](https://github.com/simonlc/Markdown-CSS).


## Licence
© 2013 Matthew Borgerson <mborgerson@gmail.com>  
© 2014 Vova Kolobok <vovkkk@ya.ru>  
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.  
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the [GNU General Public License](http://www.gnu.org/licenses/gpl-2.0.html) for more details.

<hr>

markup.ico is based on [the markdown mark](https://github.com/dcurtis/markdown-mark) and dedicated to the public domain.

### Font Awesome under [SIL](http://scripts.sil.org/cms/scripts/page.php?site_id=nrsi&id=OFL)
© 2012 Dave Gandy <http://fortawesome.github.com/Font-Awesome>

### Entypo under [CC BY-SA](http://creativecommons.org/licenses/by-sa/2.0/)
© 2012 Daniel Bruce <http://www.entypo.com>
