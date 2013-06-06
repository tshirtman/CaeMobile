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
from functools import partial
from json import JSONDecoder, JSONEncoder

json_encode = JSONEncoder().encode
json_decode = JSONDecoder().raw_decode


DEFAULTSETTINGSFILE= '.default_config.ini'
SETTINGSFILE = 'config.ini'
API_PATH = '/api/v1'


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
    requests = ListProperty([])

    def __init__(self, **kwargs):
        super (NdfApp, self).__init__(**kwargs)
        self.datalist_adapter = SimpleListAdapter(
                data=self.datalist[:],
                cls=ListItemButton,
                args_converter=self.data_converter,
                )
        self._cookie = None


    def build(self):
        settings = SafeConfigParser()
        print '%s: loaded' % settings.read((
            DEFAULTSETTINGSFILE,
            SETTINGSFILE))

        # need to load config *before* assigning to self.settings
        self.settings = settings

        print self.datalist_adapter
        return super(NdfApp, self).build()

    def auth_redirect(self, resp, *args, **kwargs):
        print "got auth!", resp
        self._cookie = resp.headers.get('set-cookie')
        self.request(**kwargs)

    def popup_auth_failure(self, *args):
        print "failure, hmm"
        p = Popup(
            title="Erreur d'authentification",
            content=Label(text=u'Vérifiez la configuration')
            )

    def request(self, path, on_success=None, on_failure=None, **kwargs):
        base_url = self.settings.get('settings', 'server') + API_PATH

        if not self._cookie:
            # get a cookie then call again
            print "not logged"
            body = json_encode({
                'login': self.settings.get('settings', 'login'),
                'password': self.settings.get('settings', 'password'),
                'submit': '', # reserved for future use
                'X-Requested-With': 'XMLHttpRequest',
                })

            self.requests.append(
                    UrlRequest(
                        base_url + '/login',
                        method='POST',
                        req_body=body,
                        on_success=partial(
                            self.auth_redirect,
                            path,
                            on_success=on_success,
                            on_failure=on_failure,
                            **kwargs),
                        on_failure=self.popup_auth_failure))

        else:
            self.requests.append(
                    UrlRequest(
                        base_url + path,
                        req_body=body,
                        on_success=on_success,
                        on_failure=on_failure,
                        )
                    )

    def get(self, on_success=None, on_failure=None, **kwargs):
        if kwargs:
            # TODO we want to use kwargs to filter
            pass

        else:
            self.request('path')

    def send(self, expense):
        ''' Try to send an expense to the server, if the request success,
            the expense should be removed from the 'tosync' expenses, else, the
            error should be displayed.
        '''
        body = {
        }

        self.request(
            self.settings.get('settings', 'server') +  API_PATH,
            on_success=self.send_success,
            on_failure=self.send_failure,
            req_body=body
            )

    def send_success(self, *args):
        ''' Take note that the expense was accepted by the server.
        '''
        self.settings.remove_option('tosync', n[0])
        self.popup.progress += 1

    def send_failure(self, *args):
        ''' Indicate a failure to the user, keep the expense in record.
        '''
        self.popup.progress += 1
        self.popup.errors.append('error treating %s: %s' % (n[0], e))

    def sync(self, *args):
        ''' Send requests to sync all the pending expenses
        '''
        expenses = self.settings.items('tosync')
        self.popup = SyncPopup()
        self.popup.open()

        for e in expenses:
            self.send(e)

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
