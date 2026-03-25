import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_xbmc_stubs():
    xbmc = types.ModuleType("xbmc")
    xbmc.LOGWARNING = 2
    xbmc.LOGERROR = 4
    xbmc.log = MagicMock()
    sys.modules["xbmc"] = xbmc

    xbmcaddon = types.ModuleType("xbmcaddon")
    xbmcaddon.Addon = MagicMock(return_value=MagicMock())
    sys.modules["xbmcaddon"] = xbmcaddon

    xbmcgui = types.ModuleType("xbmcgui")
    xbmcgui.Dialog = MagicMock(return_value=MagicMock())
    xbmcgui.ListItem = MagicMock()
    xbmcgui.NOTIFICATION_ERROR = "error"
    sys.modules["xbmcgui"] = xbmcgui

    xbmcplugin = types.ModuleType("xbmcplugin")
    for name in ("addDirectoryItem", "setContent", "endOfDirectory", "setResolvedUrl"):
        setattr(xbmcplugin, name, MagicMock())
    sys.modules["xbmcplugin"] = xbmcplugin


@pytest.fixture(scope="session")
def plugin():
    _install_xbmc_stubs()
    saved = sys.argv[:]
    sys.argv[:] = ["plugin://plugin.video.topradio.be/", "42", ""]
    for key in list(sys.modules):
        if key == "resources.lib.plugin" or key.startswith("resources.lib.plugin."):
            del sys.modules[key]
    import importlib

    mod = importlib.import_module("resources.lib.plugin")
    sys.argv[:] = saved
    return mod
