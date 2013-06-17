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
from kivy.properties import (BooleanProperty, ListProperty, NumericProperty,
                             ObjectProperty, StringProperty)
from connection import Connection

DEFAULTSETTINGSFILE = '.default_config.ini'
SETTINGSFILE = 'config.ini'
SETTINGS_FILES = DEFAULTSETTINGSFILE, SETTINGSFILE

__version__ = '0.01'


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

    def __init__(self, **kwargs):
        super(NdfApp, self).__init__(**kwargs)
        self.datalist_adapter = SimpleListAdapter(
            data=self.datalist[:],
            cls=ListItemButton,
            args_converter=self.data_converter)

    def sync(self, *args):
        ''' Sync the pending expenses to remote server
        '''
        self._connection = Connection(
            login=self.settings.get('settings', 'login'),
            password=self.settings.get('settings', 'password'),
            server=self.settings.get('settings', 'server'),
            to_sync=self.settings.items('tosync'),
            )

        self.popup = SyncPopup()
        self.popup.open()
        self._connection.bind(to_sync=self.update_to_sync)
        self._connection.bind(errors=self.popup.setter('errors'))
        self._connection.sync()

    def update_to_sync(self, *args):
        Logger.info('Ndf: FIXME: update_to_sync %s' % args)

    def sync_update(self, *args):

        self._connection = None
        Logger.warn("Ndf: FIXME: here, really update")

    def build(self):
        settings = SafeConfigParser()
        loaded_settings = settings.read(SETTINGS_FILES)
        Logger.debug("Ndf: loaded settings: %s", loaded_settings)

        # need to load config *before* assigning to self.settings
        self.settings = settings

        return super(NdfApp, self).build()

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
        with open(SETTINGSFILE, 'w') as f:
            self.settings.write(f)
        return True

    def on_stop(self, *args):
        ''' Called when the application is stopped, save data.
        '''
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
