"""Host-wide single-instance guard for Celestial Python products.

Contract: ``docs/Architecture/INSTALLER-CONTRACT.md`` v1, section 5.

Windows uses a named mutex ``Global\\Celestial.<productId>.<app>``.  When the
global namespace is unavailable (CreateMutexW denied) the guard falls back to an
exclusive file lock at ``%ProgramData%\\Celestial\\locks\\<productId>.lock``
(``FileShare.None`` semantics via a byte-range OS lock).  A second process never
starts a second UI: it tries to bring the existing window to the front and then
exits with ``CELESTIAL_ALREADY_RUNNING`` and exit code 3.

Tests use ``--instance-scope=state`` plus ``CELESTIAL_INSTANCE_STATE_ROOT`` to
get an isolated lock namespace instead of the real host-wide one.
"""
from __future__ import annotations

import ctypes
import hashlib
import os
import sys
from pathlib import Path

ALREADY_RUNNING = "CELESTIAL_ALREADY_RUNNING"
EXIT_ALREADY_RUNNING = 3
EXIT_LOCK_UNAVAILABLE = 4

_SCOPE_ARGUMENT = "--instance-scope"
_STATE_ROOT_ENV = "CELESTIAL_INSTANCE_STATE_ROOT"
_FORCE_FILE_LOCK_ENV = "CELESTIAL_INSTANCE_FORCE_FILE_LOCK"

_ERROR_ALREADY_EXISTS = 183
_SW_RESTORE = 9


def parse_instance_scope(argv=None):
    """Return ``(scope, cleaned_argv)`` and strip the test-only scope switch."""
    argv = list(sys.argv if argv is None else argv)
    scope = "global"
    cleaned = []
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument == _SCOPE_ARGUMENT and index + 1 < len(argv):
            scope = argv[index + 1]
            index += 2
            continue
        if argument.startswith(_SCOPE_ARGUMENT + "="):
            scope = argument.split("=", 1)[1]
            index += 1
            continue
        cleaned.append(argument)
        index += 1
    if scope not in {"global", "state"}:
        raise SystemExit(f"CELESTIAL_INSTANCE_SCOPE_INVALID: {scope}")
    return scope, cleaned


def _default_state_root(product_id):
    configured = os.environ.get(_STATE_ROOT_ENV)
    if configured:
        return Path(configured)
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(local) / "Celestial" / "instance-state" / product_id


class _FileLock:
    """Exclusive OS file lock; ``FileShare.None`` equivalent for this contract."""

    def __init__(self, path):
        self.path = Path(path)
        self._fd = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\0")
            os.lseek(fd, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, f"{os.getpid()}\n".encode("ascii", "replace"))
        except OSError:
            os.close(fd)
            return False
        self._fd = fd
        return True

    def release(self):
        if self._fd is None:
            return
        try:
            os.lseek(self._fd, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fd, fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            try:
                os.close(self._fd)
            finally:
                self._fd = None


def _acquire_mutex(name):
    """Create the named mutex. Return a handle, or ``None`` if it already exists."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_bool
    handle = kernel32.CreateMutexW(None, False, name)
    error = ctypes.get_last_error()
    if not handle:
        raise OSError(error, f"CreateMutexW failed for {name}")
    if error == _ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return None
    return handle


def _release_mutex(handle):
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle(handle)
    except (OSError, AttributeError):
        pass


class SingleInstance:
    """Acquire the host-wide (or test-scoped) Celestial instance lock."""

    def __init__(self, product_id, app, window_title=None, scope="global",
                 state_root=None, _force_file_lock=False):
        if scope not in {"global", "state"}:
            raise ValueError(f"unsupported instance scope: {scope}")
        self.product_id = product_id
        self.app = app
        if isinstance(window_title, str) or window_title is None:
            self.window_titles = [window_title] if window_title else []
        else:
            self.window_titles = [title for title in window_title if title]
        self.scope = scope
        self.state_root = Path(state_root) if state_root is not None else _default_state_root(product_id)
        self.force_file_lock = _force_file_lock
        self.mutex_name = self._mutex_name()
        self.lock_path = self._lock_path()
        self.acquired = False
        self.mode = None
        self._mutex = None
        self._file_lock = None
        self.last_error = None

    def _mutex_name(self):
        if self.scope == "state":
            digest = hashlib.sha256(str(self.state_root).casefold().encode("utf-8")).hexdigest()[:12]
            return f"Local\\Celestial.{self.product_id}.{self.app}.{digest}"
        return f"Global\\Celestial.{self.product_id}.{self.app}"

    def _lock_path(self):
        if self.scope == "state":
            return self.state_root / f"{self.product_id}.{self.app}.lock"
        program_data = os.environ.get("ProgramData") or "C:\\ProgramData"
        return Path(program_data) / "Celestial" / "locks" / f"{self.product_id}.lock"

    def acquire(self):
        """Return True when this process owns the lock, False if another holds it."""
        if self.acquired:
            return True
        use_file_lock = (os.name != "nt" or self.force_file_lock
                         or os.environ.get(_FORCE_FILE_LOCK_ENV) == "1")
        if not use_file_lock:
            try:
                self._mutex = _acquire_mutex(self.mutex_name)
            except OSError as error:
                self.last_error = f"mutex unavailable: {error}"
            else:
                if self._mutex is None:
                    self.mode = "mutex"
                    return False
                self.mode = "mutex"
                self.acquired = True
                return True
        return self._acquire_file_lock()

    def _acquire_file_lock(self):
        candidates = [self.lock_path]
        if self.scope == "global":
            # ProgramData may be read-only for standard users; never silently allow.
            local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
            candidates.append(Path(local) / "Celestial" / "locks" / f"{self.product_id}.lock")
        last_error = None
        for path in candidates:
            lock = _FileLock(path)
            try:
                acquired = lock.acquire()
            except OSError as error:
                last_error = f"{path}: {error}"
                continue
            if acquired:
                self._file_lock = lock
                self.lock_path = path
                self.mode = "file"
                self.acquired = True
                return True
            self.lock_path = path
            self.mode = "file"
            return False
        raise RuntimeError(
            f"CELESTIAL_INSTANCE_LOCK_UNAVAILABLE: {self.product_id}: {last_error or 'no lock path'}"
        )

    def focus_existing(self):
        """Best-effort: bring the first instance's window to the foreground."""
        if os.name != "nt":
            return False
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        user32.FindWindowW.restype = ctypes.c_void_p
        user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
        user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        user32.BringWindowToTop.argtypes = [ctypes.c_void_p]
        handles = []
        for title in self.window_titles:
            handle = user32.FindWindowW(None, title)
            if handle:
                handles.append(handle)
        if not handles:
            handles = self._find_by_title_fragment(user32)
        for handle in handles:
            user32.ShowWindow(handle, _SW_RESTORE)
            user32.SetForegroundWindow(handle)
            user32.BringWindowToTop(handle)
        return bool(handles)

    def _find_by_title_fragment(self, user32):
        handles = []
        if not self.window_titles:
            return handles
        enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows.argtypes = [enum_proc, ctypes.c_void_p]
        user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
        user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
        user32.IsWindowVisible.argtypes = [ctypes.c_void_p]

        def collect(handle, _):
            if not user32.IsWindowVisible(handle):
                return True
            length = user32.GetWindowTextLengthW(handle)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(handle, buffer, length + 1)
            title = buffer.value
            if any(title == wanted or title.startswith(wanted) for wanted in self.window_titles):
                handles.append(handle)
            return True

        user32.EnumWindows(enum_proc(collect), None)
        return handles

    def release(self):
        if self._mutex is not None:
            _release_mutex(self._mutex)
            self._mutex = None
        if self._file_lock is not None:
            self._file_lock.release()
            self._file_lock = None
        self.acquired = False

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(ALREADY_RUNNING)
        return self

    def __exit__(self, *_):
        self.release()

    def __del__(self):
        try:
            self.release()
        except Exception:  # pragma: no cover - interpreter teardown
            pass


def enforce_single_instance(product_id, app, window_title=None, argv=None):
    """Acquire the instance lock for a product ``main()`` entry point.

    Returns the held :class:`SingleInstance` guard (keep it referenced for the
    process lifetime).  Raises ``SystemExit(3)`` when another instance is
    already running, after printing ``CELESTIAL_ALREADY_RUNNING``.
    """
    scope, cleaned = parse_instance_scope(argv)
    guard = SingleInstance(product_id, app, window_title, scope=scope)
    if guard.acquire():
        sys.argv[:] = cleaned
        return guard
    focused = guard.focus_existing()
    message = (f"{ALREADY_RUNNING}: {product_id} is already running on this host; "
               "this second launch exited without starting another UI.")
    if focused:
        message = (f"{ALREADY_RUNNING}: {product_id} is already running; the existing "
                   "window was focused and this second launch exited.")
    if os.name == "nt" and sys.stderr is None:
        try:
            ctypes.windll.user32.MessageBoxW(None, message, "Celestial", 0x00000040)
        except Exception:  # pragma: no cover - GUI-less session
            pass
    else:
        print(message, file=sys.stderr)
    raise SystemExit(EXIT_ALREADY_RUNNING)
