# -*- coding: utf-8 -*-
"Document"
from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard
from trytond.transaction import Transaction
from trytond.tools import safe_eval
from decimal import Decimal, ROUND_HALF_EVEN
from trytond.pyson import In, Eval, Not, In, Equal, If, Get, Bool
import time
import datetime
import random
import copy
from ekd_state_document import _STATES_FULL

class DocumentTemplate(ModelSQL, ModelView):
    "Document Template"
    _name='ekd.document.template'
    _description=__doc__
    _rec_name = "shortcut"
    _order_name = "name"

    model = fields.Many2One('ir.model', 'Model', domain=[('model','like','ekd.document.head%')])
    model_str = fields.Char('Model Name', size=128)
    name = fields.Char('Name', size=128)
    shortcut = fields.Char('ShortCut', size=32)
    direction = fields.Selection([
                    ('input','Input'),
                    ('internal','Internal'),
                    ('output','Output')
                    ],'Direction document')
    code_call = fields.Char('Code Call', size=20, help="income, expense, ...")
    sort = fields.Char('Sort', size=4)
    type_account = fields.Selection('type_account_get', 'Type account')
    sequence = fields.Property(fields.Many2One('ir.sequence', 'Sequence'))
    view_form  = fields.Many2One('ir.action.act_window', 'Form View',
                    domain=[('res_model','like','ekd.document.%')])
    report = fields.Many2One('ir.action.report', 'Form for print')
    date_start = fields.Date('Date Start')
    date_end = fields.Date('Date end')
    active = fields.Boolean('Active')
#    document = fields.One2Many('ekd.document','template','Real Documents')

    def default_company(self):
        return Transaction().context.get('company') or False

    def default_active(self):
        return True

    def type_account_get(self):
        dictions_obj = self.pool.get('ir.dictions')
        res = []
        diction_ids = dictions_obj.search([
                ('model', '=', 'ekd.document.template'),
                ('pole', '=', 'type_account'),
                ])
        for diction in dictions_obj.browse(diction_ids):
            res.append([diction.key, diction.value])
        return res


DocumentTemplate()

class Document(ModelSQL, ModelView):
    "Documents"
    _name='ekd.document'
    _order_name = 'date_document'
    _order=['date_document', 'date_account']
    _description=__doc__

    company = fields.Many2One('company.company', 'Company', readonly=True)
    model = fields.Many2One('ir.model', 'Model', domain=[('model','like','ekd.document%')])
    model_str = fields.Char('Model Name', size=128)
    direction = fields.Selection([
                    ('input','Input'),
                    ('move','Move'),
                    ('internal','Internal'),
                    ('output','Output')
                    ],'Direction document')
    name = fields.Char('Description')
    template = fields.Many2One('ekd.document.template', 'Document Name', help="Template documents", order_field="%(table)s.template %(order)s")
    note = fields.Text('Note document')
    number_our = fields.Char('Number Outgoing', size=32, readonly=True, 
                            states={
                                'invisible': Not(Bool(Eval('number_our')))
                                })
    number_in = fields.Char('Number of incoming', size=32)
    date_document = fields.Date('Date Create')
    date_account = fields.Date('Date Account')
    employee = fields.Many2One('company.employee', 'Employee')
    from_party = fields.Many2One('party.party', 'From partner')
    to_party = fields.Many2One('party.party', 'To partner')
    amount = fields.Numeric('Amount Document', digits=(16, Eval("currency_digits",2)))
    amount_payment = fields.Function(fields.Numeric('Amount Payment', digits=(16, Eval("currency_digits", 2))), 'get_payment_field')
    amount_paid = fields.Function(fields.Numeric('Amount Paid', digits=(16, Eval("currency_digits", 2))), 'get_paid_field')
    currency = fields.Many2One('currency.currency', 'Currency')
    currency_digits = fields.Function(fields.Integer('Currency Digits' , on_change_with=['currency']), 'get_currency_digits')
    document_base = fields.Reference('Document Base', selection='documents_base_get',
                on_change=['document_base', 'lines'])
    lines = fields.One2Many('ekd.document.line.product', 'invoice', 'Lines')
    childs = fields.One2Many('ekd.document','parent', 'Child documents', readonly=True)
    parent = fields.Many2One('ekd.document', 'Parent document')
    state = fields.Selection(_STATES_FULL, 'State', readonly=True)
    stage = fields.Many2One('ekd.document.template.stage', 'Stage', readonly=True)
    journal_work = fields.One2Many('ekd.document.journal_work','document','Journal Change Stages', readonly=True)
    post_date = fields.Date('Date Post')
    active = fields.Boolean('Active', required=True)
    id_1c = fields.Char("ID import from 1C", size=None, select=1)
    deleting = fields.Boolean('Flag Deleting')

    def __init__(self): 
        super(Document, self).__init__()

        self._order.insert(0, ('company','ASC'))
        self._order.insert(0, ('date_document', 'ASC'))
        self._order.insert(0, ('template', 'ASC'))
        self._order.insert(0, ('date_account', 'ASC'))
        self._order.insert(0, ('number_our', 'ASC'))

    def default_state(self):
        return 'draft'

    def default_date_document(self):
        context = Transaction().context
        if context.get('date_document'):
            return context.get('date_document')
        elif context.get('current_date'):
            return context.get('current_date')
        return datetime.datetime.now()

    def default_date_account(self ):
        context = Transaction().context
        if context.get('date_account'):
            return context.get('date_account')
        elif context.get('current_date'):
            return context.get('current_date')
        return datetime.datetime.now()

    def default_from_party(self):
        return Transaction().context.get('from_party')

    def default_to_party(self):
        return Transaction().context.get('to_party')

    def default_company(self ):
        return Transaction().context.get('company')

    def default_child(self):
        return Transaction().context.get('child')

    def default_amount(self):
        return Transaction().context.get('amount')

    def default_name(self):
        return Transaction().context.get('name')

    def default_note(self):
        return Transaction().context.get('note')

    def default_currency(self):
        company_obj = self.pool.get('company.company')
        currency_obj = self.pool.get('currency.currency')
        context = Transaction().context
        if context.get('company'):
            company = company_obj.browse(context['company'])
            return company.currency.id
        return False

    def default_currency_digits(self):
        company_obj = self.pool.get('company.company')
        context = Transaction().context
        if context.get('company'):
            company = company_obj.browse(context['company'])
            return company.currency.digits
        return 2

    def default_active(self):
        return True

    def documents_base_dict_get(self, model=False):
        if not model:
            model = self._name
        dictions_obj = self.pool.get('ir.dictions')
        res = []
        diction_ids = dictions_obj.search( [
                                ('model', 'like', 'ekd.document.head%'),
                                ('pole', '=', 'document_base'),
                                ])
        if diction_ids:
            for diction in dictions_obj.browse( diction_ids):
                res.append([diction.key, diction.value])
        return res

    def documents_base_get(self):
        return self.documents_base_dict_get(self._name)

    def get_rec_name(self, ids, name):
        res={}

        for document in self.browse(ids):
            if document.template:
                if document.template.shortcut:
                        TemplateName = document.template.shortcut
                else:
                        TemplateName = document.template.name

            if document.number_our:
                DocumentNumber = document.number_our
            elif document.number_in:
                DocumentNumber = document.number_in
            else:
                DocumentNumber = u'без номера'

            if document.date_document:
                DocumentDate = document.date_document.strftime('%d.%m.%Y')
            else:
                DocumentDate = u'без даты'

            if document.template:
                 res[document.id] = TemplateName+ u' № '+DocumentNumber+u' от '+DocumentDate
            else:
                 res[document.id] = u'Без имени № '+ DocumentNumber+u' от '+DocumentDate

        return res

    def get_payment_field(self, ids, name):
        res = {}
        cursor = Transaction().cursor
        for id in ids:
            res.setdefault(id, Decimal('0.0'))
        cursor.execute("SELECT doc_base, SUM(amount_payment) "\
                        "FROM ekd_document_line_payment "\
                        "WHERE doc_base in ("+','.join(map(str,ids))+") and state in ('wait0', 'wait1', 'payment') "\
                        "GROUP BY doc_base")
        for id, sum in cursor.fetchall():
            # SQLite uses float for SUM
            if not isinstance(sum, Decimal):
                sum = Decimal(str(sum))
            res[id] = sum
        return res

    def get_paid_field(self, ids, name):
        res = {}
        cursor = Transaction().cursor
        for id in ids:
            res.setdefault(id, Decimal('0.0'))
        cursor.execute("SELECT doc_base, SUM(amount_payment) "\
                        "FROM ekd_document_line_payment "\
                        "WHERE doc_base in ("+','.join(map(str,ids))+") and state='done' "\
                        "GROUP BY doc_base")
        for id, sum in cursor.fetchall():
            # SQLite uses float for SUM
            if not isinstance(sum, Decimal):
                sum = Decimal(str(sum))
            res[id] = sum
        return res

    def get_currency_digits(self, ids, name):
        assert name in ('currency_digits'), 'Invalid name %s' % (name)
        res={}.fromkeys(ids, 2)
        for document in self.browse(ids):
            if document.currency:
                res[document.id] = document.currency.digits
        return res

    def on_change_document_base(self, values):
        return values

    def button_draft(self, ids):
        for document in self.browse(ids):
            if document.template.model:
                self.pool.get(document.template.model).button_draft(ids)

    def button_cancel(self, ids):
        for document in self.browse(ids):
            if document.template.model:
                self.pool.get(document.template.model).button_cancel(ids)

    def button_restore(self, ids):
        for document in self.browse(ids):
            if document.template.model:
                self.pool.get(document.template.model).button_restore(ids)

    def button_issued(self, ids):
        for document in self.browse(idst):
            if document.template.model:
                self.pool.get(document.template.model).button_issued(ids)

    def button_on_payment(self, ids):
        for document in self.browse(idst):
            if document.template.model:
                self.pool.get(document.template.model).button_payment(ids)

    def button_pay(self, ids):
        for document in self.browse(idst):
            if document.template.model:
                self.pool.get(document.template.model).button_pay(ids)

    def button_confirmed(self, ids):
        for document in self.browse(idst):
            if document.template.model:
                self.pool.get(document.template.model).button_confirmed(ids)

Document()

class DocumentJournalWork(ModelSQL, ModelView):
    "Documents Journal Change Stage"
    _name='ekd.document.journal_work'
    _description=__doc__

    document = fields.Many2One('ekd.document', 'Documents')
    state_from = fields.Selection(_STATES_FULL, 'State From', readonly=True)
    state_to = fields.Selection(_STATES_FULL, 'State To', readonly=True)
    stage_from =  fields.Many2One('ekd.document.template.stage', 'Stage From')
    stage_to = fields.Many2One('ekd.document.template.stage', 'Stage To')
    employee = fields.Many2One('company.employee', 'Employee')
    date_change = fields.DateTime('Date Change')
    deleting = fields.Boolean('Flag Deleting')

DocumentJournalWork()

class DocumentTemplateAdd(ModelSQL, ModelView):
    "Document Template"
    _name='ekd.document.template'

    document = fields.One2Many('ekd.document','template','Real Documents')

DocumentTemplateAdd()

class DocumentOpenWizard(Wizard):
    'Open Document Wizard'
    _name = 'ekd.document.wizard.open'
    states = {
        'init': {
            'result': {
                'type': 'action',
                'action': '_add',
                'state': 'end'
                        },
                },
            }

    def _add(self, data):
        document_obj = self.pool.get('ekd.document')
        model_obj = self.pool.get('ir.model')
        model_data_obj = self.pool.get('ir.model.data')
        act_window_obj = self.pool.get('ir.action.act_window')

        document = document_obj.browse(data.get('id'))
        if document.template.view_form:
            res = act_window_obj.read(document.template.view_form.id)
            res['res_id'] = data.get('id')
            res['views'].reverse()
            return res
        else:
            self.raise_user_error('Form View not find!\nPlease setup template document:\n\n %s'%(document.template.name))

DocumentOpenWizard()

