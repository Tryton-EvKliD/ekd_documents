# -*- coding: utf-8 -*-
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from __future__ import with_statement
from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard
from trytond.report import Report
from trytond.pyson import Equal, Eval, Get, PYSONEncoder
from trytond.transaction import Transaction
from decimal import Decimal
import datetime

class StaffList(ModelSQL, ModelView):
    'Staff list'
    _name = 'ekd.company.staff_list'

    order = fields.Many2One('ekd.document.head.order', 'Order')

StaffList()

class PersonalAccount(ModelSQL, ModelView):
    'Personal account'
    _name = 'ekd.company.employee.account'

    order = fields.Many2One('ekd.document.head.order', 'Order')

PersonalAccount()
