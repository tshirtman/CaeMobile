# -*- coding: utf-8 -*-
''' Kivy interface to manage expenses in autonomie
'''
import json
import random
import datetime
import dateutil.parser
import subprocess

from functools import partial

from ConfigParser import SafeConfigParser
from kivy.app import App

from kivy.logger import Logger
from kivy.uix.screenmanager import (
    Screen,
    )
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.factory import Factory
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.utils import platform
from kivy.properties import (
    BooleanProperty,
    ListProperty,
    NumericProperty,
    ObjectProperty,
    StringProperty,
    DictProperty,
    )
from connection import Connection
from utils import (
    read_locale_date,
    write_locale_date,
    get_base_url,
    get_action_path_and_method,
    filter_expenses,
    )
platform = platform()

DEFAULTSETTINGSFILE = '.default_config.ini'
SETTINGSFILE = 'config.ini'
SETTINGS_FILES = DEFAULTSETTINGSFILE, SETTINGSFILE

__version__ = '0.01'


if platform == 'android':
    from jnius import autoclass
    Intent = autoclass('android.content.Intent')
    PythonActivity = autoclass('org.renpy.android.PythonActivity')
    Uri = autoclass('android.net.Uri')


class SyncPopup(Popup):
    ''' This popup display the current syncing state in the app
    '''
    progress = NumericProperty(0)
    done = BooleanProperty(False)
    errors = ListProperty([])


class SelectPrefilPopup(Popup):
    entries = ListProperty([])

    def on_entries(self, *args):
        # we may be not open yet, delay to next frame
        Clock.schedule_once(self.populate, 0)

    def populate(self, *args):
        print self.entries
        self.ids.container.clear_widgets()

        for e in self.entries:
            self.ids.container.add_widget(
                Factory.PrefilEntry(entry=e, popup=self))


class PrefilEntry(Button):
    entry = ObjectProperty(None)
    popup = ObjectProperty(None)


class ExpenseDispatcher(Widget):
    expense = DictProperty({})


class ExpensePool(list):
    """
        The pool of expenses, handles the sync status and other
        particular stuff
    """
    ids = []

    def load(self, elements):
        """
            Load expenses from a json string
        """
        for elem in json.loads(elements):
            # We store the ids to be able to handle unicity
            self.ids.append(elem['local_id'])
            self.append(elem)

    def merge(self, expense_dict):
        if 'local_id' in expense_dict:
            return self.update_expense(expense_dict)
        else:
            return self.add_expense(expense_dict)

    def add_expense(self, expense_dict):
        """
            add an expense to our pool
        """
        Logger.debug("Ndf : Storing an expense %s" % expense_dict)
        expense_dict['local_id'] = self.get_uniq_id()
        self.append(expense_dict)
        expense_dict['todo'] = 'add'
        return expense_dict

    def update_expense(self, expense_dict):
        """
            Update an expense
        """
        Logger.debug("Ndf : Updating an expense %s" % expense_dict)
        index, expense = self.get_expense_by_local_id(expense_dict['local_id'])
        expense.update(expense_dict)
        if 'id' in expense:
            expense['todo'] = 'update'
        expense['synced'] = False
        return expense

    def del_expense(self, expense_dict):
        """
            Ask for expense deletion
        """
        index, expense = self.get_expense_by_local_id(expense_dict['local_id'])
        expense['synced'] = False
        expense['todo'] = 'delete'
        return expense

    def remove(self, expense_dict):
        """
            Remove an expense from the pool (after deletion)
        """
        index, expense = self.get_expense_by_local_id(expense_dict['local_id'])
        return self.pop(index)

    def get_expense_by_local_id(self, local_id):
        """
            Return an expense given its local id
        """
        for index, elem in enumerate(self):
            if elem['local_id'] == local_id:
                return index, elem
        # Should not happen
        return None

    def tosync(self):
        """
            Return the list of elements to be synchronized
        """
        return [elem for elem in self if not elem.get('synced', False)]

    def get_uniq_id(self):
        """
            Return a unique id
        """
        temp = random.randint(0, 10000)
        while temp in self.ids:
            temp = random.randint(0, 10000)
        return temp

    def stored_version(self):
        """
            Return this object as a json string
        """
        return json.dumps(self)


class RestRequest(object):
    def __init__(self, request, resp):
        self.request = request
        self.resp = resp
        self.code = self.request.resp_status
        if hasattr(self.resp, 'get'):
            self.status = self.resp.get('status')
            self.result = self.resp.get('result', {})
            self.errors = self.resp.get('errors', {})
        else:
            self.status = None
            self.result = {}
            self.errors = {}

        self.success = self.status == 'success'


class NdfApp(App):
    """
        The main application object
        Handle the settings and the expense add/edit/delete
    """
    settings = ObjectProperty()
    pool = ObjectProperty()
    expenses = ObjectProperty()

    def build(self):
        """
            The build method (specific to kivy)
        """
        settings = self.load_settings()
        # need to load config *before* assigning to self.settings
        self.settings = settings

        self.manager = self.root.ids.screenmanager
        self.expenses = self.manager.get_screen('expenses')

        self.load_expenses()
        if not self.is_configured():
            self.manager.transition.direction = 'down'
            self.manager.current = 'settings'
        return self.root

    def is_configured(self):
        """
            Check if the application is fully configured
        """
        for key in ('server', 'login', 'password'):
            if not self.settings.get('settings', key):
                return False
        return True

    def load_settings(self):
        """
            Load the settings from the ini files
        """
        settings = SafeConfigParser()
        loaded_settings = settings.read(SETTINGS_FILES)
        Logger.debug("Ndf: loaded settings: %s", loaded_settings)
        return settings

    def load_expenses(self):
        """
            Build our expense pool and pass it to the expenselistscreen
        """
        self.pool = ExpensePool()
        self.pool.load(self.settings.get('main', 'expenses'))
        self.property('pool').dispatch(self)
        self.expenses.data = self.pool

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

    def check_configuration(self):
        """
            Entry point for app configuration
        """
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
        rest_req = RestRequest(request, resp)
        if rest_req.code == 301:
            self.check_auth_redirect(request, resp)
        elif rest_req.success:
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

    def fetch_options(self, silent=False):
        """
            Fetch options for expense configuration
        """
        path = "expenseoptions"
        conn = self.get_connection()
        success = partial(self.fetch_options_success, silent)
        error = partial(self.fetch_options_error, silent)
        conn.request(
            path,
            {},
            on_success=success,
            on_error=error)

    def fetch_options_success(self, silent, request, resp):
        """
            Fetch options success handler
        """
        rest_req = RestRequest(request, resp)
        Logger.info("Nd : Get back : %s" % resp)
        if rest_req.success:
            self.store_options(rest_req.result)
        else:
            self.fetch_options_error(silent, request, resp)
        if not silent:
            self.dialog(
                title=u"Configuration réussie",
                text=u"Votre application a bien été configurée")

    def fetch_options_error(self, silent, request, resp):
        """
            Error while fetching options
        """
        Logger.info("Nd : Get back : %s" % resp)
        if not silent:
            self.dialog(
                title=u"Erreur à la configuration",
                text=u"Une erreur inconnue a été rencontrée lors de la "
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

    def sync_datas(self):
        """
            Sync the pending expenses to the remote server
        """
        # Handle deletion
        #path = "expenses"
        conn = self.get_connection()

        Logger.info("Fetching server options")
        self.fetch_options(silent=True)
        Logger.info("Done fetching options")

        Logger.info("Sending expense updates")
        for expense in self.pool.tosync():
            self.sync_expense(expense, conn=conn)

    def sync_expense(self, expense, conn=None):
        """
            Sync the given expense
        """
        if conn is None:
            conn = self.get_connection()
        Logger.debug("Ndf : Syncing %s", expense)
        path, method = get_action_path_and_method(expense)
        success = partial(self.sync_success, expense)
        error = partial(self.sync_error, expense)
        conn.request(
            path,
            expense,
            on_success=success,
            on_error=error,
            method=method)
        Logger.debug("Done syncing %s", expense)

    def sync_success(self, expense, req, resp):
        """
            Successfull synchronisation
        """
        rest_req = RestRequest(req, resp)
        if rest_req.success:
            Logger.info("Ndf : Synchronisation was successfull")
            Logger.info("Ndf : %s" % resp)
            if expense['todo'] == 'delete':
                self.pool.remove(expense)
            else:
                expense.update(rest_req.result)
                expense['synced'] = True
            self.pool_updated()
            Logger.info("Ndf : %s" % self.pool)
        else:
            self.sync_error(expense, req, resp)

    def sync_error(self, expense, req, resp):
        """
            Error while synchronizing
        """
        Logger.error("Ndf : Synchronization error")
        Logger.error("Ndf : error code : %s" % req.resp_status)
        Logger.error("Ndf : %s" % resp)
        rest_req = RestRequest(req, resp)
        if rest_req.code == 404:
            # This expense is not know anymore
            if expense['todo'] == 'delete':
                self.pool.remove(expense)
                self.pool_updated()
            else:
                # This expense is not know on the server side, we pop its id to
                # be able to simply add it next time
                expense.pop('id')
                expense['todo'] = 'add'
                self.sync_expense(expense)
                return
        elif rest_req.status == 'error':
            #errors = rest_req.resp
            msg = u"Une erreur est survenue lors de la synchronisation de " \
                  u"vos données"
            for key, value in rest_req.errors.items():
                msg += u'\n'
                msg += u"{key} : {value}".format(key=key, value=value)
        else:
            msg = u"Une erreur inconnue est survenue lors de la " \
                  u"synchronisation de vos données : \n %s" % resp

        self.dialog("Erreur de synchronisation", msg)

    def pool_updated(self):
        """
            Called when the expense pool has been updated
        """
        Logger.debug("Ndf Pool : pool updated")
        self.settings.set('main', 'expenses', self.pool.stored_version())
        self.property('pool').dispatch(self)

    def dialog(self, title, text):
        """
            Fires a simple dialog popup
        """
        content = BoxLayout(orientation='vertical')
        content.add_widget(Factory.NormalLabel(text=text))
        btnclose = Factory.NormalButton(text="Fermer",
                                        size_hint_y=None,
                                        height='40sp')
        content.add_widget(btnclose)
        popup_ = Factory.NormalPopup(title=title, content=content)
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

    def on_pool(self, *args):
        Logger.debug("Ndf Pool : The pool update event has been received")
        if self.expenses is not None:
            Logger.debug("%s" % self.pool)
            self.expenses.data = []
            self.expenses.data = self.pool

    def store_expense(self, screen_name, expense):
        Logger.debug("Storing an expense : %s" % expense)
        screen = self.manager.get_screen(screen_name)

        # TODO: add validation
        if expense:
            self.pool.merge(expense)
            self.pool_updated()
            self.settings.set('main', 'expenses', self.pool.stored_version())
            screen.expense = {}

    def edit_expense(self, index):
        expense = self.expenses.data[index]
        name = "expense{0}".format(index)
        if self.manager.has_screen(name):
            self.manager.remove_widget(self.manager.get_screen(name))

        if 'start' in expense:
            form = KmEditFormScreen
        else:
            form = CommonEditFormScreen

        view = form(
            name=name,
            expense=expense)
        self.manager.add_widget(view)
        self.manager.transition.direction = 'left'
        self.manager.current = view.name

    def delete_expense(self, expense):
        self.pool.del_expense(expense)
        self.pool_updated()
        self.settings.set('main', 'expenses', self.pool.stored_version())

    def select_expenses(self, expense):
        """returns a list of expenses with the same caracteristics as
        the passed one
        """
        if not self.expenses:
            return

        keys = (
            'category',
            'end',
            'ht',
            'km',
            'start',
            'tva',
            'type_id',
            'type',
            'description',
            'transport',
            )

        for e in filter_expenses(expense, self.expenses.data, keys):
            yield e

    def open_mail_link(self, mail):
        if platform == 'linux':
            process = subprocess.Popen(["xdg-email", mail])
            Logger.debug("Spawned external mailer process: PID %i", process.pid)
            return

        if platform == 'android':
            intent = Intent(Intent.ACTION_SENDTO,
                            Uri.parse('mailto:%s' % mail))
            PythonActivity.mActivity.startActivity(
                Intent.createChoser(intent, "Envoyer un mail à %s" % mail))

    def open_link(self, url):
        if platform == 'linux':
            process = subprocess.Popen(["xdg-open", url])
            Logger.debug(
                "Spawned external process: Url: %s - PID %i", 
                url, process.pid)
            return

        if platform == 'android':
            intent = Intent(Intent.ACTION_VIEW, Uri.parsr(url))
            PythonActivity.mActivity.startActivity(
                Intent.createChoser(intent, "Ouverture de l'url %s" % url))




class ExpenseFormScreen(Screen):
    expense = DictProperty({})

    def set_value(self, key, value, *args):
        Logger.debug(u"Ndf : Setting a value for {0} : {1}".format(key, value))
        Logger.debug("Ndf : Alternative options : {0}".format(args))
        if hasattr(self, 'on_%s' % key):
            value = getattr(self, 'on_%s' % key)(value, *args)
        self.expense[key] = value

    def on_type(self, value, options):
        """
            Set the type of the expense
        """
        for option in options:
            Logger.debug("Ndf : option : %s" % option)
            if option['label'] == value:
                self.set_value('type_id', option['value'])
                break
        return value

    def on_date(self, value):
        """
            Set the date
        """
        Logger.debug("Ndf : Altering the date value")
        if len(value) != 10:
            Logger.debug("Ndf : date format is invalid, expecting ddmmyyyy")
            value = ""
        else:
            try:
                date = read_locale_date(value)
            except:
                date = datetime.date.today()
            value = date.isoformat()
        return value

    def get_date(self):
        """
            return the current date (today as default)
        """
        if self.expense.get('date'):
            date = dateutil.parser.parse(self.expense.get('date'))
        else:
            date = datetime.date.today()
            self.set_value('date', date.isoformat())
        return write_locale_date(date)


class KmAddFormScreen(ExpenseFormScreen):
    pass


class KmEditFormScreen(ExpenseFormScreen):
    """
        Form used to edit km expenses
    """
    pass


class CommonAddFormScreen(ExpenseFormScreen):
    pass


class CommonEditFormScreen(ExpenseFormScreen):
    pass


class ExpenseListItem(BoxLayout):
    index = NumericProperty()
    description = StringProperty()
    todo = StringProperty(allownone=True)
    synced = BooleanProperty()
    kmtype = BooleanProperty()
    date = StringProperty()


class ExpenseListScreen(Screen):
    data = ListProperty()

    def args_converter(self, row_index, item):
        date = write_locale_date(dateutil.parser.parse(item.get('date')))
        return {'description': item.get("description", ""),
                "synced": item.get('synced', False),
                "todo": item.get('todo', ''),
                'km_expense': 'km' in item,
                'date': date,
                'index': row_index}


if __name__ == '__main__':
    NdfApp().run()
