import ctypes
import ctypes.wintypes
import threading
import winreg

# Windows constants
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_QUIT = 0x0012

VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_TAB = 0x09
VK_F4 = 0x73
VK_ESCAPE = 0x1B
VK_ALT = 0x12

REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Policies\System"
REGISTRY_VALUE = "DisableTaskMgr"
AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "FlexionLock"

HOOKPROC = ctypes.WINFUNCTYPE(
    ctypes.c_int,
    ctypes.c_int,
    ctypes.wintypes.WPARAM,
    ctypes.wintypes.LPARAM,
)


class LockManager:
    def __init__(self):
        self._hook_handle = None
        self._hook_thread = None
        self._hook_thread_id = None
        self._callback_ref = None   # keep reference to prevent GC
        self._lock_screen = None
        self._hook_ready = threading.Event()

    # ------------------------------------------------------------------ public

    def lock(self, lock_screen) -> None:
        if self._hook_thread is not None:  # already locked
            return
        self._lock_screen = lock_screen
        self._disable_task_manager()
        self._install_keyboard_hook()
        lock_screen.showFullScreen()

    def unlock(self) -> None:
        self._remove_keyboard_hook()
        self._enable_task_manager()
        if self._lock_screen:
            self._lock_screen.close()
            self._lock_screen = None

    def set_autostart(self, enabled: bool, exe_path: str) -> None:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE
        )
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)

    # ------------------------------------------------------------ task manager

    def _disable_task_manager(self) -> None:
        try:
            key = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                REGISTRY_KEY,
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.SetValueEx(key, REGISTRY_VALUE, 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
        except OSError:
            pass  # best effort

    def _enable_task_manager(self) -> None:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                REGISTRY_KEY,
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.DeleteValue(key, REGISTRY_VALUE)
            winreg.CloseKey(key)
        except (FileNotFoundError, OSError):
            pass

    # ----------------------------------------------------------- keyboard hook

    def _install_keyboard_hook(self) -> None:
        self._hook_ready.clear()
        self._hook_thread = threading.Thread(
            target=self._hook_message_loop, daemon=True
        )
        self._hook_thread.start()

    def _hook_message_loop(self) -> None:
        import win32api
        self._hook_thread_id = win32api.GetCurrentThreadId()
        self._hook_ready.set()

        def _callback(nCode, wParam, lParam):
            if nCode >= 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                vk = ctypes.cast(lParam, ctypes.POINTER(ctypes.c_ulong))[0]
                if self._should_block(vk):
                    return 1
            return ctypes.windll.user32.CallNextHookEx(
                self._hook_handle, nCode, wParam, lParam
            )

        self._callback_ref = HOOKPROC(_callback)
        self._hook_handle = ctypes.windll.user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._callback_ref, None, 0
        )

        # Windows message loop — required for low-level keyboard hooks
        msg = ctypes.wintypes.MSG()
        while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

        if self._hook_handle:
            ctypes.windll.user32.UnhookWindowsHookEx(self._hook_handle)
            self._hook_handle = None

    def _should_block(self, vk: int) -> bool:
        if vk in (VK_LWIN, VK_RWIN, VK_ESCAPE):
            return True
        alt_down = bool(ctypes.windll.user32.GetAsyncKeyState(VK_ALT) & 0x8000)
        if vk == VK_TAB and alt_down:
            return True
        if vk == VK_F4 and alt_down:
            return True
        return False

    def _remove_keyboard_hook(self) -> None:
        if self._hook_thread is not None:
            self._hook_ready.wait(timeout=1.0)
            if self._hook_thread_id is not None:
                ctypes.windll.user32.PostThreadMessageW(
                    self._hook_thread_id, WM_QUIT, 0, 0
                )
                self._hook_thread_id = None
            self._hook_thread.join(timeout=2.0)
            self._hook_thread = None
        self._callback_ref = None
