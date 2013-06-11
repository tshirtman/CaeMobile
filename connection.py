#coding: utf-8
''' Connection object to manage the communication with autonomie server
'''
from kivy.network.urlrequest import UrlRequest
from kivy.event import EventDispatcher
from kivy.properties import (
        ObjectProperty, StringProperty, DictProperty, ListProperty)
from kivy.logger import Logger

from functools import partial
from json import JSONDecoder, JSONEncoder

JSON_ENCODE = JSONEncoder().encode
JSON_DECODE = JSONDecoder().raw_decode

API_PATH = '/api/v1'

class Connection(EventDispatcher):
    ''' see module config
    '''
    cookie = ObjectProperty(None)
    server = StringProperty('')
    login = StringProperty('')
    password = StringProperty('')
    requests = ListProperty([])
    to_sync = DictProperty({})
    errors = ListProperty([])

    def auth_redirect(self, resp, path, *args, **kwargs):
        ''' This should be called when a connection request succeed
        '''
        Logger.info("Ndf: Must authenticate: %s", resp)
        self.cookie = resp.headers.get('set-cookie')
        self.request(path, *args, **kwargs)

    def request(self, path, on_success, on_error, **kwargs):
        ''' Base method to send requests to server, autoconnect if needed
        '''
        base_url = self.server + API_PATH
        if not base_url.startswith('http://'):
            base_url = 'http://' + base_url

        if not self.cookie:
            Logger.info("Ndf: not logged in, authenticating")
            # get a cookie then call again
            body = JSON_ENCODE({
                'login': self.login,
                'password': self.password,
                'submit': '', # reserved for future use
                'X-Requested-With': 'XMLHttpRequest',
                })

            request = UrlRequest(
                    base_url + '/login',
                    method='POST',
                    req_body=body,
                    on_success=partial(
                        self.auth_redirect,
                        path,
                        on_success=on_success,
                        on_error=on_error,
                        on_progress=Logger.info,
                        **kwargs),
                    on_error=self.connection_error)

        else:
            body = JSON_ENCODE(kwargs)
            request = UrlRequest(
                    base_url + path,
                    req_body=body,
                    on_success=on_success,
                    on_error=on_error,
                    on_progress=Logger.info
                    )

        self.requests.append(request)

    def send(self, expense):
        ''' Try to send an expense to the server, if the request success,
            the expense should be removed from the 'tosync' expenses, else, the
            error should be displayed.
        '''
        body = JSON_ENCODE(expense)

        self.request(
                'expenses',
                method='POST',
                req_body=body,
                on_success=partial(self.send_success, expense),
                on_error=partial(self.send_error, expense)
                )

    def send_success(self, expense, *args):
        ''' Take note that the expense was accepted by the server.
        '''
        print expense, args
        self.to_sync.pop()

    def send_error(self, expense, *args):
        ''' Indicate a error to the user, keep the expense in record.
        '''
        self.errors.append(expense[0], args)

    def connection_error(self, *args):
        '''
        '''
        self.errors.append(
                u'Erreur de connection, merci de vérifier vos identifiants')
        print args

    def sync(self, *args):
        ''' Send requests to sync all the pending expenses
        '''
        expenses = self.to_sync

        for exp in expenses:
            self.send(exp)
