# coding: utf-8
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.listview import ListItemButton
from kivy.uix.popup import Popup
from kivy.adapters.simplelistadapter import SimpleListAdapter
from kivy.properties import (
        ObjectProperty, ListProperty, StringProperty, AliasProperty,
        BooleanProperty, NumericProperty)

from kivy.network.urlrequest import UrlRequest
from ConfigParser import SafeConfigParser

DEFAULTSETTINGSFILE= '.default_config.ini'
SETTINGSFILE = 'config.ini'


__version__ = '0.01'


class SyncPopup(Popup):
    progress = NumericProperty(0)
    done = BooleanProperty(False)
    errors = ListProperty([])


class NdfApp(App):
    datalist_adapter = ObjectProperty(None)
    datalist = ListProperty([])
    settings = ObjectProperty()
    requests = ListProperty([])

    def __init__(self, **kwargs):
        super (NdfApp, self).__init__(**kwargs)
        self.datalist_adapter = SimpleListAdapter(
                data=self.datalist[:],
                cls=ListItemButton,
                args_converter=self.data_converter,
                )


    def build(self):
        settings = SafeConfigParser()
        print '%s: loaded' % settings.read((
            DEFAULTSETTINGSFILE,
            SETTINGSFILE))

        # need to load config *before* assigning to self.settings
        self.settings = settings

        print self.datalist_adapter
        return super(NdfApp, self).build()

    def send(self, note):
        body = {
        }

        self.requests.append(UrlRequest(
            self.settings.get('settings', 'server'),
            on_success=self.send_success,
            on_failure=self.send_failure,
            req_body=body
            )
        )

    def send_success(self, *args):
        self.settings.remove_option('tosync', n[0])
        self.popup.progress += 1

    def send_failure(self, *args):
        self.popup.progress += 1
        self.popup.errors.append('error treating %s: %s' % (n[0], e))

    def sync(self, *args):
        notes = self.settings.items('tosync')
        self.popup = SyncPopup()
        self.popup.open()

        for n in notes:
            self.send(n)

    def on_pause(self, *args):
        with open(SETTINGSFILE, 'w') as f:
            self.settings.write(f)
        return True

    def on_stop(self, *args):
        with open(SETTINGSFILE, 'w') as f:
            self.settings.write(f)
        return True

    def on_resume(self, *args):
        return True

    def on_datalist(self, *args):
        self.datalist_adapter.data = self.datalist[:]

    def data_converter(self, row_index, element):
        return {
            'text': element['title'],
            'size_hint_y': None,
            'height': '30sp'
            }

class FirstScreen(Screen):
    pass


class MenuScreen(Screen):
    pass


class AddScreen(Screen):
    ndf_type = StringProperty('')

    def on_ndf_type(self, *args):
        print 'type changed: %s' % str(args)


class BacklogScreen(Screen):
    pass


if __name__ == '__main__':
    NdfApp().run()
