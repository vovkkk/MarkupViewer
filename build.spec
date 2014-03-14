# -*- mode: python -*-
from PyInstaller.hooks.hookutils import collect_submodules

a = Analysis(
    ['MarkupViewer.py'],
    pathex=['D:\\dev\\GitHub\\MarkdownViewer'],
    hiddenimports=[
        'markdown.markdown','xml.etree.ElementTree','htmlentitydefs'
        ,'creole.creole2html', 'xml.sax.saxutils.escape', 'xml.sax.xmlreader', 'xml.sax.handler', 'xml.sax._exceptions', 'HTMLParser', 'markupbase'
        ,'ConfigParser' # for docutils
        ,'uuid' # for textile
        ],
    hookspath=None,    runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='MarkupViewer.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='MarkupViewer')
