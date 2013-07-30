#coding: utf-8
''' Connection object to manage the communication with autonomie server
'''

import urlparse

from kivy.network.urlrequest import UrlRequest
from kivy.event import EventDispatcher
from kivy.properties import (
        ObjectProperty, StringProperty, DictProperty, ListProperty)
from kivy.logger import Logger

from functools import partial
from json import JSONDecoder, JSONEncoder

JSON_ENCODE = JSONEncoder().encode
JSON_DECODE = JSONDecoder().raw_decode

API_PATH = '/api/v1/'

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
        if not self.server.endswith('/'):
            self.server += '/'
        base_url = urlparse.urljoin(self.server, API_PATH)

        if any(base_url.startswith(scheme)
            for scheme in ('http://', 'https://')):
            self._base_url = base_url
        else:
            self._base_url = 'http://%s' % base_url

        Logger.info('computed base_url: %s' % self._base_url)
        return self._base_url

    def _get_headers(self):
        """
            Return the headers used to request the remote rest api
        """
        headers = {'Content-type': 'text/json',
                'Accept': 'text/json',
                'X-Requested-With':'XMLHttpRequest'
                }
        if self.cookie is not None:
            headers["Cookie"] = self.cookie
        return headers

    def _get_request(self, url, body, on_success, on_error, on_progress=None, \
            **kwargs):
        headers = self._get_headers()
        return UrlRequest(
                url,
                req_body=body,
                req_headers=headers,
                on_success=on_success,
                on_error=on_error,
                on_progress=on_progress,
                **kwargs)

    def _get_credentials(self):
        """
            Return the credentials used for the auth request
        """
        Logger.debug("Credentials : {0} {1}".format(self.login, self.password))
        return JSON_ENCODE({
                'login': self.login,
                'password': self.password,
                'submit': 'submit', # reserved for future use
                })


    def request(self, path, req_body, **kwargs):
        ''' Base method to send requests to server, autoconnect if needed
        '''
        base_url = self.base_url()
        if not self.cookie:
            Logger.info("Ndf: not logged in, authenticating")

            # get a cookie then call again
            body = self._get_credentials()

            Logger.info(body)

            accept_login = partial(
                    self.auth_redirect,
                    path,
                    req_body=req_body,
                    #on_progress=Logger.info,
                    **kwargs
                    )
            on_error = partial(self.connection_error,
                        error=r"Impossible de contacter le serveur renseigné "\
                                "dans la configuration, veuillez vérifier "\
                                "que l'adresse est correcte.")


            request = self._get_request(
                    base_url + '/login',
                    body,
                    accept_login,
                    on_error)


        else:
            on_success = kwargs.pop('on_success', None)
            on_error = kwargs.pop('on_error', None)
            on_progress = kwargs.pop('on_progress', None)

            body = JSON_ENCODE(req_body)
            url = urlparse.urljoin(base_url, path)
            Logger.info("   + Calling the following url : %s" % url)

            request = self._get_request(
                    url,
                    body,
                    on_success,
                    on_error,
                    on_progress,
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
        Logger.info("Successfully sent the expense :")
        Logger.info(expense)
        Logger.info(args)
        self.to_sync.pop()

    def send_error(self, expense, *args):
        ''' Indicate an error to the user, keep the expense in record.
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

        for _id, data  in expenses.items():
            Logger.info(_id)
            Logger.info(data)
            self.send(data)


    def check_auth(self, success, error):
        """
            Check authentification and launch the callback
        """
        url = self.base_url() + '/login'
        body = self._get_credentials()
        request = self._get_request(url, body, success, error)
