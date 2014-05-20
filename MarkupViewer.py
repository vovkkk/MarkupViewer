#!python2
# coding: utf8

import sys, time, os, webbrowser, importlib, itertools, locale, io, yaml, subprocess, threading, shutil
from PyQt4 import QtCore, QtGui, QtWebKit

sys_enc = locale.getpreferredencoding()


class Settings:
    def __init__(self):
        self.user_source = os.path.join(os.getenv('APPDATA'), 'MarkupViewer/settings.yaml')
        self.app_source  = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'settings.yaml')
        self.settings_file = self.user_source if os.path.exists(self.user_source) else self.app_source
        self.reload_settings()
        thread2 = threading.Thread(target=self.watch_settings)
        thread2.setDaemon(True)
        thread2.start()

    @classmethod
    def get(cls, key='', default_value=''):
        return cls().settings.get(key, default_value)

    def reload_settings(self):
        with io.open(self.settings_file, 'r', encoding='utf8') as f:
            self.settings = yaml.safe_load(f)

    def watch_settings(self):
        last_modified = 0
        while True:
            current_modified = os.path.getmtime(self.settings_file)
            if last_modified != current_modified:
                last_modified = current_modified
                self.reload_settings()
            time.sleep(1)

    def edit_settings(self):
        if not os.path.exists(self.user_source):
            os.makedirs(os.path.dirname(self.user_source))
            shutil.copy2(self.app_source, self.user_source)
            self.settings_file = self.user_source
        return self.settings_file


class SetuptheReader:
    """a knot of methods related to readers: which one need to be used, is it available etc.
    basic usecase:
        reader, writer = SetuptheReader._for(filename)
        html = writer(unicode_object)
    """
    readers = Settings.get('formats')

    @classmethod
    def _for(self, filename):
        file_ext = filename.split('.')[-1].lower()
        return self.is_available(self.reader(file_ext))

    @classmethod
    def mapping_formats(self, readers=''):
        ''' get    dict {'reader1': 'ext1 ext2 ...', ...}
            return dict {'ext1': 'reader1', ...}'''
        # why: make it simple for user to redefine readers for file extensions
        omg = lambda d: itertools.imap(lambda t: (t, d[0]), d[1].split())
        return {e: r for e, r in itertools.chain(*itertools.imap(omg, readers.iteritems()))}

    @classmethod
    def readers_names(self):
        return self.readers.keys()

    @classmethod
    def reader(self, file_ext):
        formats = self.mapping_formats(self.readers)
        if file_ext in formats.keys():
            reader = formats[file_ext]
        else:
            reader = Settings.get('no_extension')
        return reader

    @classmethod
    def is_available(self, reader):
        via_pandoc = Settings.get('via_pandoc')
        if via_pandoc and (reader != 'creole') and (reader != 'asciidoc'):
            try:            subprocess.call(['pandoc', '-v'], shell=True)
            except OSError: via_pandoc = False
            else:           return (reader, 'pandoc')
        elif not via_pandoc or reader == 'creole' or reader == 'asciidoc':
            writers = {
                'asciidoc': ('asciidoc.asciidocapi', 'AsciiDocAPI'),
                'creole'  : ('creole',        'creole2html'),
                'markdown': ('markdown',      'markdown'),
                'rst'     : ('docutils.core', 'publish_parts'),
                'textile' : ('textile',       'textile')
                }
            fail = (KeyError, ImportError)
            try:
                writer = getattr(importlib.import_module(writers[reader][0]), writers[reader][1])
            except fail as e:
                print(reader, str(e))
                return (reader, False)
            else:
                print(reader, writer)
                return (reader, writer)


script_dir = os.path.dirname(os.path.realpath(__file__))
stylesheet_dir = os.path.join(script_dir, 'stylesheets/')
stylesheet_default = Settings.get('style')


class App(QtGui.QMainWindow):
    def __init__(self, parent=None, filename=''):
        QtGui.QMainWindow.__init__(self, parent)
        # Configure the window
        # TODO: remember/restore geometry in/from @settings
        self.setGeometry(0, 488, 640, 532)
        self.setWindowTitle(u'%s — MarkupViewer' % unicode(os.path.abspath(filename) if Settings.get('show_full_path', True) else os.path.basename(filename), sys_enc))
        self.setWindowIcon(QtGui.QIcon('icons/markup.ico'))
        try: # separate icon in the Windows dock
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('MarkupViewer')
        except: pass
        # Add the WebView control
        self.web_view = QtWebKit.QWebView()
        self.setCentralWidget(self.web_view)
        # Start the File Watcher Thread
        self.thread1 = WatcherThread(filename if filename else os.path.join(os.path.dirname(os.path.realpath(__file__)), 'README.md'))
        self.connect(self.thread1, QtCore.SIGNAL('update(QString)'), self.update)
        self.thread1.start()
        self.filename = filename
        self.update('')
        # Open links in default browser
        # TODO: ¿ non-default browser @settings ?
        self.web_view.linkClicked.connect(lambda url: webbrowser.open_new_tab(url.toString()))
        # drag&drop
        self.web_view.setAcceptDrops(True)
        setattr(self.web_view, 'dragEnterEvent', self.dragEnterEvent)
        setattr(self.web_view, 'dropEvent', self.dropEvent)
        # ui
        self.menu_bar()
        self.search_panel()

    def dragEnterEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        fn = event.mimeData().urls()[0].toLocalFile().toLocal8Bit().data()
        self.filename = self.thread1.filename = fn
        self.setWindowTitle(u'%s — MarkupViewer' % unicode(os.path.abspath(fn) if Settings.get('show_full_path', True) else os.path.basename(fn), sys_enc))

    def edit_file(self, fn):
        if not fn: fn = self.filename
        args = Settings.get('editor', 'notepad').split() + [fn]
        try:    subprocess.Popen(args)
        except:
            try:    subprocess.Popen(['notepad', fn])
            except: QtGui.QMessageBox.critical(self,
                        'MarkupViewer cannot find a text editor',
                        'Change <code>editor</code> field in <code>settings.yaml</code> file.<br><br>'
                        'It can be found in <pre>{0}</pre> or in <pre>{1}</pre> it is editable in any text editor.'
                        .format(*(os.path.normpath(s) for s in (Settings().user_source, Settings().app_source)))
                    )

    def save_html(self):
        formats = '*.html;;*;;*.pdf;;*.md;;*.txt%s' % (';;*.odt;;*.docx;;*.rtf;;*.epub;;*.epub3;;*.fb2' if Settings.get('via_pandoc', False) else '')
        new_file = unicode(QtGui.QFileDialog.getSaveFileName(self, 'Save file', os.path.dirname(self.filename), formats))
        ext = os.path.splitext(new_file)[1]
        if ext == ('.html' or ''):
            with io.open(new_file, 'w', encoding='utf8') as f:
                f.writelines(unicode(self.current_doc.toHtml()))
        elif ext == '.pdf':
            QtGui.QMessageBox.critical(self, 'Yo', '<a href="http://i0.kym-cdn.com/photos/images/original/000/284/529/e65.gif">AiNT NOBODY GOT TiME FOR DAT</a>')
        elif ext:
            reader, _ = SetuptheReader._for(self.filename)
            pandoc_path = Settings.get('pandoc_path')
            args = ('%s -s --from=%s --to=%s'%(pandoc_path, reader, ext[1:])).split() + [self.filename, '--output=%s' % new_file]
            try:    subprocess.Popen(args)
            except: QtGui.QMessageBox.critical(self, 'Cannot find pandoc',
                        'Please, install <a href="http://johnmacfarlane.net/pandoc/installing.html">Pandoc</a>.<br>'
                        'If it is installed for sure, check if it is in PATH or change <code>pandoc_path</code> in settings.')
        else:
            return

    def update(self, text):
        self.web_view.settings().setAttribute(3, Settings.get('plugins', False))
        self.web_view.settings().setAttribute(7, Settings.get('inspector', False))
        prev_doc    = self.web_view.page().currentFrame()
        prev_size   = prev_doc.contentsSize()
        prev_scroll = prev_doc.scrollPosition()
        self.web_view.setHtml(text, baseUrl=QtCore.QUrl('file:///'+unicode(os.path.join(os.getcwd(), self.filename).replace('\\', '/'), sys_enc)))
        self.current_doc  = self.web_view.page().currentFrame()
        current_size = self.current_doc.contentsSize()
        if prev_scroll.y() > 0: # self.current_doc.scrollPosition() is always 0
            ypos = prev_scroll.y() - (prev_size.height() - current_size.height())
            self.current_doc.scroll(0, ypos)
        # Delegate links to default browser
        self.web_view.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)
        self.web_view.loadFinished.connect(self.stats_and_toc)
        self.web_view.page().linkHovered.connect(lambda link:self.setToolTip(link))

    def stats_and_toc(self):
        # Statistics:
        u'''This is VERY big deal. For instance, how many words:
                « un lien »
            Two? One? many markdown editors claims that it’s four (sic!) words… ugh…
            Another examples:
                1.5 litres (English)
                1,5 литра (Russian)
                10.000 = 10,000 = 10 000
            Unfortunately, even serious software (e.g. http://liwc.net) fails to
            count properly. The following implementation is not perfect either,
            still, more accurate than many others.
            TODO: statistics — decimals is a huge problem
        '''
        text  = unicode(self.current_doc.toPlainText())
        filtered_text = text.replace('\'', '').replace(u'’', '')
        filtered_text_2 = ''
        for c in filtered_text:
            if c not in u'"…!?¡¿/\\*,‘”“„«»—&\n':
                filtered_text_2 += c
            else:
                filtered_text_2 += ' '
        filtered_text = filtered_text_2.replace('...', ' ')
        words = filtered_text.split()
        lines = text.split('\n')
        text  = text.replace('\n', '')
        self.stats_menu.clear()
        if len(text) > 0:
            self.stats_menu.setDisabled(False)
            self.stats_menu.setTitle( str(len(words)) + ' &words')
            self.stats_menu.addAction(str(len(text))  + ' characters')
            self.stats_menu.addAction(str(len(lines)) + ' lines')
            unique_words = []
            # lame; incorrect for any lang with grammar cases
            for w in words:
                if any(c for c in '(){}[]<>,.' if c in w):
                    unique_words.append(''.join(c for c in w.lower() if c not in '(){}[]<>,.'))
                else:
                    unique_words.append(w.lower())
            self.stats_menu.addAction(str(len(set(unique_words))) + ' unique words')
        else:
            self.stats_menu.setDisabled(True)
            self.stats_menu.setTitle('Statistics')
        # TOC
        self.toc.clear()
        self.toc.setDisabled(True)
        headers = []
        def examineChildElements(parentElement):
            element = parentElement.firstChild()
            while not element.isNull():
                if element.tagName()[0] == 'H' and len(element.tagName()) == 2 and not 'HR' in element.tagName():
                    headers.append(element)
                examineChildElements(element)
                element = element.nextSibling()
        examineChildElements(self.current_doc.documentElement())
        for n, h in enumerate(headers, start=1):
            try:
                indent = int(h.tagName()[1:])
            except ValueError: # cannot make it integer, means no headers
                print(h.tagName())
                break
            else:
                self.toc.setDisabled(False)
            vars(self)['toc_nav%d'%n] = QtGui.QAction(QtGui.QIcon('icons/h%d.png'%indent),'%s%s'% ('  '*indent, h.toPlainText()), self)
            vars(self)['toc_nav%d'%n].triggered[()].connect(lambda header=h: self._scroll(header))
            self.toc.addAction(vars(self)['toc_nav%d'%n])

    def _scroll(self, header):
        self.current_doc.setScrollPosition(QtCore.QPoint(0, header.geometry().top()))

    def set_stylesheet(self, stylesheet='default.css'):
        # QT only works when the slashes are forward??
        full_path = 'file://' + os.path.join(stylesheet_dir, stylesheet)
        full_path = full_path.replace('\\', '/')
        url = QtCore.QUrl(full_path)
        self.web_view.settings().setUserStyleSheetUrl(url)

    def show_search_panel(self):
        self.addToolBar(0x8, self.search_bar)
        self.search_bar.show()
        self.field.setFocus()
        self.field.selectAll()

    def find(self, text, btn=''):
        p = self.web_view.page()
        back = p.FindFlags(1) if btn is self.prev else p.FindFlags(0)
        case = p.FindFlags(2) if self.case.isChecked() else p.FindFlags(0)
        wrap = p.FindFlags(4) if self.wrap.isChecked() else p.FindFlags(0)
        high = p.FindFlags(8) if self.high.isChecked() else p.FindFlags(0)
        p.findText('', p.FindFlags(8)) # clear prev highlight
        p.findText(text, back | wrap | case | high)

    def menu_bar(self):
        # TODO: hide menu?
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')

        saveAction = QtGui.QAction(u'&Save as…', self)
        saveAction.setShortcut('Ctrl+s')
        saveAction.triggered.connect(self.save_html)
        fileMenu.addAction(saveAction)

        editAction = QtGui.QAction(QtGui.QIcon('icons/feather.png'), '&Edit the original', self)
        editAction.setShortcut('Ctrl+e')
        editAction.triggered[()].connect(lambda fn='': self.edit_file(fn))
        fileMenu.addAction(editAction)

        searchAction = QtGui.QAction(u'&Find on the page…', self)
        searchAction.setShortcut('Ctrl+f')
        searchAction.triggered.connect(self.show_search_panel)
        fileMenu.addAction(searchAction)

        settingsAction = QtGui.QAction('Set&tings', self)
        settingsAction.setShortcut('Ctrl+t')
        settingsAction.triggered[()].connect(lambda: self.edit_file(Settings().edit_settings()))
        fileMenu.addAction(settingsAction)

        exitAction = QtGui.QAction('E&xit', self)
        exitAction.setShortcut('ESC')
        exitAction.triggered.connect(self.escape)
        fileMenu.addAction(exitAction)

        # Add style menu
        if os.path.exists(stylesheet_dir):
            default = ''
            sheets = []
            for f in os.listdir(stylesheet_dir):
                if not f.endswith('.css'): continue
                sheets.append(QtGui.QAction(f, self))
                if len(sheets) < 10:
                    sheets[-1].setShortcut('Ctrl+%d' % len(sheets))
                sheets[-1].triggered.connect(
                    lambda x, stylesheet=f: self.set_stylesheet(stylesheet))
            styleMenu = menubar.addMenu('&Style')
            for item in sheets:
                styleMenu.addAction(item)
            self.set_stylesheet(stylesheet_default)

        self.toc = self.menuBar().addMenu('Table of &content')
        self.stats_menu = self.menuBar().addMenu('Statistics')
        self.toc.setDisabled(True)
        self.stats_menu.setDisabled(True)

    def search_panel(self):
        self.search_bar = QtGui.QToolBar()
        for v, t in (('close', u'×'), ('case', u'Aa'), ('wrap', QtGui.QIcon('icons/around.png')), ('high', QtGui.QIcon('icons/bulb.png')), ('next', QtGui.QIcon('icons/down.png')), ('prev', QtGui.QIcon('icons/up.png'))):
            if type(t) == unicode: vars(self)[v] = QtGui.QPushButton(t, self)
            else:                  vars(self)[v] = QtGui.QPushButton(t, '', self)
        self.field = QtGui.QLineEdit()
        def _toggle_btn(btn=''):
            self.field.setFocus()
            self.find(self.field.text(), btn)
        for w in (self.close, self.case, self.wrap, self.high, self.field, self.next, self.prev):
            self.search_bar.addWidget(w)
            if type(w) == QtGui.QPushButton:
                w.setFlat(True)
                w.setFixedWidth(36)
                if any(t for t in (self.case, self.wrap, self.high) if t is w):
                    w.setCheckable(True)
                    w.setFixedWidth(24)
                    w.clicked.connect(_toggle_btn)
                if any(t for t in (self.next, self.prev) if t is w):
                    w.pressed[()].connect(lambda btn=w: _toggle_btn(btn))
        self.field.textChanged.connect(self.find)
        self.field.returnPressed.connect(_toggle_btn)
        self.close.pressed.connect(self.escape)

    def escape(self):
        if self.search_bar.isVisible():
            self.search_bar.hide()
        else:
            QtGui.qApp.quit()

class WatcherThread(QtCore.QThread):
    def __init__(self, filename):
        QtCore.QThread.__init__(self)
        self.filename = filename

    def __del__(self):
        self.wait()

    def run(self):
        last_modified = 0
        while True:
            current_modified = os.path.getmtime(self.filename)
            if last_modified != current_modified:
                last_modified = current_modified
                reader, writer = SetuptheReader._for(self.filename)
                if not writer:
                    # TODO: make a proper error message
                    return reader
                if writer == 'pandoc':
                    pandoc_path     = Settings.get('pandoc_path')
                    pandoc_markdown = Settings.get('pandoc_markdown')
                    pandoc_args     = Settings.get('pandoc_args')
                    reader = pandoc_markdown if reader == 'markdown' else reader
                    args = ('%s --from=%s %s'%(pandoc_path, reader, pandoc_args)).split() + [self.filename]
                    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
                    html = p.communicate()[0].decode('utf8')
                else:
                    with io.open(self.filename, 'r', encoding='utf8') as f:
                        text = f.read()
                    if reader == 'rst':
                        html = writer(text, writer_name='html', settings_overrides={'stylesheet_path': ''})['body']
                    elif reader == 'asciidoc':
                        import StringIO
                        infile = StringIO.StringIO(text.encode('utf8'))
                        outfile = StringIO.StringIO()
                        asciidoc = writer(asciidoc_py=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'asciidoc/asciidoc.py'))
                        asciidoc.options('--no-header-footer')
                        asciidoc.execute(infile, outfile, backend='html5')
                        html = outfile.getvalue().decode('utf8')
                    else:
                        html = writer(text)

                self.emit(QtCore.SIGNAL('update(QString)'), html)
            time.sleep(0.5)


def main():
    app = QtGui.QApplication(sys.argv)
    # if not (via_pandoc or via_markdown):
    #     QtGui.QMessageBox.critical(QtGui.QWidget(),'MarkupViewer cannot convert a file',
    #         'Please, install one of the following packages:<br>'
    #         u'• <a href="https://pythonhosted.org/Markdown/install.html">Markdown</a><br>'
    #         u'• <a href="http://johnmacfarlane.net/pandoc/installing.html">Pandoc</a>')
    if True:
        if len(sys.argv) != 2: test = App()
        else:                  test = App(filename=sys.argv[1])
        test.show()
        app.exec_()

if __name__ == '__main__':
    main()
