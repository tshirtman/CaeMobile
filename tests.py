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
# * Last Modified :
#
# * Project :
#
import datetime
from utils import (
        read_locale_date,
        write_locale_date,
        get_base_url,
        get_action_path_and_method,
        )

def test_read_locale_date():
    assert read_locale_date('25-07-2013') == datetime.date(2013, 07, 25)

def test_write_locale_date():
    assert write_locale_date(datetime.date(2013, 07, 25)) == '25-07-2013'

def test_get_base_url():
    assert get_base_url('http://test.com/testpath') == 'http://test.com/'
    assert get_base_url('http://test.com/?testpath') == 'http://test.com/'

def test_get_action_path_and_method():
    edict = {'id':1}
    for action, method, path in (
            ('add', 'POST', 'expenses'),
            ('update', 'PUT', 'expenses/1'),
            ('delete', 'DELETE', 'expenses/1'),):
        edict['todo'] = action
        assert get_action_path_and_method(edict) == (path, method)


