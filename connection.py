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

    def auth_redirect(self, path, request, result, **kwargs):
        ''' This should be called when a connection request succeed
        '''
        Logger.info("Ndf: Must authenticate: %s")
        self.cookie = request.resp_headers.get('set-cookie')
        if result['status'] == 'success':
            self.request(path, **kwargs)
        else:
            self.connection_error(
                    request,
                    error='Erreur de connection, merci de vérifier vos'
                          'identifiants\n')


    def base_url(self):
        """
        returns the url for the application. Value is cached.
        """
        if hasattr(self, '_base_url'):
            return self._base_url
        base_url = self.server + API_PATH

        if any(base_url.startswith(scheme)
            for scheme in ('http://', 'https://')):
            self._base_url = base_url
        else:
            self._base_url = 'https://%s' % base_url

        Logger.info('computed base_url: %s' % self._base_url)
        return self._base_url

    def request(self, path, req_body, **kwargs):
        ''' Base method to send requests to server, autoconnect if needed
        '''
        base_url = self.base_url()
        if not self.cookie:
            Logger.info("Ndf: not logged in, authenticating")

            # get a cookie then call again
            body = JSON_ENCODE({
                'login': self.login,
                'password': self.password,
                'submit': 'submit', # reserved for future use
                })

            headers = {
                'X-Requested-With': 'XMLHttpRequest',
                }

            Logger.info(body)
            accept_login = partial(
                    self.auth_redirect,
                    path,
                    req_body=req_body,
                    on_progress=Logger.info,
                    **kwargs)

            request = UrlRequest(
                    base_url + '/login',
                    req_body=body,
                    req_headers=headers,
                    on_success=accept_login,
                    on_redirect=accept_login,
                    #on_progress=lambda *x: Logger.info(str(x)),
                    on_error=partial(self.connection_error,
                        error=r"Impossible de contacter le serveur renseigné "\
                                "dans la configuration, veuillez vérifier "\
                                "que l'adresse est correcte.")
                )


        else:
            on_success = kwargs.pop('on_success', None)
            on_error = kwargs.pop('on_error', None)
            on_progress = kwargs.pop('on_progress', None)
            import pudb; pudb.set_trace()

            body = JSON_ENCODE(kwargs)

            request = UrlRequest(
                    base_url + path,
                    req_body=body,
                    on_success=on_success,
                    on_error=on_error,
                    on_progress=on_progress,
                    #on_progress=Logger.info,
                    **kwargs
                    )

        # FIXME remove these requests when they are done
        self.requests.append(request)

    def send(self, expense):
        ''' Try to send an expense to the server, if the request success,
            the expense should be removed from the 'tosync' expenses, else, the
            error should be displayed.
        '''
        self.request(
                'expenses',
                method='POST',
                on_success=partial(self.send_success, expense),
                on_error=partial(self.send_error, expense),
                req_body=expense
                )

    def send_success(self, expense, *args):
        ''' Take note that the expense was accepted by the server.
        '''
        print expense, args
        print "success"
        self.to_sync.pop()

    def send_error(self, expense, *args):
        ''' Indicate a error to the user, keep the expense in record.
        '''
        self.errors.append(expense[0], args)

    def connection_error(self, request, error='Undefined error', *args):
        '''
        '''
        Logger.info(error)
        self.errors.append(error)
        Logger.debug('%s' % request)

    def sync(self, *args):
        ''' Send requests to sync all the pending expenses
        '''
        expenses = self.to_sync

        #import pudb; pudb.set_trace()
        for _id, data  in expenses.items():
            print _id, data
            self.send(data)
