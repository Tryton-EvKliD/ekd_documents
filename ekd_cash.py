# -*- coding: utf-8 -*-
#NOTE: Кассовые документы
#TODO: Что делать?
"Document Cash"
from trytond.model import ModelStorage, ModelView, ModelSQL, fields
from trytond.report import Report
from trytond.transaction import Transaction
from trytond.tools import safe_eval
from decimal import Decimal, ROUND_HALF_EVEN
from trytond.pyson import In, Eval, Not, In, Equal, If, Get, Bool
import time
import datetime
import logging
from pytils import numeral
from ekd_state_document import _STATE_CASH

_STATES = {
    'readonly': Equal(Eval('state_doc'),'posted'),
    }
_DEPENDS = ['state_doc']

class DocumentCash(ModelSQL, ModelView):
    "Documents of cash"
    _name='ekd.document.head.cash'
    _description=__doc__
    _inherits = {'ekd.document': 'document'}

    document = fields.Many2One('ekd.document', 'Document', required=True, ondelete='CASCADE')
    template_cash = fields.Function(fields.Many2One('ekd.document.template',
            string='Document Name', states=_STATES, depends=_DEPENDS,
            help="Template documents", domain=[
                ('type_account','=','cash_documents'),
                ('code_call','=',Eval('type_transaction'))
                ],
            on_change=['type_transaction', 'template_cash', 'document_base_ref']),
            'get_fields', setter='set_fields', searcher='template_search')
    note_cash = fields.Function(fields.Text('Note', states=_STATES, depends=_DEPENDS), 
            'get_fields', setter='set_fields', searcher='template_search')
    type_transaction = fields.Selection((
                        ('income_cash','Income'),
                        ('expense_cash','Expense'),
                        ('return_cash','Return'),
                        ), 'Type Transaction')
    cash_account_txt = fields.Char('Cash Account', size=20, states=_STATES, depends=_DEPENDS)
    #document_base = fields.Many2One('ekd.document', 'Document Base')
    document_base_ref = fields.Reference('Document Base', selection='documents_get',
                states=_STATES, depends=_DEPENDS,
                domain=[('state','=','payment')],
                context={'date_account': Eval('date_account'), 'state_doc':'payment'},
                on_change=['type_transaction', 'document_base_ref'])
    corr_account_txt = fields.Char('Corr. Account',  size=20, states=_STATES, depends=_DEPENDS)
    from_to_party = fields.Function(fields.Many2One('party.party', 'From or To Party', 
                states=_STATES, depends=_DEPENDS),
                'get_fields', setter='set_fields', searcher='template_search')
    income = fields.Function(fields.Numeric('Income', digits=(16, Eval('currency_digits', 2))), 'get_fields')
    expense = fields.Function(fields.Numeric('expense', digits=(16, Eval('currency_digits', 2))), 'get_fields')
    state_doc = fields.Function(fields.Selection(_STATE_CASH, required=True, readonly=True, string='State'),
            'get_fields', setter='set_fields')

    lines_payment = fields.One2Many('ekd.document.line.payment', 'doc_payment', 'Line Spec Amounts')
    deleting = fields.Boolean('Flag deleting', readonly=True)

    def __init__(self):
        super(DocumentCash, self).__init__()
        self._rpc.update({
            'button_post': True,
            'button_draft': True,
            'button_restore': True,
            'button_add_number': True,
            })

        self._order.insert(0, ('date_account', 'ASC'))
        self._order.insert(1, ('template', 'ASC'))
        self._order.insert(2, ('number_our', 'ASC'))

    def default_state_doc(self):
        return Transaction().context.get('state_doc') or 'draft'

    def default_document_base(self):
        return Transaction().context.get('document_base')

    def default_document_base_ref(self):
        return Transaction().context.get('document_base_ref')

    def default_cash_account(self):
        return Transaction().context.get('cash_account')

    def default_corr_account(self):
        return Transaction().context.get('corr_account')

    def default_from_to_party(self):
        return Transaction().context.get('from_to_party')

    def default_lines_payment(self):
        return Transaction().context.get('lines_payment')

    def default_get(self, fields, with_rec_name=True):
        values = super(DocumentCash, self).default_get(fields, with_rec_name=with_rec_name)
        #raise Exception(str(values), str(fields))
        #context = Transaction().context
        #if fields:
        #    pass
        return values

    def default_amount(self):
        return Transaction().context.get('amount') or Decimal('0.0')

    def default_type_transaction(self):
        return Transaction().context.get('type_transaction') or 'expense'

    def default_currency_digits(self):
        return 2

    def default_second_currency_digits(self):
        return 2

    def default_company(self):
        return Transaction().context.get('company')

    def get_fields(self, ids, names):
        if not ids:
            return {}
        res={}
        for line in self.browse(ids):
            for name in names:
                res.setdefault(name, {})
                res[name].setdefault(line.id, Decimal('0.0'))
                if name == 'income' and line.type_transaction in ('income_cash', 'return_cash'):
                    res[name][line.id] = line.amount
                elif name=='expense' and line.type_transaction == 'expense_cash':
                    res[name][line.id] = line.amount
                elif name == 'from_to_party':
                    if line.type_transaction == 'income_cash':
                        res[name][line.id] = line.from_party.id
                    else:
                        res[name][line.id] = line.to_party.id
                elif name == 'state_doc':
                        res[name][line.id] = line.state
                elif name == 'template_cash':
                        res[name][line.id] = line.template.id
                elif name == 'note_cash':
                        res[name][line.id] = line.note
        return res

    def set_fields(self, ids, name, value):
        if isinstance(ids, list):
            ids = ids[0]
        if not value:
            return
        document = self.browse(ids)
        if name == 'from_to_party':
            if document.type_transaction == 'income_cash':
                self.write(ids, {'from_party':value, })
            else:
                self.write(ids, {'to_party':value, })
        elif name == 'state_doc':
            self.write(ids, {'state':value, })
        elif name == 'template_cash':
            self.write(ids, { 'template': value, })
        elif name == 'note_cash':
            self.write(ids, { 'note': value, })

    def get_template_select(self):
        template_obj = self.pool.get('ekd.document.template')
        template_ids = template_obj.search(['type_account','=','cash_documents'])
        res=[]
        for template in template_obj.browse(template_ids):
            res.append([template.id,template.name])
        return res

    def template_search(self, name, domain=[]):
        if name == 'template_cash':
            for table, exp, value in domain:
                return  [('template', 'ilike', value)]

        if name == 'from_to_party':
            document_obj = self.pool.get('ekd.document')
            table, exp, value = domain[0]
            find_ids = document_obj.search(['OR', [('from_party', 'ilike', value)], [('to_party', 'ilike', value)]])
            return [('document', 'in', find_ids)]

    def get_rec_name(self, ids, name):
        if not ids:
            return {}
        return self.pool.get('ekd.document').get_rec_name(ids, name)

    def documents_get(self):
        dictions_obj = self.pool.get('ir.dictions')
        res = []
        diction_ids = dictions_obj.search([
            ('model', '=', 'ekd.document.head.cash'),
            ('pole', '=', 'document_base_ref'),
            ])
        for diction in dictions_obj.browse(diction_ids):
            res.append([diction.key, diction.value])
        return res

    def get_currency_digits(self, ids, name):
        assert name in ('currency_digits'), 'Invalid name %s' % (name)
        res={}.fromkeys(ids, 2)
        #for document in self.browse(ids):
        #    if document.cash_account:
        #        res[document.id] = document.cash_account.currency_digits
        return res

    def on_change_document_base(self, values):
        if not values.get('document_base'):
            return {}
        res = {}
        model, model_ids = values.get('document_base').split(',')
        if model and model_ids != '0':
            model_obj = self.pool.get(str(model))
            model_id = model_obj.browse(int(model_ids))
            res['document_base'] = model_ids
            res['amount']=model_id.amount
            res['child']=model_ids
            if values.get('type_transaction') == 'income_cash' :
                res['from_to_party']=model_id.from_party.id
                res['parent']= model_id.id
                res['income']=model_id.amount
            else:
                res['from_to_party']=model_id.to_party.id
                res['parent']= model_id.id
                res['expense']=model_id.amount
        return res

    def on_change_document_base_ref(self, values):
        if not values.get('document_base_ref'):
            return {}
        res = {}
        model, model_ids = values.get('document_base_ref').split(',')
        if model and model_ids != '0':
            model_obj = self.pool.get(str(model))
            model_id = model_obj.browse(int(model_ids))
            res['document_base'] = model_ids
            res['amount']=model_id.amount
            res['child']=model_ids
            if values.get('type_transaction') == 'income_cash' :
                res['from_to_party']=model_id.from_party.id
                res['income']=model_id.amount
            else:
                res['from_to_party']=model_id.to_party.id
                res['expense']=model_id.amount
        return res

    def on_change_amount(self, values):
        if not values.get('amount'):
            return {}
        if values.get('type_transaction'):
            if values.get('type_transaction') == 'income_cash':
                return {'income': values.get('amount')}
            else:
                return {'expense': values.get('amount')}

    def on_change_template_cash(self, values):
        if not values.get('template_cash'):
            return {}
        res={}
        template_obj = self.pool.get('ekd.document.template')
        template_ids = template_obj.browse(int(values.get('template_cash')))
        values['type_transaction'] = template_ids.code_call
        if values.get('document_base_ref'):
            model, model_ids = values.get('document_base_ref').split(',')
            if model and model_ids != '0':
                model_obj = self.pool.get(str(model))
                model_id = model_obj.browse(int(model_ids))
                res['amount']= model_id.amount
                if template_ids.code_call == 'income' and model_id.from_party:
                    res['from_to_party']=model_id.from_party.id
                elif template_ids.code_call == 'expense' and model_id.to_party:
                    res['from_to_party']=model_id.to_party.id
        return res

    def view_header_get(self, value, view_type='form'):
        cash_account = u'1'
        balance_cash = u'2'
        date_balance = u'3'
        if Transaction().context.get('cash_balance'):
            balance_cash = Transaction().context.get('cash_balance')
        if Transaction().context.get('date_account'):
            date_balance = Transaction().context.get('date_account').strftime('%d.%m.%Y')
        if Transaction().context.get('cash_account'):
            cash_account = self.pool.get('ekd.account').browse(Transaction().context.get('cash_account')).rec_name
        return value + u': '+ cash_account + balance_cash + date_balance

    def button_post(self, ids):
        return self.post(ids)

    def button_draft(self, ids):
        return self.draft(ids)

    def button_restore(self, ids):
        return self.draft(ids)

    def button_add_number(self, ids):
        return self.new_number(ids)

    def new_number(self, ids):
        sequence_obj = self.pool.get('ir.sequence')
        for document in self.browse(ids):
            if document.template and document.template.sequence:
                sequence = sequence_obj.get_id(document.template.sequence.id)
            else:
                raise Exception('Error', 'Sequence for document not find!')
            self.write(document.id, {
                    'number_our': sequence,
                    })

    def post(self, ids):
        self.write(ids, {
            'state': 'posted',
            'post_date': date_obj.today(),
            })

    def draft(self, ids):
        self.write(ids, {
                'state': 'draft',
                })
        return

    def create(self, vals):
        later = {}
        vals = vals.copy()
        cr = Transaction().cursor
        for field in vals:
            if field in self._columns\
                    and hasattr(self._columns[field], 'set'):
                later[field] = vals[field]
        for field in later:
            del vals[field]
        vals['state'] = 'draft'
        if cr.nextid(self._table):
            cr.setnextid(self._table, cr.currid(self._table))
        new_id = super(DocumentCash, self).create(vals)
        cash = self.browse(new_id)
        new_id = cash.document.id
        cr.execute('UPDATE "' + self._table + '" SET id = %s '\
                        'WHERE id = %s', (cash.document.id, cash.id))
        ModelStorage.delete(self, cash.id)
        self.write(new_id, later)
        res = self.browse(new_id)
        return res.id

    # Схема удаления документа
    def delete(self, ids):
        cr = Transaction().cursor
        for document in self.browse(ids):
            if document.state == 'deleted' and document.deleting:
                cr.execute('DELETE FROM "ekd_document_head_cash" WHERE id=%s', (document.id,))
                cr.execute('DELETE FROM "ekd_document" WHERE id=%s', (document.id,))
                cr.execute('DELETE FROM "ekd_document_line_payment" WHERE doc_payment=%s', (document.id,))
            else:
                self.write(document.id, {'state': 'deleted', 'deleting':True})
        return True

DocumentCash()

class DocumentCashIncomePrint(Report):
    _name='ekd.document.print.cash.income'

    def parse(self, report, objects, datas, localcontext={}):
        user = self.pool.get('res.user').browse(Transaction().user)
        localcontext['company'] = user.company
        localcontext['numeral'] = numeral
        res = super(DocumentCashIncomePrint, self).parse(report, objects, datas, localcontext=localcontext)
        return res

DocumentCashIncomePrint()

class DocumentCashExpensePrint(Report):
    _name='ekd.document.print.cash.expense'

    def parse(self, report, objects, datas, localcontext={}):
        user = self.pool.get('res.user').browse(Transaction().user)
        localcontext['company'] = user.company
        localcontext['numeral'] = numeral
        res = super(DocumentCashExpensePrint, self).parse(report, objects, datas, localcontext=localcontext)
        return res

DocumentCashExpensePrint()
