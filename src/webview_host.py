"""Windows native child WebEngine process. Only local assets and region IDs cross it."""
import json
import os
from pathlib import Path
import sys
import threading


def main():
    # Match the existing Tk process' Windows DPI virtualization for native parenting.
    os.environ.setdefault('QT_QPA_PLATFORM', 'windows:dpiawareness=0')
    os.environ.setdefault('QT_ENABLE_HIGHDPI_SCALING', '0')
    from PySide6.QtCore import QObject, Signal, Slot, QUrl, QTimer, Qt
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QWindow
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineUrlRequestInterceptor
    from PySide6.QtWebChannel import QWebChannel
    import ctypes
    from ctypes import wintypes
    from src.anatomy import REGIONS

    assets = Path(__file__).resolve().parents[1]/'assets/web'
    def emit(event, **values):
        print(json.dumps(dict(event=event, **values), ensure_ascii=True), flush=True)

    class LocalOnly(QWebEngineUrlRequestInterceptor):
        def interceptRequest(self, info):
            url=info.requestUrl()
            allowed=(url.scheme()=='qrc' and url.path()=='/qtwebchannel/qwebchannel.js')
            if url.scheme()=='file':
                allowed=Path(url.toLocalFile()).resolve().is_relative_to(assets.resolve())
            if url.scheme()=='data': allowed=True
            if not allowed: info.block(True)

    class Page(QWebEnginePage):
        def acceptNavigationRequest(self, url, navigation_type, main_frame):
            return url==QUrl.fromLocalFile(str(assets/'index.html'))
        def javaScriptConsoleMessage(self, level, message, line, source):
            print(f'HTML {level}: {message} ({line})',file=sys.stderr,flush=True)

    class Bridge(QObject):
        command=Signal(str)
        @Slot(str)
        def selectRegion(self, region):
            if region in REGIONS: emit('select',region=region)
        @Slot()
        def ready(self):
            self.loaded=True;emit('ready');self.apply()
        def apply(self):
            if self.loaded and self.state:
                page.runJavaScript('window.applyAnatomyState('+json.dumps(self.state,ensure_ascii=True)+');')
        @Slot(str)
        def receive(self, line):
            try:
                data=json.loads(line)
                if data.get('action')=='close': app.quit()
                elif data.get('action')=='state': self.state=data['state'];self.apply()
                elif data.get('action')=='size':
                    fit()
            except (ValueError,KeyError,TypeError): pass

    app=QApplication([])
    profile=QWebEngineProfile(app)  # off-the-record, no user browser profile
    interceptor=LocalOnly(profile);profile.setUrlRequestInterceptor(interceptor)
    view=QWebEngineView();view.setWindowFlags(Qt.WindowType.FramelessWindowHint)
    page=Page(profile,view);view.setPage(page)
    bridge=Bridge();bridge.loaded=False;bridge.state=None
    channel=QWebChannel(page);channel.registerObject('anatomy',bridge);page.setWebChannel(channel)
    bridge.command.connect(bridge.receive)
    user32=ctypes.WinDLL('user32',use_last_error=True)
    user32.SetParent.argtypes=[wintypes.HWND,wintypes.HWND];user32.SetParent.restype=wintypes.HWND
    user32.GetWindowLongW.argtypes=[wintypes.HWND,ctypes.c_int];user32.GetWindowLongW.restype=ctypes.c_long
    user32.SetWindowLongW.argtypes=[wintypes.HWND,ctypes.c_int,ctypes.c_long]
    user32.MoveWindow.argtypes=[wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.BOOL]
    user32.IsWindow.argtypes=[wintypes.HWND];user32.IsWindow.restype=wintypes.BOOL
    user32.GetParent.argtypes=[wintypes.HWND];user32.GetParent.restype=wintypes.HWND
    user32.GetClientRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
    parent=int(sys.argv[1]);hwnd=int(view.winId())
    foreign=QWindow.fromWinId(parent)
    view.windowHandle().setParent(foreign)
    view.resize(int(sys.argv[2]),int(sys.argv[3]));view.show()
    # Qt may recreate the HWND when changing native ancestry/showing the widget.
    hwnd=int(view.winId())
    style=user32.GetWindowLongW(hwnd,-16)
    user32.SetWindowLongW(hwnd,-16,(style & ~0x80000000)|0x40000000)
    ctypes.set_last_error(0);user32.SetParent(hwnd,parent)
    if ctypes.get_last_error():raise ctypes.WinError(ctypes.get_last_error())
    def fit():
        rect=wintypes.RECT();user32.GetClientRect(parent,ctypes.byref(rect))
        w=max(1,rect.right);h=max(1,rect.bottom);scale=view.devicePixelRatioF()
        view.resize(round(w/scale),round(h/scale))
        user32.MoveWindow(hwnd,0,0,w,h,True)
    fit()
    def attach():
        nonlocal hwnd
        hwnd=int(view.winId())
        style=user32.GetWindowLongW(hwnd,-16)
        user32.SetWindowLongW(hwnd,-16,(style & ~0x80000000)|0x40000000)
        user32.SetParent(hwnd,parent)
        fit()
        print(f'native parent={parent}, actual={user32.GetParent(hwnd)}, child={hwnd}, size={view.width()}x{view.height()}',file=sys.stderr,flush=True)
    QTimer.singleShot(300,attach)
    emit('attached',hwnd=hwnd)
    page.loadFinished.connect(lambda ok: emit('error',message='HTML 页面加载失败') if not ok else None)
    view.load(QUrl.fromLocalFile(str(assets/'index.html')))
    def incoming():
        for line in sys.stdin: bridge.command.emit(line)
        bridge.command.emit('{"action":"close"}')
    threading.Thread(target=incoming,daemon=True).start()
    timer=QTimer();timer.timeout.connect(lambda: app.quit() if not user32.IsWindow(parent) else None);timer.start(500)
    app.exec()
    page.deleteLater();profile.deleteLater()


if __name__=='__main__':main()
