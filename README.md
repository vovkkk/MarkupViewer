MarkdownViewer
==============
MarkdownViewer is a simple Markdown file viewer written in Python. I wanted an
easy way to view Markdown files, so I hacked this together...it isn't pretty,
but it is functional. The view will be refreshed when the opened file is saved,
allowing you to use whatever editor you'd like and see the results immediately.

Features
--------
* Cross Platform
* Updates when the file is changed
* Stylesheet support

Dependencies
------------
* [Python](http://python.org/) 2.6 or 2.7
* [PyQt4](http://www.riverbankcomputing.com/software/pyqt/download)
* [Markdown Python Package](http://pypi.python.org/pypi/Markdown) (Available via PIP)

Usage
-----
  ```
  $ python MarkdownViewer.py <file>
  ```

  To automatically open a Markdown file with this viewer in Windows, associate
  the filetype with the included .bat file. You can apply styles by dropping
  your stylesheets in the stylesheets/ directory next to this script and
  selecting one from the Style menu.

Contributing
------------
Feel free to make improvements. Fork and send me a pull request.

Credit
------
The bundled style came from [here](https://github.com/simonlc/Markdown-CSS).

More Info
---------
Learn more about Markdown and the Markdown syntax [here](http://daringfireball.net/projects/markdown/).
