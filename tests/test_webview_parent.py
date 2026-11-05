import unittest
from src.webview_host import require_native_parent


class NativeParentTests(unittest.TestCase):
    def test_successful_parenting_ignores_unreliable_last_error(self):
        # Real Win32 reproduction: SetParent returned the expected HWND,
        # GetParent matched, but last_error remained ERROR_ACCESS_DENIED.
        require_native_parent(actual=398186, expected=398186, error=5)

    def test_wrong_parent_is_rejected_with_or_without_error(self):
        for error in (0, 5):
            with self.subTest(error=error), self.assertRaises(OSError):
                require_native_parent(actual=0, expected=398186, error=error)


if __name__ == '__main__':
    unittest.main()
