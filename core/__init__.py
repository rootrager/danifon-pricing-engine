# core package - urllib3 polyfill for PTB v13 compatibility
import sys
import types
import urllib3

if not hasattr(urllib3, 'contrib'):
    urllib3.contrib = types.ModuleType('urllib3.contrib')
    sys.modules['urllib3.contrib'] = urllib3.contrib

if 'urllib3.contrib.appengine' not in sys.modules:
    appengine_mock = types.ModuleType('urllib3.contrib.appengine')
    appengine_mock.is_appengine = lambda: False
    appengine_mock.is_appengine_sandbox = lambda: False
    sys.modules['urllib3.contrib.appengine'] = appengine_mock
    urllib3.contrib.appengine = appengine_mock
