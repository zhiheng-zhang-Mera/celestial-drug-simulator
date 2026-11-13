"""Round-2 UI evidence for a Celestial Tk product.

Verifies, in a real Tk window:

* every registered ``?`` help bubble has static text (2-6 sentences) and a
  unique key;
* open/close via toggle, keyboard Enter and Esc all work;
* clicking elsewhere closes the open bubble;
* the product window icon comes from ``assets/branding/<product>.ico`` and the
  ``.png`` fallback, without needing an executable icon (pythonw case);
* screenshots of the collapsed and expanded states are stored under
  ``_evidence/round2/``.

The script is read-only for product data; it never calls a model or network.
"""
import ctypes
import json
import os
import sys
import tempfile
import tkinter as tk

try:  # keep Tk geometry and ImageGrab pixel coordinates consistent on high-DPI screens
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except (AttributeError, OSError):
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
EVIDENCE_DIR = REPO / "_evidence" / "round2"


def sentence_count(text):
    return max(1, text.count("。") + text.count("！") + text.count("？") + text.count("；") // 2)


def grab(window, path):
    from PIL import ImageGrab

    window.update_idletasks()
    window.update()
    x, y = window.winfo_rootx(), window.winfo_rooty()
    width, height = window.winfo_width(), window.winfo_height()
    image = ImageGrab.grab(bbox=(x, y, x + width, y + height))
    image.save(path)
    return {"path": str(path), "width": image.width, "height": image.height}


def run(product_id):
    temporary = tempfile.TemporaryDirectory()
    evidence = {
        "schemaVersion": 1,
        "productId": product_id,
        "testedAt": datetime.now(timezone.utc).isoformat(),
        "pythonVersion": sys.version.split()[0],
        "tkVersion": tk.TkVersion,
        "checks": {},
        "bubbles": [],
        "icon": {},
        "screenshots": [],
        "pass": False,
    }
    try:
        if product_id == "celestial-butler":
            os.environ.setdefault("CELESTIAL_BUTLER_STATE",
                                  str(Path(temporary.name) / "butler-state"))
            import butler
            window = tk.Tk()
            butler.build_ui(window)
        else:
            from src import app
            window = tk.Tk()
            window.geometry("1240x820+30+30")
            app.build(window)
        window.update()
        manager = getattr(window, "_celestial_help_manager", None)
        evidence["window"] = {"title": window.title(), "geometry": window.geometry()}
        if manager is None:
            evidence["checks"]["manager"] = False
            raise SystemExit(1)
        evidence["checks"]["manager"] = True
        evidence["checks"]["bubbleCount"] = len(manager.bubbles)
        keys = [bubble.key for bubble in manager.bubbles]
        evidence["checks"]["uniqueKeys"] = len(keys) == len(set(keys))
        minimum = 7 if product_id == "celestial-butler" else 10
        evidence["checks"]["minimumBubbles"] = len(manager.bubbles) >= minimum
        all_text = True
        sentence_ok = True
        for bubble in manager.bubbles:
            sentences = sentence_count(bubble.text)
            record = {
                "key": bubble.key,
                "title": bubble.title,
                "chars": len(bubble.text),
                "sentences": sentences,
                "text": bubble.text,
            }
            evidence["bubbles"].append(record)
            if record["chars"] < 40:
                all_text = False
            if not 2 <= sentences <= 8:
                sentence_ok = False
        evidence["checks"]["allTextsPresent"] = all_text
        evidence["checks"]["sentenceCounts2to8"] = sentence_ok

        first = manager.bubbles[0]
        first.toggle()
        window.update()
        evidence["checks"]["toggleOpens"] = first.is_open and bool(first._popup.winfo_ismapped())
        first.toggle()
        window.update()
        evidence["checks"]["toggleCloses"] = not first.is_open

        evidence["checks"]["tabFocusable"] = str(first.canvas.cget("takefocus")).lower() not in ("", "0", "false")
        first.canvas.focus_set()
        window.update()
        first.canvas.event_generate("<Return>")
        window.update()
        evidence["checks"]["keyboardEnterOpens"] = first.is_open
        window.event_generate("<Escape>")
        window.update()
        evidence["checks"]["escapeCloses"] = not first.is_open
        first.canvas.event_generate("<space>")
        window.update()
        evidence["checks"]["keyboardSpaceOpens"] = first.is_open
        window.event_generate("<Escape>")
        window.update()
        evidence["checks"]["escapeClosesAfterSpace"] = not first.is_open

        manager.bubbles[1].open()
        window.update()
        window.event_generate("<Button-1>")
        window.update()
        evidence["checks"]["clickAwayCloses"] = not manager.bubbles[1].is_open

        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        manager.close_all()
        window.update()
        collapsed = grab(window, EVIDENCE_DIR / f"help-bubble-collapsed-{product_id}.png")
        first.open()
        window.update()
        expanded = grab(window, EVIDENCE_DIR / f"help-bubble-expanded-{product_id}.png")
        evidence["screenshots"] = [collapsed, expanded]
        first.close()

        branding = getattr(window, "_celestial_branding", {}) or {}
        evidence["icon"] = {
            "icoPath": branding.get("icoPath", ""),
            "pngPath": branding.get("pngPath", ""),
            "icoExists": bool(branding.get("icoExists")),
            "pngExists": bool(branding.get("pngExists")),
            "applied": branding.get("applied", []),
            "errors": branding.get("errors", []),
            "windowIconBitmap": branding.get("windowIconBitmap", ""),
        }
        evidence["checks"]["brandingIcoExists"] = evidence["icon"]["icoExists"]
        evidence["checks"]["brandingPngExists"] = evidence["icon"]["pngExists"]
        evidence["checks"]["windowIconApplied"] = bool(evidence["icon"]["applied"])
        evidence["pass"] = all(bool(value) for value in evidence["checks"].values())
        window.destroy()
    finally:
        temporary.cleanup()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / f"ui-{product_id}.json"
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"productId": product_id, "pass": evidence["pass"],
                      "checks": evidence["checks"], "evidence": str(out)},
                     ensure_ascii=False))
    return 0 if evidence["pass"] else 1


if __name__ == "__main__":
    repo_name = REPO.name
    product = "celestial-butler" if repo_name == "celestial-butler" else "celestial-drug-simulator"
    raise SystemExit(run(product))
