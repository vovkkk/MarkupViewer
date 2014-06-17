#!python2
# coding: utf8

import sys, time, os, webbrowser, importlib, itertools, locale, io, yaml, subprocess, threading, shutil
from PyQt4 import QtCore, QtGui, QtWebKit

sys_enc        = locale.getpreferredencoding()
script_dir     = os.path.dirname(os.path.realpath(__file__))
stylesheet_dir = os.path.join(script_dir, 'stylesheets/')


class App(QtGui.QMainWindow):
    def __init__(self, parent=None, filename=''):
        QtGui.QMainWindow.__init__(self, parent)
        # Configure the window
        # TODO: add commandline parameter to force specific geometry
        qsettings = QtCore.QSettings(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, 'MarkupViewer', 'MarkupViewer')
        self.resize(qsettings.value('size', QtCore.QSize(800, 600)).toSize())
        self.move(qsettings.value('pos', QtCore.QPoint(50, 50)).toPoint())
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
        self.filename = filename or os.path.join(script_dir, 'README.md')
        self.thread1 = WatcherThread(self.filename)
        self.connect(self.thread1, QtCore.SIGNAL('update(QString,QString)'), self.update)
        self.thread1.start()
        self.update('','')
        self.web_view.loadFinished.connect(self.after_update)
        # Open links in default browser
        # TODO: ¿ non-default browser @settings ?
        self.web_view.linkClicked.connect(lambda url: webbrowser.open_new_tab(url.toString()))
        # drag&drop
        self.web_view.setAcceptDrops(True)
        setattr(self.web_view, 'dragEnterEvent', self.dragEnterEvent)
        setattr(self.web_view, 'dropEvent', self.dropEvent)
        # ui
        self.menus()
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
            pandoc_path = Settings.get('pandoc_path', 'pandoc')
            args = ('%s -s --from=%s --to=%s'%(pandoc_path, reader, ext[1:])).split() + [self.filename, '--output=%s' % new_file]
            try:    subprocess.Popen(args)
            except: QtGui.QMessageBox.critical(self, 'Cannot find pandoc',
                        'Please, install <a href="http://johnmacfarlane.net/pandoc/installing.html">Pandoc</a>.<br>'
                        'If it is installed for sure, check if it is in PATH or change <code>pandoc_path</code> in settings.')
        else:
            return

    def update(self, text, warn):
        self.web_view.settings().setAttribute(3, Settings.get('plugins', False))
        self.web_view.settings().setAttribute(7, Settings.get('inspector', False))
        # prepare for auto scroll
        prev_doc         = self.web_view.page().currentFrame()
        self.prev_size   = prev_doc.contentsSize()
        self.prev_scroll = prev_doc.scrollPosition()
        self.prev_ls     = []
        self.examine_doc_elements(prev_doc.documentElement(), self.prev_ls)
        # actual update
        self.web_view.setHtml(text, baseUrl=QtCore.QUrl('file:///'+unicode(os.path.join(os.getcwd(), self.filename).replace('\\', '/'), sys_enc)))
        # Delegate links to default browser
        self.web_view.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)
        self.web_view.page().linkHovered.connect(lambda link:self.setToolTip(link))
        # supposed to be 3 threads: main, convertion, settings-reload
        # IDs are supposed to be the same on each update
        # for threadId, _ in sys._current_frames().items():
        #     print "ThreadID: %s" % threadId
        # print '====================\tfinish update()'
        if warn:
            QtGui.QMessageBox.warning(self, 'Converter says', warn)

    def examine_doc_elements(self, parentElement, tree):
        element = parentElement.firstChild()
        while not element.isNull():
            # print element.tagName()
            # FIXME: actually need to filter all parents (not only BODY) or something, e.g. <ul> is the issue (and I don’t even want to try it with tables)
            # besides, parent may have content AND children, e.g. li>ul>li
            if not any(t for t in ('BODY', 'HEAD', 'META', 'TITLE', 'STYLE', 'TABLE', 'TBODY', 'UL', 'OL', 'LI') if t == element.tagName()):
                tree.append([element, element.toPlainText()])
            self.examine_doc_elements(element, tree)
            element = element.nextSibling()

    def after_update(self):
        self.current_doc, current_ls = self.web_view.page().currentFrame(), []
        self.examine_doc_elements(self.current_doc.documentElement(), current_ls)
        # import pprint
        # pprint.pprint([(a.tagName(), b) for a,  b in self.prev_ls])
        # print '='*20
        # pprint.pprint([(a.tagName(), b) for a,  b in  current_ls])
        prev_len, curr_len, go = len(self.prev_ls), len(current_ls), 0
        for i, (element, content) in enumerate(current_ls):
            # print element.tagName()
            if curr_len > prev_len and i + 1 > prev_len:
                # some block was appended to doc
                go = 1
            elif curr_len < prev_len and  i + 1 == curr_len:
                # some block was removed in the end of doc
                go = 1
            elif element.tagName() == self.prev_ls[i][0].tagName():
                # block’s content was changed
                if content != self.prev_ls[i][1]:
                    # print 'ya', element.geometry().top(), element.tagName(), unicode(content).encode('utf8', 'replace')
                    go = 1
            else: # block in the middle of doc was changed (<p> → <h1>)
                # print 'na', element.geometry().top(), unicode(content).encode('utf8', 'replace')
                # print element.tagName(), self.prev_ls[i][0].tagName()
                go = 1
            if go:
                self._scroll(element)
                break
            if not go and i + 1 == curr_len:
                # no actual changes, keep scrollbar in place
                self._scroll()
        # print '='*20
        self.generate_toc(current_ls)
        self.calc_stats()

    def calc_stats(self):
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
        text = unicode(self.current_doc.toPlainText())
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
                if any(c for c in '(){}[]<>,.:;' if c in w):
                    unique_words.append(''.join(c for c in w.lower() if c not in '(){}[]<>,.'))
                else:
                    unique_words.append(w.lower())
            self.stats_menu.addAction(str(len(set(unique_words))) + ' unique words')
        else:
            self.stats_menu.setDisabled(True)
            self.stats_menu.setTitle('Statistics')

    def generate_toc(self, current_ls):
        self.toc.clear()
        self.toc.setDisabled(True)
        headers = []
        for element, _ in current_ls:
            if element.tagName()[0] == 'H' and len(element.tagName()) == 2 and not 'HR' in element.tagName():
                headers.append(element)
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

    def _scroll(self, element=0):
        if element:
            margin = (int(element.styleProperty('margin-top', 2)[:~1]) or
                      int(self.current_doc.findFirstElement('body').styleProperty('padding-top', 2)[:~1]) or
                      0)
            self.current_doc.setScrollPosition(QtCore.QPoint(0, element.geometry().top() - margin))
            element.addClass('markupviewerautoscrollstart')
            QtCore.QTimer.singleShot(1100, lambda: element.addClass('markupviewerautoscrollend'))
            QtCore.QTimer.singleShot(1200, lambda: element.removeClass('markupviewerautoscrollstart'))
            QtCore.QTimer.singleShot(2300, lambda: element.removeClass('markupviewerautoscrollend'))
        else:
            current_size = self.current_doc.contentsSize()
            ypos = self.prev_scroll.y() - (self.prev_size.height() - current_size.height())
            # print '%s = %s - (%s - %s)' % (ypos, self.prev_scroll.y(), self.prev_size.height(), current_size.height())
            self.current_doc.scroll(0, ypos)

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

    def menus(self):
        # TODO: hide menu?
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        ic = 'icons/feather.png'
        for d in (
            {'icon': '', 'label': u'&Save as…',          'keys': 'Ctrl+s', 'func': self.save_html},
            {'icon': ic, 'label': u'&Edit the original', 'keys': 'Ctrl+e', 'func': lambda : self.edit_file('')},
            {'icon': '', 'label': u'&Find on the page…', 'keys': 'Ctrl+f', 'func': self.show_search_panel},
            {'icon': '', 'label': u'&Print',             'keys': 'Ctrl+p', 'func': self.print_doc},
            {'icon': '', 'label': u'Set&tings',          'keys': 'Ctrl+t', 'func': lambda: self.edit_file(Settings().edit_settings())},
            {'icon': '', 'label': u'E&xit',              'keys': 'ESC',    'func': self.escape}
            ):
                a = QtGui.QAction(QtGui.QIcon(d['icon']), d['label'], self)
                a.setShortcut(d['keys'])
                a.triggered.connect(d['func'])
                fileMenu.addAction(a)

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
            self.set_stylesheet(Settings.get('style', 'default.css'))

        self.toc = self.menuBar().addMenu('Table of &content')
        self.stats_menu = self.menuBar().addMenu('Statistics')
        self.toc.setDisabled(True)
        self.stats_menu.setDisabled(True)
        # context menu
        reload_action = self.web_view.page().action(QtWebKit.QWebPage.Reload)
        reload_action.setShortcut(QtGui.QKeySequence.Refresh)
        reload_action.triggered.connect(self.force_reload_view)
        self.web_view.addAction(reload_action)

    def force_reload_view(self):
        self.thread1.last_modified = 0

    def search_panel(self):
        self.search_bar = QtGui.QToolBar()
        for v, t in (('close', u'×'), ('case', u'Aa'), ('wrap', QtGui.QIcon('icons/around.png')), ('high', QtGui.QIcon('icons/bulb.png')), ('next', QtGui.QIcon('icons/down.png')), ('prev', QtGui.QIcon('icons/up.png'))):
            if type(t) == unicode: vars(self)[v] = QtGui.QPushButton(t, self)
            else:                  vars(self)[v] = QtGui.QPushButton(t, '', self)
        class IHATEQT(QtGui.QLineEdit): pass
        self.field = IHATEQT()
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
        setattr(self.field, 'keyPressEvent', self.searchShortcuts)
        self.close.pressed.connect(self.escape)

    def searchShortcuts(self, event):
        if not self.field.isVisible(): return
        if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier and event.key() == 16777220:
            self.find(self.field.text(), self.prev)
        elif event.key() == 16777220:
            self.find(self.field.text(), self.next)
        else:
            super(self.field.__class__, self.field).keyPressEvent(event)

    def print_doc(self):
        dialog = QtGui.QPrintPreviewDialog()
        dialog.paintRequested.connect(self.web_view.print_)
        dialog.exec_()

    def escape(self):
        if self.search_bar.isVisible():
            self.search_bar.hide()
        else:
            self.closeEvent(QtGui.QCloseEvent)

    def closeEvent(self, QCloseEvent):
        qsettings = QtCore.QSettings(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, 'MarkupViewer', 'MarkupViewer')
        qsettings.setValue('size', self.size())
        qsettings.setValue('pos', self.pos())
        QtGui.qApp.quit()


class WatcherThread(QtCore.QThread):
    def __init__(self, filename):
        QtCore.QThread.__init__(self)
        self.filename = filename

    def __del__(self):
        self.wait()

    def run(self):
        self.last_modified = 0
        while True:
            warn = ''
            current_modified = os.path.getmtime(self.filename)
            if self.last_modified != current_modified:
                self.last_modified = current_modified
                reader, writer = SetuptheReader._for(self.filename)
                if not writer:
                    # TODO: make a proper error message
                    return reader
                if writer == 'pandoc':
                    path    = Settings.get('pandoc_path', 'pandoc')
                    pd_args = Settings.get('pandoc_args', '')
                    reader  = Settings.get('pandoc_markdown', 'markdown') if reader == 'markdown' else reader
                    args = [path] + ('--from=%s %s' % (reader, pd_args)).split() + [self.filename]
                    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    # print p.communicate()[1].decode('utf8')
                    html, warn = (m.decode('utf8') for m in p.communicate())
                else:
                    with io.open(self.filename, 'r', encoding='utf8') as f:
                        text = f.read()
                    if reader == 'rst':
                        html = writer(text, writer_name='html', settings_overrides={'stylesheet_path': ''})['body']
                    elif reader == 'asciidoc':
                        import StringIO
                        infile = StringIO.StringIO(text.encode('utf8'))
                        outfile = StringIO.StringIO()
                        asciidoc = writer(asciidoc_py=os.path.join(script_dir, 'asciidoc/asciidoc.py'))
                        asciidoc.options('--no-header-footer')
                        asciidoc.execute(infile, outfile, backend='html5')
                        html = outfile.getvalue().decode('utf8')
                    else:
                        html = writer(text)

                self.emit(QtCore.SIGNAL('update(QString,QString)'), html, warn)
            time.sleep(0.5)


class Settings:
    def __init__(self):
        self.user_source = os.path.join(os.getenv('APPDATA'), 'MarkupViewer/settings.yaml')
        self.app_source  = os.path.join(script_dir, 'settings.yaml')
        self.settings_file = self.user_source if os.path.exists(self.user_source) else self.app_source
        self.reload_settings()

    @classmethod
    def get(cls, key, default_value):
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
    '''a knot of methods related to readers: which one need to be used, is it available etc.
    basic usecase:
        reader, writer = SetuptheReader._for(filename)
        html = writer(unicode_object)
    '''
    readers = Settings.get('formats', {'markdown': 'md'})

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
            reader = Settings.get('no_extension', 'markdown')
        return reader

    @classmethod
    def is_available(self, reader):
        via_pandoc = Settings.get('via_pandoc', False)
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


def main():
    app = QtGui.QApplication(sys.argv)
    # if not (via_pandoc or via_markdown):
    #     QtGui.QMessageBox.critical(QtGui.QWidget(),'MarkupViewer cannot convert a file',
    #         'Please, install one of the following packages:<br>'
    #         u'• <a href="https://pythonhosted.org/Markdown/install.html">Markdown</a><br>'
    #         u'• <a href="http://johnmacfarlane.net/pandoc/installing.html">Pandoc</a>')
    if True:
        thread2 = threading.Thread(target=Settings().watch_settings)
        thread2.setDaemon(True)
        thread2.start()
        if len(sys.argv) != 2: test = App()
        else:                  test = App(filename=sys.argv[1])
        test.show()
        app.exec_()

if __name__ == '__main__':
    main()
