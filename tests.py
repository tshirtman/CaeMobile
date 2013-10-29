# -*- coding: utf-8 -*-
# * File Name : tests.py
#
# * Copyright (C) 2012 Gaston TJEBBES <g.t@majerti.fr>
# * Company : Majerti ( http://www.majerti.fr )
#
#   This software is distributed under GPLV3
#   License: http://www.gnu.org/licenses/gpl-3.0.txt
#
# * Creation Date : 31-07-2013
# * Last Modified : 29-10-2013
#
# * Project :
#
import datetime
from utils import (
    read_locale_date,
    write_locale_date,
    get_base_url,
    get_action_path_and_method,
    filter_expenses,
    cmp_attribute,
    )


def test_read_locale_date():
    assert read_locale_date('25-07-2013') == datetime.date(2013, 07, 25)


def test_write_locale_date():
    assert write_locale_date(datetime.date(2013, 07, 25)) == '25-07-2013'


def test_get_base_url():
    assert get_base_url('http://test.com/testpath') == 'http://test.com/'
    assert get_base_url('http://test.com/?testpath') == 'http://test.com/'


def test_get_action_path_and_method():
    edict = {'id': 1}
    for action, method, path in (
            ('add', 'POST', 'expenses'),
            ('update', 'PUT', 'expenses/1'),
            ('delete', 'DELETE', 'expenses/1'),):
        edict['todo'] = action
        assert get_action_path_and_method(edict) == (path, method)


def test_cmp_attribute():
    assert cmp_attribute('test', {}, {})
    assert cmp_attribute('test', {'test': 0}, {'test': 0})
    assert cmp_attribute('test', {}, {'test': 0})
    assert not cmp_attribute('test', {'test': 0}, {'test': 1})
    assert not cmp_attribute('test', {'test': 0}, {})
    assert not cmp_attribute('test', {'test': 'ham'}, {'test': 'spam'})


def test_filter_expenses():
    expenses = [
        {
            'category': u'2', 'todo': 'add',
            'description': 'repas rdv', 'type_id': u'5', 'tva': '2',
            'ht': '10', 'local_id': 2435, 'date': '2013-10-29',
            'type': u'Restauration'
        },
        {
            'category': u'3', 'todo': 'add',
            'description': 'repas rdv', 'type_id': u'6', 'tva': '2',
            'ht': '10', 'local_id': 2435, 'date': '2013-10-29',
            'type': u'Restauration'
        },
        {
            'category': u'2', 'todo': 'add',
            'description': 'repas rdv', 'type_id': u'6', 'tva': '2',
            'ht': '10', 'local_id': 2435, 'date': '2013-10-29',
            'type': u'Restauration'
        },
    ]

    assert list(filter_expenses({'category': '2'}, expenses, ('category', )))
    assert list(filter_expenses({'category': '4'}, expenses, ('type_id', )))
    assert list(filter_expenses({'ht': '10'}, expenses, ('category', )))
    assert list(filter_expenses({'ht': '10', 'category': '3'},
                                expenses, ('category', 'type')))
    assert len(list(filter_expenses({'ht': '10', 'category': '2'},
                                    expenses, ('category', 'type')))) == 2

    assert len(list(filter_expenses({'type_id': '6', 'category': '2'},
                                    expenses, ('category', 'type_id')))) == 1

    assert not list(filter_expenses(
        {'category': '4'}, expenses, ('category', )))
