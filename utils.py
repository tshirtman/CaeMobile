# -*- coding: utf-8 -*-
# * File Name : utils.py
#
# * Copyright (C) 2012 Gaston TJEBBES <g.t@majerti.fr>
# * Company : Majerti ( http://www.majerti.fr )
#
#   This software is distributed under GPLV3
#   License: http://www.gnu.org/licenses/gpl-3.0.txt
#
# * Creation Date : 31-07-2013
# * Last Modified :
#
# * Project :
#
"""
    Some usefull funcs
"""
import urlparse
import datetime

def read_locale_date(value):
    """
        return a date object based on a string expected to be in the local
        format : ddmmYYYY
    """
    day, month, year = map(int, value.split('-'))
    return datetime.date(year, month, day)

def write_locale_date(date_obj):
    """
        Return the date object as a string in local format
    """
    return date_obj.strftime('%d-%m-%Y')


def get_base_url(url):
    """
        Return scheme + location
    """
    result = urlparse.urlsplit(url)
    scheme = result.scheme or 'http'
    return "{0}://{1}/".format(scheme, result.netloc)


def get_action_path_and_method(expense_dict):
    """
        Return the path and the method to be used to synchronize this expense
    """
    if expense_dict['todo'] == 'add':
        method = 'POST'
        path = 'expenses'
    elif expense_dict['todo'] == 'update':
        method = 'PUT'
        path = 'expenses/{id}'.format(id=expense_dict['id'])
    elif expense_dict['todo'] == 'delete':
        method = 'DELETE'
        exp_id = expense_dict.get('id', '00')
        path = 'expenses/{id}'.format(id=exp_id)
    return path, method


def filter_expenses(expense, expenses, keys):
    for e in expenses:
        f = lambda x: cmp_attribute(x, expense, e)
        if all(map(f, keys)):
            yield {k: e.get(k) for k in keys}


def cmp_attribute(attr, e1, e2):
    if not attr in e1:
        return True

    return e1[attr] == e2.get(attr)
