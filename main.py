# coding: utf-8
''' Kivy interface to manage expenses in autonomie
'''

from ConfigParser import SafeConfigParser
from kivy.app import App
from kivy.logger import Logger
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.listview import ListItemButton
from kivy.uix.popup import Popup
from kivy.adapters.simplelistadapter import SimpleListAdapter
from kivy.properties import (
                BooleanProperty,
                ListProperty,
                NumericProperty,
                ObjectProperty,
                StringProperty,
                )
from connection import Connection

DEFAULTSETTINGSFILE = '.default_config.ini'
SETTINGSFILE = 'config.ini'
SETTINGS_FILES = DEFAULTSETTINGSFILE, SETTINGSFILE

__version__ = '0.01'


def get_base_url(url):
    """
        Return scheme + location
    """
    import urlparse
    result = urlparse.urlsplit(url)
    scheme = result.scheme or 'http'
    return "{0}://{1}/".format(scheme, result.netloc)


class SyncPopup(Popup):
    ''' This popup display the current syncing state in the app
    '''
    progress = NumericProperty(0)
    done = BooleanProperty(False)
    errors = ListProperty([])


class NdfApp(App):
    ''' #TODO
    '''
    datalist_adapter = ObjectProperty(None)
    datalist = ListProperty([])
    settings = ObjectProperty()
    check_auth_token = StringProperty(u"")

    def __init__(self, **kwargs):
        super(NdfApp, self).__init__(**kwargs)
        self.datalist_adapter = SimpleListAdapter(
            data=self.datalist[:],
            cls=ListItemButton,
            args_converter=self.data_converter)

    def get_connection(self):
        """
            Return a connection object
        """
        return Connection(
            login=self.settings.get('settings', 'login'),
            password=self.settings.get('settings', 'password'),
            server=self.settings.get('settings', 'server'),
            to_sync=self.settings.items('tosync'),
            )

    def sync(self, *args):
        ''' Sync the pending expenses to remote server
        '''
        self._connection = self.get_connection()

        self.popup = SyncPopup()
        self.popup.open()
        self._connection.bind(to_sync=self.update_to_sync)
        self._connection.bind(errors=self.popup.setter('errors'))
        self._connection.sync()

    def check_configuration(self):
        self.check_auth()

    def check_auth(self):
        """
            Launch an authentication check
        """
        Logger.info("Checking auth : NDFAPP")
        _connection = self.get_connection()
        _connection.check_auth(self.check_auth_success, self.check_auth_error)

    def check_auth_success(self, request, resp):
        """
            Launched if the authentication test succeeded
        """
        if request.resp_status == 301:
            self.check_auth_redirect(request, resp)
        elif hasattr(resp, 'get') and resp.get('status') == 'success':
            Logger.info("Authentication test succeeded")
            self.check_auth_token = u"Authentification réussie"
            self.fetch_options()
        else:
            Logger.info("Authentication test failed")
            self.check_auth_error()

    def check_auth_error(self, *args):
        """
            Launched if the authentication test failed
        """
        self.check_auth_token = u"Erreur d'authentification"

    def check_auth_redirect(self, request, resp):
        """
            Launch if the authentication test faced a redirect
        """
        # 1- Change the url
        # 2- Launch the check_auth again
        Logger.info("Page has moved permanently, we change the url")
        #The page has moved permanently
        url = self.settings.get('settings', 'server')
        new_url = request.resp_headers.get('location', url)
        new_url = get_base_url(new_url)

        self.settings.set('settings', 'server', new_url)
        self.property('settings').dispatch(self)
        self.check_auth()

    def fetch_options(self):
        """
            Fetch options for expense configuration
        """
        path = "expenseoptions"
        conn = self.get_connection()
        conn.request(
                path,
                {},
                on_success=self.fetch_options_success,
                on_error=self.fetch_options_error)

    def fetch_options_success(self, request, resp):
        """
            Fetch options success handler
        """
        Logger.info("%s" % resp)
        if resp.get('status', 'error') == 'success':
            self.store_options(resp.get('result'))
        else:
            self.fetch_options_error(request, resp)

    def fetch_options_error(self, request, resp):
        """
            Error while fetching options
        """
        self.check_auth_token = u"Une erreur inconnue est survenue"

    def store_options(self, options):
        Logger.info("Storing options %s" % options)

    def update_to_sync(self, *args):
        Logger.info('Ndf: FIXME: update_to_sync %s' % args)

    def sync_update(self, *args):
        self._connection = None
        Logger.warn("Ndf: FIXME: here, really update")

    def build(self):
        settings = self.load_settings()
        # need to load config *before* assigning to self.settings
        self.settings = settings

        return super(NdfApp, self).build()

    def load_settings(self):
        settings = SafeConfigParser()
        loaded_settings = settings.read(SETTINGS_FILES)
        Logger.debug("Ndf: loaded settings: %s", loaded_settings)
        return settings

    def get(self, on_success=None, on_error=None, **kwargs):
        if kwargs:
            # TODO we want to use kwargs to filter
            pass

        else:
            self.request('path')

    def popup_auth_error(self, *args):
        Logger.warning("Ndf: Erreur d'authentification")
        p = Popup(
            title="Erreur d'authentification",
            content=Label(text=u'Vérifiez la configuration')
            )
        Logger.debug("Ndf: popup for auth error (%s)", p)

    def on_pause(self, *args):
        ''' Implement on_pause to save data before going to sleep on android.
        '''
        return self.save_settings()

    def on_stop(self, *args):
        ''' Called when the application is stopped, save data.
        '''
        return self.save_settings()

    def save_settings(self):
        with open(SETTINGSFILE, 'w') as f:
            self.settings.write(f)
        return True

    def on_resume(self, *args):
        ''' Allow resuming app
        '''
        return True

    def on_datalist(self, *args):
        '''
        '''
        self.datalist_adapter.data = self.datalist[:]

    def data_converter(self, row_index, element):
        return {
            'text': element['title'],
            'size_hint_y': None,
            'height': '30sp'
            }


class AddScreen(Screen):
    ndf_type = StringProperty('')

    def on_ndf_type(self, *args):
        Logger.debug("Ndf: note type changed: %s", str(args))


if __name__ == '__main__':
    NdfApp().run()
