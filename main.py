# -*- coding: utf-8 -*-
''' Kivy interface to manage expenses in autonomie
'''
import json

from ConfigParser import SafeConfigParser
from kivy.app import App
from kivy.logger import Logger
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.listview import ListItemButton
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.adapters.simplelistadapter import SimpleListAdapter
from kivy.properties import (
                BooleanProperty,
                ListProperty,
                NumericProperty,
                ObjectProperty,
                StringProperty,
                DictProperty,
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
    settings = ObjectProperty()

    def __init__(self, **kwargs):
        super(NdfApp, self).__init__(**kwargs)
        self.datalist = []
        self.datalist_adapter = SimpleListAdapter(
            data=self.datalist,
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
        Logger.info("Ndf : Checking auth : NDFAPP")
        _connection = self.get_connection()
        _connection.check_auth(self.check_auth_success, self.check_auth_error)

    def check_auth_success(self, request, resp):
        """
            Launched if the authentication test succeeded
        """
        if request.resp_status == 301:
            self.check_auth_redirect(request, resp)
        elif hasattr(resp, 'get') and resp.get('status') == 'success':
            Logger.info("Ndf : Authentication test succeeded")
            self.fetch_options()
        else:
            Logger.info("Ndf : Authentication test failed")
            self.check_auth_error()

    def check_auth_error(self, *args):
        """
            Launched if the authentication test failed
        """
        self.dialog(
                title=u"Erreur d'authentification",
                text=u"Veuillez vérifier votre configuration"
                )

    def check_auth_redirect(self, request, resp):
        """
            Launch if the authentication test faced a redirect
        """
        # 1- Change the url
        # 2- Launch the check_auth again
        Logger.info("Ndf : Page has moved permanently, we change the url")
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
        if resp.get('status', 'error') == 'success':
            self.store_options(resp.get('result'))
        else:
            self.fetch_options_error(request, resp)
        self.dialog(
                title=u"Configuration réussie",
                text=u"Votre application a bien été configurée")

    def fetch_options_error(self, request, resp):
        """
            Error while fetching options
        """
        self.dialog(
                title=u"Erreur à la configuration",
                text=u"Une erreur inconnue a été rencontrée lors de la " \
                        "configuration de l'application.")

    def store_options(self, options):
        """
            Store expensetypes (options) retrieved from the server
        """
        Logger.info("Ndf : Storing options %s" % options)
        if not self.settings.has_section('main'):
            self.settings.add_section('main')
        self.settings.set('main', 'expensetypes', json.dumps(options))
        self.property('settings').dispatch(self)

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

    def dialog(self, title, text):
        """
            Fires a simple dialog popup
        """
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text=text))
        btnclose = Button(text="Fermer")
        content.add_widget(btnclose)
        popup_ = Popup( title=title, content=content )
        btnclose.bind(on_release=popup_.dismiss)
        popup_.open()

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

    def data_converter(self, row_index, element):
        return {
            'text': element['title'],
            'size_hint_y': None,
            'height': '30sp'
            }

    def store_expense(self, screen_name):
        manager = self.root.ids.screenmanager
        screen = manager.get_screen(screen_name)
        expense = screen.expense
        # TODO: add validation
        if expense:
            Logger.debug("Ndf : Storing an expense %s" % expense)
            self.datalist_adapter.data.append(expense)
            self.property('datalist_adapter').dispatch(self)
            screen.expense = {}


class AddScreen(Screen):
    ndf_type = StringProperty('Type de frais')

    def on_ndf_type(self, screen, value):
        if value == 'km':
            self.manager.transition.direction = 'left'
            self.manager.current = "kmform"
        elif value == 'tel':
            pass
        else:
            pass
        # Reset the spinner to the default value
        self.ndf_type = "Type de frais"


class KmFormScreen(Screen):
    expense = DictProperty({})

    def set_value(self, key, value):
        Logger.debug(u"Ndf : Setting a value for {0} : {1}".format(key, value))
        self.expense[key] = value


if __name__ == '__main__':
    NdfApp().run()
