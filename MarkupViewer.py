#!python2
# coding: utf8

from __future__ import print_function
import sys, os, webbrowser, importlib, itertools, locale, io, subprocess, shutil, urllib2, json, datetime, math
try:
    import yaml
except ImportError:
    yaml = None
from PyQt4 import QtCore, QtGui, QtWebKit

try:
    # separate icon in the Windows dock
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('MarkupViewer')

    # enable unicode filenames
    from ctypes import POINTER, byref, cdll, c_int, windll
    from ctypes.wintypes import LPCWSTR, LPWSTR

    GetCommandLineW = cdll.kernel32.GetCommandLineW
    GetCommandLineW.argtypes = []
    GetCommandLineW.restype = LPCWSTR

    CommandLineToArgvW = windll.shell32.CommandLineToArgvW
    CommandLineToArgvW.argtypes = [LPCWSTR, POINTER(c_int)]
    CommandLineToArgvW.restype = POINTER(LPWSTR)

    cmd = GetCommandLineW()
    argc = c_int(0)
    argv = CommandLineToArgvW(cmd, byref(argc))
    if argc.value > 0:
        # Remove Python executable and commands if present
        start = argc.value - len(sys.argv)
        sys.argv = [argv[i] for i in xrange(start, argc.value)]
except: pass

sys_enc        = locale.getpreferredencoding()
script_dir     = os.path.dirname(os.path.realpath(__file__))
if os.name != 'nt':
    script_dir = script_dir.decode(sys_enc)
stylesheet_dir = os.path.join(script_dir, 'stylesheets/')
VERSION = 'unreleased'


class App(QtGui.QMainWindow):
    @property
    def QSETTINGS(self):
        return QtCore.QSettings(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, 'MarkupViewer', 'MarkupViewer')

    def set_title(self):
        parent, name = os.path.split(os.path.abspath(self.filename))
        self.setWindowTitle(u'%s — MarkupViewer' % (u'%s (%s)' % (name, parent) if Settings.get('show_full_path', True) else name))

    def __init__(self, parent=None, filename=''):
        QtGui.QMainWindow.__init__(self, parent)
        self.filename = filename or os.path.join(script_dir, u'README.md')
        # Configure the window
        # TODO: add commandline parameter to force specific geometry
        self.resize(self.QSETTINGS.value('size', QtCore.QSize(800, 600)).toSize())
        self.move(self.QSETTINGS.value('pos', QtCore.QPoint(50, 50)).toPoint())
        self.set_title()
        self.setWindowIcon(QtGui.QIcon('icons/markup.ico'))
        # Add the WebView control
        self.web_view = QtWebKit.QWebView()
        self.setCentralWidget(self.web_view)
        # Start the File Watcher Thread
        self.thread1 = WatcherThread(self.filename)
        self.connect(self.thread1, QtCore.SIGNAL('update(QString,QString)'), self.update)
        self.w = QtCore.QFileSystemWatcher([self.filename])
        self.w.fileChanged.connect(self.thread1.start)
        self.thread1.start()
        self.update('', '')
        self.web_view.loadFinished.connect(self.after_update)
        # Open links in default browser
        # TODO: ¿ non-default browser @settings ?
        self.web_view.linkClicked.connect(lambda url: webbrowser.open_new_tab(url.toString()))
        # drag&drop
        self.setAcceptDrops(True)
        self.web_view.setAcceptDrops(True)
        setattr(self.web_view, 'dragEnterEvent', self.dragEnterEvent)
        setattr(self.web_view, 'dropEvent', self.dropEvent)
        # ui
        self.menus()
        self.search_panel()
        self.toc_panel()
        # update
        QtCore.QTimer.singleShot(60000, lambda: CheckUpdate(self))

    def dragEnterEvent(self, event): event.accept()

    def dropEvent(self, event):
        fn = event.mimeData().urls()[0].toLocalFile().toUtf8().data()
        self.filename = self.thread1.filename = fn.decode('utf8')
        self.set_title()
        self.force_reload_view()

    def edit_file(self, fn):
        if not fn: fn = self.filename
        editor  = Settings.get('editor', 'sublime_text').split()
        command = editor[0]
        ed_args = editor[1:] + [fn]
        caller = QtCore.QProcess()
        status = caller.execute(command, ed_args)
        if status < 0:
            caller = QtCore.QProcess()
            success = caller.startDetached('notepad', [fn])
            if not success:
                msg = (u'Please, install <a href="https://pypi.python.org/pypi/PyYAML/">PyYAML</a> (if not yet).<br><br>'
                       u'And then change <code>editor</code> field in <code>settings.yaml</code> file.<br><br>'
                       u'It can be found in <pre>{0}</pre> or in <pre>{1}</pre> it is editable in any text editor.'
                       .format(*(os.path.normpath(s) for s in (Settings().user_source, Settings().app_source))))
                QtGui.QMessageBox.critical(self, 'MarkupViewer cannot find a text editor', msg)

    def save_html(self):
        formats = ('HyperText Markup Language (*.html);;'
                   'All files (*);;'
                   'Portable Document Format (*.pdf);;'
                   'Markdown (*.md);;'
                   'Plain text (*.txt);;%s' %
                   ('OpenDocument Text (*.odt);;'
                    'Office Open XML (*.docx);;'
                    'Rich Text Format (*.rtf);;'
                    'Electronic Publication v2 (*.epub);;'
                    'Electronic Publication v3 (*.epub3);;'
                    'FictionBook (*.fb2);;' if Settings.get('via_pandoc', False) else ''))
        new_file = unicode(QtGui.QFileDialog.getSaveFileName(self, 'Save file', os.path.dirname(self.filename), formats))
        ext = os.path.splitext(new_file)[1]
        if ext == ('.html' or ''):
            with io.open(new_file, 'w', encoding='utf8') as f:
                f.writelines(unicode(self.current_doc.toHtml()))
        elif ext == '.pdf':
            QtGui.QMessageBox.critical(self, 'Yo', '<a href="http://i0.kym-cdn.com/photos/images/original/000/284/529/e65.gif">AiNT NOBODY GOT TiME FOR DAT</a>')
        elif ext:
            reader, _ = SetuptheReader._for(self.filename)
            command = Settings.get('pandoc_path', 'pandoc')
            pd_args = ['-s', '--from=%s' % reader, '--to=%s' % ext[1:], self.filename, '--output=%s' % new_file]
            caller = QtCore.QProcess()
            status = caller.execute(command, pd_args)
            if status < 0:
                msg = ('Please, install <a href="http://johnmacfarlane.net/pandoc/installing.html">Pandoc</a>.<br><br>'
                       'If it is installed for sure, check if it is in PATH or change <code>pandoc_path</code> in settings.')
                QtGui.QMessageBox.critical(self, 'Cannot find pandoc', msg)
        else:
            return

    def update(self, text, warn):
        self.web_view.settings().setAttribute(3, Settings.get('plugins', False))
        self.web_view.settings().setAttribute(7, Settings.get('inspector', False))
        # prepare for auto scroll
        prev_doc         = self.web_view.page().currentFrame()
        self.prev_size   = prev_doc.contentsSize()
        self.prev_scroll = prev_doc.scrollPosition()
        self.prev_ls     = self.examine_doc_elements(prev_doc.documentElement())
        # actual update
        self.web_view.setHtml(text, baseUrl=QtCore.QUrl('file:///' + os.path.join(os.getcwd(), self.filename).replace('\\', '/')))
        # Delegate links to default browser
        self.web_view.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)
        self.web_view.page().linkHovered.connect(lambda link: self.setToolTip(link))
        # supposed to be 2 threads when start script: main, convertion
        # then only 1 on each update: main
        # IDs are supposed to be the same on each update
        # for threadId, _ in sys._current_frames().items():
        #     print("ThreadID: %s" % threadId)
        # print('====================\tfinish update()')
        if warn:
            QtGui.QMessageBox.warning(self, 'Converter says', warn)

    def examine_doc_elements(self, parentElement):
        u'''create tree of QWebElements starting from parentElement;
            [
              [Parent1, [[child, [child_of_child, ...], ...]],
              [Parent2, [[child, [child_of_child, ...], ...]],
              ...
            ]
            where Parent1 is the first child of parentElement;
            each list contains QWebElement and list of its children recursively,
            an empty list represents the absence of children
        '''
        children = []
        element = parentElement.firstChild()
        while not element.isNull():
            if not any(t for t in ('HEAD', 'META', 'TITLE', 'STYLE') if t == element.tagName()):
                if element not in children:
                    further = self.examine_doc_elements(element)
                    children.append([element, further])
            element = element.nextSibling()
        if children:
            return children

    def after_update(self):
        def compare(prev_ls, current_ls, prev_len, curr_len, go):
            for i, (element, children) in enumerate(current_ls):
                if children:
                    if prev_ls:
                        prev_children = prev_ls[i][1]
                        prev_children_len = len(prev_children) if prev_children else 0
                        go = compare(prev_children, children, prev_children_len, len(children), go)
                        if go:
                            return go
                    else:
                        return children[0][0]
                if element.tagName() == 'BODY':
                    go = 0
                elif curr_len > prev_len and i + 1 > prev_len:
                    # some block was appended to doc
                    go = 1
                elif curr_len < prev_len and  i + 1 == curr_len:
                    # some block was removed in the end of doc
                    go = 1
                elif element.tagName() == prev_ls[i][0].tagName():
                    if element.toInnerXml() != prev_ls[i][0].toInnerXml():
                        # block’s content was changed
                        go = 1
                        # print ('ya', element.geometry().top(), element.tagName(), unicode(element.toPlainText()).encode('utf8', 'replace'))
                else: # block in the middle of doc was changed (<p> → <h1>)
                    go = 1
                    # print ('na', element.geometry().top(), unicode(element.toPlainText()).encode('utf8', 'replace'))
                    # print (element.tagName(), self.prev_ls[i][0].tagName())
                if go:
                    value = element
                    break
                elif not go and i + 1 == curr_len:
                    # no actual changes, keep scrollbar in place
                    value = 0
            return value
        self.current_doc = self.web_view.page().currentFrame()
        current_ls       = self.examine_doc_elements(self.current_doc.documentElement())
        prev_len, curr_len, go = len(self.prev_ls), len(current_ls), 0
        self._scroll(element=compare(self.prev_ls, current_ls, prev_len, curr_len, go), update=True)
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
        def flatten(ls):
            for item in ls:
                if not item: continue
                if isinstance(item, list):
                    for x in flatten(item):
                        yield x
                else:
                    yield item
        self.toc.clear()
        self.toc.setDisabled(True)
        headers = []
        for element in flatten(current_ls):
            if element.tagName()[0] == 'H' and len(element.tagName()) == 2 and not 'HR' in element.tagName():
                headers.append(element)
        self.toc.addAction(self.toc_panel_action)
        for n, h in enumerate(headers, start=1):
            try:
                indent = int(h.tagName()[1:])
            except ValueError: # cannot make it integer, means no headers
                print(h.tagName())
                break
            else:
                self.toc.setDisabled(False)
            title = u'  '*indent + h.toPlainText()
            vars(self)['toc_nav%d'%n] = QtGui.QAction(QtGui.QIcon('icons/h%d.png'%indent), title, self)
            vars(self)['toc_nav%d'%n].triggered[()].connect(lambda header=h: self._scroll(header))
            self.toc.addAction(vars(self)['toc_nav%d'%n])
        self.toc_list.clear()
        if not headers:
            self.dock_widget.setDisabled(True)
            self.filter.hide()
            self.captain.show()
            return
        self.dock_widget.setDisabled(False)
        for t in list(vars(self)['toc_nav%d'%i].text() for i in xrange(1, n+1)):
            # item = QtGui.QListWidgetItem(QtGui.QIcon('icons/left_margin.png'), t)
            item = QtGui.QListWidgetItem(t)
            item.setSizeHint(QtCore.QSize(0, 26))
            self.toc_list.addItem(item)
        # self.toc_list.addItems(list(vars(self)['toc_nav%d'%i].text() for i in xrange(1, n+1)))
        self.toc_list.itemPressed.connect(lambda n: vars(self)['toc_nav%d' % (n.listWidget().currentRow()+1)].activate(0))
        self.toc_list.itemActivated.connect(lambda n: vars(self)['toc_nav%d' % (n.listWidget().currentRow()+1)].activate(0))
        self.filter.show()
        self.captain.hide()
        self.filter_toc(self.filter.text())

    def _scroll(self, element=0, update=0):
        '''
        element  html tag to top of which we need to scroll
        update   if True, it was called upon doc update, otherwise it is on toc
        '''
        if update:
            current_size = self.current_doc.contentsSize()
            ypos = self.prev_scroll.y() - (self.prev_size.height() - current_size.height())
            # print ('%s = %s - (%s - %s)' % (ypos, self.prev_scroll.y(), self.prev_size.height(), current_size.height()))
            self.current_doc.scroll(0, ypos)
        if element:
            margin = (int(float(element.styleProperty('margin-top', 2)[:~1])) or
                      int(float(element.parent().styleProperty('margin-top', 2)[:~1])) or
                      int(float(self.current_doc.findFirstElement('body').styleProperty('padding-top', 2)[:~1])) or
                      0)
            self.anim = QtCore.QPropertyAnimation(self.current_doc, 'scrollPosition')
            start = self.prev_scroll if update else self.current_doc.scrollPosition()
            # duration is logarithm of 700 to base x, where x is amount of pixels need to scroll (700 is arbitrary number which seems to give suitable results)
            # i.e. more pixels means faster duration & fewer pixels—slower duration
            #   10px: 284ms = 100 * (math.log(700)/math.log(10))
            #  100px: 142ms = 100 * (math.log(700)/math.log(100))
            # 1000px:  94ms = 100 * (math.log(700)/math.log(1000))
            # so if change is close to prev pos, then we get nice smooth animation;
            # if it is far, then we kinda quickly jump to it
            self.anim.setDuration(100 * int(math.log(700)/math.log(abs(start.y() - element.geometry().top()))))
            self.anim.setStartValue(QtCore.QPoint(start))
            self.anim.setEndValue(QtCore.QPoint(0, element.geometry().top() - margin))
            self.anim.start()
            # highlight element via css property
            element.addClass('markupviewerautoscrollstart')
            QtCore.QTimer.singleShot(1100, lambda: element.addClass('markupviewerautoscrollend'))
            QtCore.QTimer.singleShot(1200, lambda: element.removeClass('markupviewerautoscrollstart'))
            QtCore.QTimer.singleShot(2300, lambda: element.removeClass('markupviewerautoscrollend'))

    @staticmethod
    def set_stylesheet(self, stylesheet='default.css'):
        full_path = os.path.join(stylesheet_dir, stylesheet)
        url = QtCore.QUrl.fromLocalFile(full_path)
        self.web_view.settings().setUserStyleSheetUrl(url)

    def show_search_panel(self):
        self.addToolBar(0x8, self.search_bar)
        self.search_bar.show()
        self.field.setFocus()
        self.field.selectAll()

    def show_toc_panel(self):
        self.addDockWidget(self.QSETTINGS.value('toc_bar_area', QtCore.Qt.LeftDockWidgetArea).toInt()[0], self.dock)
        if self.dock.isVisible():
            self.dock.hide()
            self.toc_panel_action.setChecked(False)
        else:
            self.dock.show()
            self.toc_panel_action.setChecked(True)

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
        na = 'icons/left_margin.png' # workaround for Linux to keep items aligned
        for d in (
            {'icon': na, 'label': u'&Save as…',          'keys': 'Ctrl+s', 'func': self.save_html},
            {'icon': ic, 'label': u'&Edit the original', 'keys': 'Ctrl+e', 'func': lambda : self.edit_file('')},
            {'icon': na, 'label': u'&Find on the page…', 'keys': 'Ctrl+f', 'func': self.show_search_panel},
            {'icon': na, 'label': u'&Print',             'keys': 'Ctrl+p', 'func': self.print_doc},
            {'icon': na, 'label': u'Set&tings',          'keys': 'Ctrl+t', 'func': lambda: self.edit_file(Settings().edit_settings())},
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
                    lambda x, stylesheet=f: self.set_stylesheet(self, stylesheet))
            styleMenu = menubar.addMenu('&Style')
            for item in sheets:
                styleMenu.addAction(item)
            self.set_stylesheet(self, Settings.get('style', 'default.css'))

        self.toc = menubar.addMenu('Table of &content')
        self.toc.setStyleSheet('menu-scrollable: 1')
        self.toc_panel_action = QtGui.QAction('Show in sidebar', self)
        self.toc_panel_action.setCheckable(True)
        self.toc_panel_action.triggered.connect(self.show_toc_panel)
        self.toc.addAction(self.toc_panel_action)

        self.stats_menu = menubar.addMenu('Statistics')
        self.toc.setDisabled(True)
        self.stats_menu.setDisabled(True)

        menubar_on_right = QtGui.QMenuBar()
        menubar.setCornerWidget(menubar_on_right, QtCore.Qt.TopRightCorner)

        self.about = QtGui.QAction('About', self)
        about = QtGui.QMessageBox(0, 'About MarkupViewer',
         '<table cellspacing="50"><tr valign="middle">'
         '<td><img src="icons/markup.ico"></td>'
         '<td style="white-space: nowrap">Version: %s<br><br>'
           '<a href="https://github.com/vovkkk/MarkupViewer/issues/new">Send feedback</a>'
           '<br><br><br><br>'
           u'© 2013 Matthew Borgerson<br>© 2014 Vova Kolobok<br><br>'
           '<a href="http://www.gnu.org/licenses/gpl-2.0.html">The GNU General Public License</a>'
         '</td></tr></table>'
         % (VERSION), parent=self)
        self.about.triggered.connect(lambda: about.show())
        menubar_on_right.addAction(self.about)

        # context menu
        reload_action = self.web_view.page().action(QtWebKit.QWebPage.Reload)
        reload_action.setShortcut(QtGui.QKeySequence.Refresh)
        reload_action.triggered.connect(self.force_reload_view)
        self.web_view.addAction(reload_action)

    def force_reload_view(self):
        self.thread1.run()

    def search_panel(self):
        self.search_bar = QtGui.QToolBar()
        for b, n, t in (
         ('close',      u'×',                      'Close (Escape)'),
         ('case',       u'Aa',                     'Case sensitive'),
         ('wrap', QtGui.QIcon('icons/around.png'), 'Wrap'),
         ('high', QtGui.QIcon('icons/bulb.png'),   'Highlight all matches'),
         ('next', QtGui.QIcon('icons/down.png'),   'Find next (Enter)'),
         ('prev', QtGui.QIcon('icons/up.png'),     'Find previous (Shift+Enter)')
        ):
            if isinstance(n, unicode):
                vars(self)[b] = QtGui.QPushButton(n, self)
            else:
                vars(self)[b] = QtGui.QPushButton(n, '', self)
            vars(self)[b].setToolTip(t)
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
        if self.QSETTINGS.value('search_bar', False).toBool():
            self.show_search_panel()
        for t, w in (('case_btn', self.case), ('wrap_btn', self.wrap), ('highlight_btn', self.high)):
            w.setChecked(self.QSETTINGS.value(t, False).toBool())

    def searchShortcuts(self, event):
        '''useful links:
            http://pyqt.sourceforge.net/Docs/PyQt4/qt.html#Key-enum
            http://pyqt.sourceforge.net/Docs/PyQt4/qkeysequence.html#details
            http://pyqt.sourceforge.net/Docs/PyQt4/qkeyevent.html
        tbh, all keybindings stuff in Qt is completely frustrating :(
        '''
        if not self.field.isVisible(): return
        key = event.key()
        modifier = event.modifiers()
        return_key = key == 16777220
        enter_key  = key == 16777221
        if (return_key and modifier == QtCore.Qt.ShiftModifier) or (
            enter_key  and modifier != QtCore.Qt.KeypadModifier):
                self.find(self.field.text(), self.prev)
        elif return_key or enter_key:
            self.find(self.field.text(), self.next)
        else:
            super(self.field.__class__, self.field).keyPressEvent(event)

    def toc_panel(self):
        self.dock = QtGui.QDockWidget("  TOC", self)
        self.dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.dock.visibilityChanged.connect(lambda v: self.toc_panel_action.setChecked(v))
        self.dock.dockLocationChanged.connect(lambda a: self.toc_panel_save_state(a))
        if not self.QSETTINGS.value('toc_bar', False).toBool():
            self.dock.hide()
        else:
            self.show_toc_panel()

        self.dock_widget = QtGui.QWidget()
        self.dock.setWidget(self.dock_widget)
        self.dock_widget.setDisabled(True)

        self.toc_list = QtGui.QListWidget(self.dock)
        self.setStyleSheet('QListWidget{border:0px}')
        setattr(self.toc_list, 'sizeHint', self.toc_panel_default_width)
        # self.toc_list.setWordWrap(True)

        self.filter = QtGui.QLineEdit()
        self.filter.setPlaceholderText('Filter headers')
        self.filter.textChanged.connect(self.filter_toc)
        self.filter.hide()

        self.captain = QtGui.QLabel('<br><br><br><center><big>No headers</big></center>')

        dock_layout = QtGui.QVBoxLayout()
        dock_layout.setContentsMargins(0,0,0,0)
        dock_layout.addWidget(self.captain)
        dock_layout.addWidget(self.filter)
        dock_layout.addWidget(self.toc_list)
        self.dock_widget.setLayout(dock_layout)

    def filter_toc(self, text):
        # kinda fuzzy search: text → *t*e*x*t*
        text = u'*%s*' % u'*'.join(unicode(t) for t in text)
        matches = self.toc_list.findItems(text, QtCore.Qt.MatchContains | QtCore.Qt.MatchWildcard)
        all_items = self.toc_list.findItems('*', QtCore.Qt.MatchWildcard | QtCore.Qt.MatchWrap)
        for i in all_items:
            i.setHidden(True if i not in matches else False)

    def toc_panel_default_width(self):
        # 30% of main window width
        return QtCore.QSize(int(self.width()*3/10), 0)

    def toc_panel_save_state(self, area):
        self.QSETTINGS.setValue('toc_bar_area', area)

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
        self.QSETTINGS.setValue('size', self.size())
        self.QSETTINGS.setValue('pos', self.pos())
        for t, w in (('search_bar', self.search_bar), ('toc_bar', self.dock), ('case_btn', self.case), ('wrap_btn', self.wrap), ('highlight_btn', self.high)):
            if 'btn' in t: self.QSETTINGS.setValue(t, w.isChecked())
            else:          self.QSETTINGS.setValue(t, w.isVisible())
        QtGui.qApp.quit()


class WatcherThread(QtCore.QThread):
    def __init__(self, filename):
        QtCore.QThread.__init__(self)
        self.filename = filename

    def run(self):
        warn = ''
        reader, writer = SetuptheReader._for(self.filename)
        if not writer:
            html, warn = u'', self.tell_em(reader)
        elif writer == 'pandoc':
            html, warn = self.pandoc_rules(reader)
        else:
            try:  html = self.aint_no_need_pandoc(reader, writer)
            except Exception as e:
                html, warn = '', u'<b>%s</b><br>%s' % (str(writer)[1:-1], e)
        self.emit(QtCore.SIGNAL('update(QString,QString)'), html, warn)

    def tell_em(self, reader):
        warn = (u'<p>There is no module able to convert <b>%s</b>.</p>' % reader)
        if Settings.get('via_pandoc', False):
            warn += ('<p>Make sure <a href="http://johnmacfarlane.net/pandoc/installing.html">Pandoc</a> is installed.</p>'
                     'If it is installed for sure,<br>check if it is in PATH or<br>change <code>pandoc_path</code> in settings.')
        else:
            warn += 'Make sure certain package is installed<br>(see <a href="https://github.com/vovkkk/MarkupViewer#dependencies">Dependencies</a>).'
        return warn

    def pandoc_rules(self, reader):
        path    = Settings.get('pandoc_path', 'pandoc')
        pd_args = Settings.get('pandoc_args', '')
        reader  = Settings.get('pandoc_markdown', 'markdown') if reader == 'markdown' else reader
        args = ('--from=%s %s' % (reader, pd_args)).split() + [self.filename]
        caller = QtCore.QProcess()
        caller.start(path, args)
        caller.waitForFinished()
        html = unicode(caller.readAllStandardOutput(), 'utf8')
        warn = unicode(caller.readAllStandardError(), 'utf8')
        return (html, warn)

    def aint_no_need_pandoc(self, reader, writer):
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
        return html


class Settings:
    def __init__(self):
        if os.name == 'nt':
            self.user_source = os.path.join(os.getenv('APPDATA'), 'MarkupViewer/settings.yaml')
        else:  # for Linux & OSX
            self.user_source = os.path.join(os.getenv('HOME'), '.config/MarkupViewer/settings.yaml')
        self.app_source = os.path.join(script_dir, 'settings.yaml')
        self.settings_file = self.user_source if os.path.exists(self.user_source) else self.app_source
        self.reload_settings()

    @classmethod
    def get(cls, key, default_value):
        return cls().settings.get(key, default_value)

    def reload_settings(self):
        if not yaml:
            self.settings = {}
            return
        with io.open(self.settings_file, 'r', encoding='utf8') as f:
            self.settings = yaml.safe_load(f)

    def edit_settings(self):
        if not os.path.exists(self.user_source):
            userfld = os.path.dirname(self.user_source)
            if not os.path.isdir(userfld):
                os.makedirs(os.path.dirname(self.user_source))
            with io.open(self.app_source, 'r', encoding='utf8') as a:
                text = a.read()
            with io.open(self.user_source, 'w', encoding='utf8') as u:
                u.write(text)
            self.settings_file = self.user_source
        return self.settings_file


class SetuptheReader:
    '''a knot of methods related to readers: which one need to be used, is it available etc.
    basic usecase:
        reader, writer = SetuptheReader._for(filename)
        html = writer(unicode_object)
    '''
    readers = Settings.get('formats', {
                'asciidoc' : 'adoc asciidoc',
                'creole'   : 'creole',
                'docbook'  : 'dbk xml',
                'docx'     : 'docx',
                'epub'     : 'epub',
                'latex'    : 'tex',
                'markdown' : 'md mdown markdn markdown',
                'mediawiki': 'mediawiki',
                'opml'     : 'opml',
                'org'      : 'org',
                'rst'      : 'rst',
                't2t'      : 't2t',
                'textile'  : 'textile'
                })

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
        return dict((e, r) for e, r in itertools.chain(*itertools.imap(omg, readers.iteritems())))

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
            if subprocess.call([Settings.get('pandoc_path', 'pandoc'), '-v'], shell=(os.name == 'nt')):
                via_pandoc = False
            else:
                return (reader, 'pandoc')
        if not via_pandoc or reader == 'creole' or reader == 'asciidoc':
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


class CheckUpdate:
    @property
    def QSETTINGS(self):
        return QtCore.QSettings(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, 'MarkupViewer', 'MarkupViewer')

    def __init__(self, parent):
        self.t = self.Check()
        self.t.start()
        self.t.finished.connect(lambda: self.notify(self.t.response, parent))

    class Check(QtCore.QThread):
        def __init__(self): QtCore.QThread.__init__(self)
        def run(self):
            request  = urllib2.urlopen('https://api.github.com/repos/vovkkk/MarkupViewer/releases').read()
            self.response = json.loads(request)[0]

    def notify(self, response, parent):
        last_update = self.QSETTINGS.value('last_update', datetime.datetime(2014, 1, 1, 1, 1, 1)).toPyObject()
        published   = datetime.datetime.strptime(response.get('published_at', ''), '%Y-%m-%dT%H:%M:%SZ')
        now         = datetime.datetime.now()
        if now - last_update > datetime.timedelta(7) and published > last_update:
            self.QSETTINGS.setValue('last_update', now)
            notify = self.Notification(parent)
            notify.show()
            link = (response['assets'][0]['browser_download_url'] if os.name == 'nt' else response['tarball_url'])
            size = round(float(response['assets'][0]['size'])/10**6, 2)
            togh = response['html_url']
            body = response.get('body', '# FAIL ;D')
            _, writer = SetuptheReader.is_available('markdown')
            if not writer:
                text = body.replace('\n', '<br>')
            elif writer == 'pandoc':
                path = Settings.get('pandoc_path', 'pandoc')
                args = [path] + ('--from=markdown %s' % Settings.get('pandoc_args', '')).split()
                p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                text = p.communicate(body.encode('utf8'))[0].decode('utf8')
            else:
                text = writer(body)
            notify.web_view.setHtml(text)
            App.set_stylesheet(notify, Settings.get('style', 'default.css'))
            notify.download.setText('Download (%s MB)' % size)
            notify.download.pressed.connect(lambda: webbrowser.open(link))
            notify.go_to_gh.pressed.connect(lambda: webbrowser.open(togh))

    class Notification(QtGui.QMainWindow):
        def __init__(self, parent=None):
            QtGui.QMainWindow.__init__(self, parent)
            self.setWindowTitle(u'New version of MarkupViewer is availiable')
            self.resize(QtCore.QSize(450, 400))

            self.web_view = QtWebKit.QWebView()
            self.setCentralWidget(self.web_view)

            tb = QtGui.QToolBar()
            tb.setMovable(False)
            self.setStyleSheet('QToolBar{border: 0px; margin: 10px; spacing:10px}'
                               'QPushButton{padding: 5px 10px}')

            spacer = QtGui.QWidget()
            spacer.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
            self.download = QtGui.QPushButton('Download')
            self.go_to_gh = QtGui.QPushButton('Go to GitHub')
            self.cancel   = QtGui.QPushButton('Cancel')
            self.cancel.setShortcut('Esc')
            self.cancel.pressed.connect(lambda: self.close())
            for b in (spacer, self.download, self.go_to_gh, self.cancel):
                tb.addWidget(b)

            self.addToolBar(0x8, tb)


def main():
    app = QtGui.QApplication(sys.argv)
    if len(sys.argv) != 2:
        test = App()
    else:
        test = App(filename=sys.argv[1] if os.name == 'nt' else sys.argv[1].decode(sys_enc))
    test.show()
    if not yaml:
        QtGui.QMessageBox.information(test, 'PyYAML is not installed',
            'MarkupViewer will work using default settings.<br>'
            'In order to change settings, please install <a href="https://pypi.python.org/pypi/PyYAML/">PyYAML</a>.')
    app.exec_()

if __name__ == '__main__':
    main()
