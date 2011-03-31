# -*- coding: utf-8 -*-
"Document Advance for money"
from trytond.model import ModelView, ModelStorage,  ModelSQL, fields
from trytond.transaction import Transaction
from trytond.report import Report
from trytond.tools import safe_eval
from decimal import Decimal, ROUND_HALF_EVEN
from trytond.pyson import In, If, Get, Eval, Not, Equal, Bool, Or, And
import time
import datetime
import logging

_ADVANCE_STATES = {
    'readonly': Equal(Eval('state'), 'empty'),
    }

_ADVANCE_DEPENDS = ['state']

_LINE_STATES = {
    'readonly': Not(Equal(Eval('state'), 'draft')),
        }

_LINE_DEPENDS = [
    'state',
        ]

class DocumentAdvanceCash(ModelSQL, ModelView):
    "Documents of advance for money"
    _name='ekd.document.head.advancecash'
    _description=__doc__
    _inherits = {'ekd.document': 'document'}

    document = fields.Many2One('ekd.document', 'Document', required=True,
            ondelete='CASCADE')
    template_advance = fields.Function(fields.Many2One('ekd.document.template', 'Document', help="Template documents",
                            domain=[('type_account','=','advance_report')]), 'get_fields', setter='set_fields'
                            )

    date_report = fields.Function(fields.Date('Date of report'), 'get_fields', setter='set_fields')

    document_ref = fields.Reference('Base', selection='documents_get', select=1)
    document_name = fields.Function(fields.Char('Document Name'), 'get_doc_name')
    #employee = fields.Function(fields.Many2One('company.employee', string='Employee'), 'get_fields', setter='set_fields')
    amount_advance = fields.Function(fields.Numeric('Total Advanced'), 'get_amount_line')
    lines = fields.One2Many('ekd.document.line.advancecash', 'advance', 
            'Lines Advance', states=_ADVANCE_STATES, depends=_ADVANCE_DEPENDS)
    advance_lines = fields.Function(fields.One2Many('ekd.document.line.advancecash', None, 'Lines Advance', 
            add_remove=[
                ('advance.employee','=', Eval('employee')),
                ('state','in', ('partially', 'fully', 'done')),
                ], states=_ADVANCE_STATES, depends=_ADVANCE_DEPENDS),
            'get_lines', setter='set_lines')

    state_doc = fields.Function(fields.Selection([
            ('empty', 'Empty'),
            ('draft', 'Draft'),
            ('request', 'Request'),
            ('confirmed', 'Confirmed'),
            ('canceled', 'Canceled'),
            ('posted', 'Posted'),
            ('deleted', 'Deleted'),
            ], required=True, readonly=True, string='State'), 'get_fields', setter='set_fields')

    def __init__(self):
        super(DocumentAdvanceCash, self).__init__()
        self._rpc.update({
           'button_draft': True,
           'button_request': True,
           'button_cancel': True,
           'button_confirm': True,
           'button_post': True,
           'button_restore': True,
           })

    def default_currency(self):
        company_obj = self.pool.get('company.company')
        currency_obj = self.pool.get('currency.currency')
        context =Transaction().context
        if context.get('company'):
            company = company_obj.browse(context['company'])
            return company.currency.id
        return False

    def default_employee(self):
        return Transaction().context.get('employee', False)

    def default_currency_digits(self):
        company_obj = self.pool.get('company.company')
        context = Transaction().context
        if context.get('company'):
            company = company_obj.browse(context['company'])
            return company.currency.digits
        return 2

    def default_state_doc(self):
        return 'empty'

    def default_state(self):
        return 'empty'

    def get_rec_name(self, ids, name):
        if not ids:
            return {}
        return self.pool.get('ekd.document').get_rec_name(ids, name)

    def get_lines(self, ids, name):
        res = {}
        for advance in self.browse(ids):
                res[advance.id] = None
                for line in advance.lines:
                    if res[advance.id] == None:
                        res[advance.id] = []
                    res[advance.id].append(line.id)
        return res

    def set_lines(self, line_id, name, values):
        if not values:
            return
        lines_obj = self.pool.get('ekd.document.line.advancecash')
        lines_amount_obj = self.pool.get('ekd.document.line.advancecash.amounts')
        #raise Exception('SET-FIELDS', str(value[1]), str(value[2]))
        for value in values:
            if value[0] == 'create':
                value[1]['advance'] = line_id[0]
                #raise Exception(value[0], str(value[1]))
                lines_obj.create(value[1])
            elif value[0] == 'write':
                value[2]['advance'] = line_id
                lines_obj.write(value[1], value[2])
            elif value[0] == 'delete':
                lines_obj.write(value[1], {'advance': None})
#            raise Exception('SET-FIELDS', str(value))

    def get_template_select(self):
        template_obj = self.pool.get('ekd.document.template')
        template_ids = template_obj.search(['type_account','=','advance_report'])
        res=[]
        for template in template_obj.browse(template_ids):
            res.append([template.id,template.name])
        return res

    def get_currency_digits(self, ids, name):
        res = {}
        for line in self.browse(ids):
            res[line.id] = line.currency and line.currency.digits or 2
        return res

    def get_amount_line(self, ids, name):
        res={}.fromkeys(ids, Decimal('0.0'))
        amount = Decimal('0.0')
        amount_received = Decimal('0.0')
        for advance in self.browse(ids):
            for line in advance.lines:
                 amount += abs(line.amount_advance)
            res[advance.id] = amount
            amount = Decimal('0.0')
        return res

    def documents_get(self):
        dictions_obj = self.pool.get('ir.dictions')
        res = []
        diction_ids = dictions_obj.search([
                ('model', '=', 'ekd.document.advancecash'),
                ('pole', '=', 'document_ref'),
                ])
        for diction in dictions_obj.browse(diction_ids):
            res.append([diction.key, diction.value])
        return res

    def get_fields(self, ids, names):
        res = {}
        for advance in self.browse(ids):
            for name in names:
                res.setdefault(name, {})
                res[name].setdefault(advance.id, False)
                if name == 'manager':
                    res[name][advance.id] = advance.from_party.id
                elif name == 'employee':
                    res[name][advance.id] = advance.employee.id
                elif name == 'date_report':
                    res[name][advance.id] = advance.date_account
                elif name == 'state_doc':
                    res[name][advance.id] = advance.state
                elif name == 'template_advance':
                    res[name][advance.id] = advance.template.id

        return res

    def set_fields(self, id, name, value):
        if not value:
            return
        if name == 'manager':
            self.write(id, {'from_party':value, })
        elif name == 'employee':
            self.write(id, {'employee':value, })
        elif name == 'date_report':
            self.write(id, {'date_account':value, })
        elif name == 'state_doc':
            self.write(id, {'state':value, })
        elif name == 'template_advance':
            self.write(id, {'template':value, })

    def button_draft(self, ids):
        return self.set_state_draft(ids)

    def button_request(self, ids):
        return self.set_state_request(ids)

    def button_confirm(self, ids):
        return self.set_state_confirm(ids)

    def button_cancel(self, ids):
        return self.set_state_cancel(ids)

    def button_draft(self, ids):
        return self.set_state_draft(ids)

    def button_restore(self, ids):
        return self.set_state_draft(ids)

    def set_state_draft(self, ids):
        for advance in self.browse(ids):
            for advance_line in advance.lines:
                advance_line.set_state(advance_line.id, { 'state': 'draft', })
        self.write(ids, { 'state': 'draft', })

    def set_state_request(self, ids):
        for advance in self.browse(ids):
            for advance_line in advance.lines:
                advance_line.set_state(advance_line.id, { 'state': 'request', })
        self.write(ids, { 'state': 'request', })

    def set_state_post(self, ids):
        for advance in self.browse(ids):
            for advance_line in advance.lines:
                advance_line.set_state(advance_line.id, { 'state': 'posted', })
        self.write(ids, { 'state': 'posted', })

    def set_state_cancel(self, ids):
        for advance in self.browse(ids):
            for advance_line in advance.lines:
                advance_line.set_state(advance_line.id, { 'state': 'canceled', })
        self.write(ids, { 'state': 'canceled', })

    def set_state_confirm(self, ids):
        for advance in self.browse(ids):
            for advance_line in advance.lines:
                advance_line.set_state(advance_line.id, { 'state': 'confirmed', })
        self.write(ids, { 'state': 'confirmed', })

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
        if cr.nextid(self._table):
            cr.setnextid(self._table, cr.currid(self._table))
        new_id = super(DocumentAdvanceCash, self).create(vals)
        advance = self.browse(new_id)
        new_id = advance.document.id
        cr.execute('UPDATE "' + self._table + '" SET id = %s '\
                            'WHERE id = %s', (advance.document.id, advance.id))
        ModelStorage.delete(self, advance.id)
        self.write(new_id, later)
        res = self.browse(new_id)
        return res.id

DocumentAdvanceCash()

class DocumentAdvanceCashLineSum(ModelSQL, ModelView):
    "Advance report (amount)"
    _name='ekd.document.line.advancecash.amounts'
    _description=__doc__

    advance = fields.Many2One('ekd.document.head.advancecash', 'Document advance Head',
            select=1)
    advance_line = fields.Many2One('ekd.document.line.request', 'Document line advance')
    name = fields.Char('Description')
    product = fields.Many2One('product.product', 'Product')
    uom = fields.Many2One('product.uom', 'Unit',
                    states={'required': Bool(Eval('product'))},
                    domain=[('category', '=', 
                    (Eval('product'), 'product.default_uom.category'))],
                    context={'category': (Eval('product'), 'product.default_uom.category')})
    quantity = fields.Float('Quantity', digits=(16, Eval('unit_digits', 2)))
    unit_digits = fields.Function(fields.Integer('Unit Digits', on_change_with=['uom']), 'get_unit_digits')
    unit_price = fields.Numeric('Price Unit', digits=(16, 2))
    amount_advance = fields.Numeric('Amount Advance', digits=(16, 2))
    balance = fields.Function(fields.Numeric('Balance Amount', digits=(16, 2)), 'get_balance')

    def on_change_with_unit_digits(self, vals):
        uom_obj = self.pool.get('product.uom')
        if vals.get('uom'):
            uom = uom_obj.browse(vals['uom'])
            return uom.digits
        return 2

    def get_unit_digits(self, ids, name):
        res = {}
        for line in self.browse(ids):
            if line.uom:
                res[line.id] = line.uom.digits
            else:
                res[line.id] = 2
        return res

    def get_balance(self, ids, name):
        res = {}
        return res

DocumentAdvanceCashLineSum()

class DocumentAdvanceCashLine(ModelSQL, ModelView):
    "Specification of advance report"
    _name='ekd.document.line.advancecash'
    _table='ekd_document_line_request'
    _description=__doc__

    requestcash = fields.Many2One('ekd.document.head.request', 'Document Request', ondelete='CASCADE',
                select=1)
    advance = fields.Many2One('ekd.document.head.advancecash', 'Document advance Head',
            select=1)
    advance_amount = fields.One2Many('ekd.document.line.advancecash.amounts', 'advance_line', 'Amount Advance')
    lines_received = fields.One2Many('ekd.document.line.payment', 'line_request', 'Line Amount Received')

    name_advance = fields.Char('Description')
    name = fields.Char('Description')
    amount_received = fields.Function(fields.Numeric('Amount Received', digits=(16, 2)), 'get_fields')
    amount_advance_total = fields.Function(fields.Numeric('Total Advance', digits=(16, 2)), 'get_amount_advance_total')
    amount_advance = fields.Function(fields.Numeric('Amount Advance', digits=(16, 2)), 'get_adv_fields', setter='set_adv_fields')
    state = fields.Selection([
            ('draft', 'Draft'),
            ('request', 'Request'),
            ('confirmed', 'Confirmed'),
            ('payment', 'Payment'),
            ('partially', 'Partially'),
            ('fully', 'Fully'),
            ('done', 'Done'),
            ('deleted', 'Deleted'),
            ], 'State', readonly=True)
    state_advance = fields.Selection([
                ('draft', 'Draft'),
                ('request', 'Request'),
                ('confirmed', 'Confirmed'),
                ('posted', 'Posted'),
                ('deleted', 'Deleted'),
                ], 'State', readonly=True)
    def default_state_advance(self):
        return 'draft'

    def default_type(self):
        return 'line'

    def get_adv_fields(self, ids, names):
        res = {}
        for name in names:
            res.setdefault(name, {})
            for id in ids:
                res[name].setdefault(id, False)
        for line in self.browse(ids):
            for advance_sum in line.advance_amount:
                if advance_sum.advance.id == line.advance.id:
                    for name in names:
                        if name == 'product' and advance_sum.product:
                            res[name][line.id] = advance_sum.product.id
                        elif name == 'uom' and advance_sum.uom:
                            res[name][line.id] = advance_sum.uom.id
                        elif name == 'quantity':
                            res[name][line.id] = advance_sum.quantity
                        elif name == 'unit_price':
                            res[name][line.id] = advance_sum.unit_price
                        elif name == 'amount_advance':
                            res[name][line.id] = advance_sum.amount_advance
        return res

    def get_fields(self, ids, names):
        if not ids:
            return {}
        res = {}
        for request in self.browse(ids):
            for name in names:
                res.setdefault(name, {})
                res[name].setdefault(request.id, {})
                if name == 'amount_balance':
                    res[name][request.id] = request.amount_request-request.amount_received
                elif name == 'amount_payment':
                    res[name][request.id] = request.amount_request-request.amount_received
                elif name == 'unit_digits':
                    if request.uom:
                        res[name][request.id] = request.uom.digits
                    else:
                        res[name][request.id] = 2
                elif name == 'amount_received':
                    amount_received = Decimal('0.0')
                    for line_received in request.lines_received:
                        amount_received += line_received.amount_payment
                    res[name][request.id] = amount_received
        return res

    def get_amount_advance_total(self, ids, name):
        res = {}.fromkeys(ids, Decimal('0.0'))
        cr = Transaction().cursor
        cr.execute("SELECT advance_line, SUM(amount_advance) "\
                        "FROM ekd_document_line_advancecash_amounts "\
                        "WHERE advance_line in ("+','.join(map(str,ids))+") "\
                        "GROUP BY advance_line")
        for id, sum in cr.fetchall():
        # SQLite uses float for SUM 
            if not isinstance(sum, Decimal):
                sum = Decimal(str(sum))
            res[id] = sum
        return res

    def set_adv_fields(self, id, name, value):
        if not value:
            return
        test_found = True
        linesum_obj = self.pool.get('ekd.document.line.advancecash.amounts')
        line_ids = self.browse( id)
        if isinstance(line_ids, list) and len(line_ids)>0:
            line_ids = line_ids[0]

        #raise Exception('SET_ADV_FIELDS', str(value))
        if line_ids.advance_amount:
            for advance_sum in line_ids.advance_amount:
                if advance_sum.advance == line_ids.advance.id:
                    test_found = False
                    if name == 'product':
                        linesum_obj.write(advance_sum.id, {
                                'advance':line_ids.advance,
                                'advance_line':line_ids.id,
                                'product':value, })
                    elif name == 'uom':
                        raise Exception(name, value)
                        linesum_obj.write(advance_sum.id, {
                                'advance':line_ids.advance,
                                'advance_line':line_ids.id,
                                'uom':value, })
                    elif name == 'quantity':
                        linesum_obj.write(advance_sum.id, {
                                'advance':line_ids.advance,
                                'advance_line':line_ids.id,
                                'quantity':value, })
                    elif name == 'unit_price':
                        linesum_obj.write(advance_sum.id, {'unit_price':value, })
                    elif name == 'amount_advance':
                        linesum_obj.write(advance_sum.id, {
                                'advance':line_ids.advance,
                                'advance_line':line_ids.id,
                                'amount_advance':value, })
            if test_found:
                if name == 'product':
                    linesum_obj.create({
                                'advance':line_ids.advance,
                                'advance_line':line_ids.id,
                                'product':value,
                                })
                elif name == 'uom':
                    linesum_obj.create( {
                                'advance':line_ids.advance,
                                'advance_line':line_ids.id,
                                'uom':value,
                                })
                elif name == 'quantity':
                    linesum_obj.create( {
                                'advance':line_ids.advance,
                                'advance_line':line_ids.id,
                                'quantity':value, 
                                })
                elif name == 'unit_price':
                    linesum_obj.create( {
                                'advance':line_ids.advance,
                                'advance_line':line_ids.id,
                                'unit_price':value,
                                })
                elif name == 'amount_advance':
                    linesum_obj.create( {
                                'advance':line_ids.advance, 
                                'advance_line':line_ids.id, 
                                'amount_advance':value, 
                                })

        else:
            if name == 'product':
                linesum_obj.create({
                                'advance':line_ids.advance, 
                                'advance_line':line_ids.id, 
                                'product':value, 
                                })
            elif name == 'uom':
                linesum_obj.create( {
                                'advance':line_ids.advance, 
                                'advance_line':line_ids.id, 
                                'uom':value,
                                })
            elif name == 'quantity':
                linesum_obj.create( {
                                'advance':line_ids.advance, 
                                'advance_line':line_ids.id, 
                                'quantity':value, 
                                })
            elif name == 'unit_price':
                linesum_obj.create( {
                                'advance':line_ids.advance, 
                                'advance_line':line_ids.id, 
                                'unit_price':value, 
                                })
            elif name == 'amount_advance':
                linesum_obj.create( {
                                'advance':line_ids.advance, 
                                'advance_line':line_ids.id, 
                                'amount_advance':value, 
                                })

    def set_state(self, ids, value):
        self.write(ids, {'state': value, })

    def write(self, ids, value=None):
#        raise Exception('WRITE-Lines',str(value))
        if value is None:
            return
        linesum_obj = self.pool.get('ekd.document.line.advancecash.amounts') 
        line_ids = self.browse(ids)
        line_sum = {}
        not_found = True
        value = value.copy()
        for field in value.keys():
            if field in ('advance', 'advance_line', 'product', 'uom', 'quantity', 'unit_price', 'amount_advance'):
                    line_sum[field] = value[field]
        for field in line_sum.keys():
            if field != 'advance':
                del value[field]
        for amount_sum in line_ids.advance_amount:
            if amount_sum.advance.id == line_ids.advance.id:
                not_found = False
                linesum_obj.write(amount_sum.id, line_sum)
        if not_found:
            line_sum['advance'] = line_ids.advance.id
            line_sum['advance_line'] = line_ids.id
            linesum_obj.create(line_sum)

        return super(DocumentAdvanceCashLine, self).write(ids, value)

    def on_change_with_unit_digits(self, vals):
        uom_obj = self.pool.get('product.uom')
        if vals.get('uom'):
            uom = uom_obj.browse(vals['uom'])
            return uom.digits
        return 2

    def get_unit_digits(self, ids, name):
        res = {}
        for line in self.browse(ids):
            if line.uom:
                res[line.id] = line.uom.digits
            else:
                res[line.id] = 2
        return res

DocumentAdvanceCashLine()

class DocumenAdvanceCashReport(Report):
    _name='ekd.document.print.advancecash'
    def parse(self, report, objects, datas):
        res = super(DocumentAdvanceCash, self).parse(report, objects, datas)
        return res

DocumenAdvanceCashReport()
