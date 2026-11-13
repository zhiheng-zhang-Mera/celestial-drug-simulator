"""Product branding assets for Tk windows and launcher shortcuts.

Each Celestial product stores its own icon under ``assets/branding/``:

* ``<productId>.ico`` - Windows multi-size icon for the Tk title bar, the
  installer copy and the desktop/Start-menu shortcut ``IconLocation``;
* ``<productId>.png`` - 256 px fallback for ``iconphoto`` on Tk builds that do
  not support ``.ico`` bitmaps.

The module never reads another repository and never uses the network.
"""
from pathlib import Path
import tkinter as tk

BRANDING_DIRNAME = Path("assets") / "branding"


def repository_root():
    return Path(__file__).resolve().parent


def branding_paths(product_id, base_dir=None):
    root = Path(base_dir) if base_dir is not None else repository_root()
    folder = root / BRANDING_DIRNAME
    return folder / f"{product_id}.ico", folder / f"{product_id}.png"


def apply_window_icon(window, product_id, base_dir=None):
    """Set the Tk window icon from the product's own files.

    Works for ``python.exe`` and for ``pythonw.exe`` (which has no executable
    icon of its own): the ``.ico`` branch sets the title-bar icon directly and
    the ``.png`` branch provides a ``PhotoImage`` fallback.  Returns a small
    report used by the round-2 verification evidence.
    """
    ico, png = branding_paths(product_id, base_dir=base_dir)
    report = {
        "productId": product_id,
        "icoPath": str(ico),
        "pngPath": str(png),
        "icoExists": ico.is_file(),
        "pngExists": png.is_file(),
        "applied": [],
        "errors": [],
    }
    if ico.is_file():
        try:
            window.iconbitmap(default=str(ico))
            report["applied"].append("iconbitmap")
        except tk.TclError as error:
            report["errors"].append(f"iconbitmap: {error}")
    if png.is_file():
        try:
            image = tk.PhotoImage(file=str(png))
            window.iconphoto(True, image)
            # Tk does not keep a Python reference; store it on the window.
            window._celestial_icon_photo = image
            report["applied"].append("iconphoto")
        except tk.TclError as error:
            report["errors"].append(f"iconphoto: {error}")
    try:
        report["windowIconBitmap"] = str(window.tk.call("wm", "iconbitmap", window._w))
    except tk.TclError:
        report["windowIconBitmap"] = ""
    return report
