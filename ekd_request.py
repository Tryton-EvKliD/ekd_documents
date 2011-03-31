# -*- encoding: utf-8 -*-
#NOTE: Заявки на деньги
"Document Request for money"
from trytond.model import ModelView, ModelSQL, ModelStorage, fields
from trytond.transaction import Transaction
from trytond.report import Report
from trytond.tools import safe_eval
import time
from decimal import Decimal, ROUND_HALF_EVEN
from trytond.pyson import In, If, Get, Eval, Not, Equal, Bool, Or, And
import time
import datetime
from ekd_state_document import _STATE_REQUEST

_REQUEST_STATES = {
    'readonly': Not(In(Eval('state_doc'),['empty', 'draft'])),
    }

_REQUEST_DEPENDS = ['state_doc']

_LINE_STATES = {
    'readonly': Equal(Eval('state_doc'), 'draft'),
    }

_LINE_DEPENDS = ['state_doc']

_ISSUE_STATES = {
    'readonly': Not(In(Eval('state_doc'), ['empty', 'draft', 'confirmed', 'payment'])),
    }

_RECEIVED_STATES = {
    'readonly': Not(Equal(Eval('state_doc'), 'draft')),
    }

_RECEIVED_DEPENDS = ['state_doc']

class DocumentRequest(ModelSQL, ModelView):
    "Documents of request"
    _name='ekd.document.head.request'
    _description=__doc__
    _inherits = {'ekd.document': 'document'}

    document = fields.Many2One('ekd.document', 'Document', required=True,
                ondelete='CASCADE')

    template_request = fields.Function(fields.Many2One('ekd.document.template',
                'Document', help="Template document",
                states=_REQUEST_STATES, depends=_REQUEST_DEPENDS,
                domain=[('type_account', '=',
                    Eval('type_request',
                        Get(Eval('context', {}), 'type_request')))]
                ), 'get_fields', setter='set_fields')

    date_issued = fields.Function(fields.Date('Date of issue', states=_ISSUE_STATES,
                depends=_REQUEST_DEPENDS), 'get_fields', setter='set_fields')
    type_request = fields.Selection([
                ('request_monies', 'Money'),
                ('request_product', 'Product'),
                ('request_service', 'Service'),
                ], required=True, string='Type request')

    document_ref = fields.Reference('Base', selection='documents_get', select=1, 
                domain=[('state','=','open')], context={'request_from':'requestcash'},
                states=_REQUEST_STATES, depends=_REQUEST_DEPENDS, on_change=['document_ref'],  )
    document_name = fields.Function(fields.Char('Document Name'), 'get_doc_name')
    invoice_ref = fields.Reference('Invoice', selection='invoice_get', select=1,
                states=_REQUEST_STATES, depends=_REQUEST_DEPENDS)
    manager = fields.Function(fields.Many2One('company.employee', 
                'Manager to confirm', states=_REQUEST_STATES, depends=_REQUEST_DEPENDS),
                'get_fields', setter='set_fields')
    recipient = fields.Function(fields.Many2One('party.party', 'Recipient',
                states=_REQUEST_STATES, depends=_REQUEST_DEPENDS),
                'get_fields', setter='set_fields')

    amount_request = fields.Function(fields.Numeric('Total Request', 
                digits=(16, Eval('currency_digits', 2)), 
                readonly=True,  on_change_with=['lines']), 'get_fields', setter='set_fields')
    amount_received = fields.Function(fields.Numeric('Total Received',
                digits=(16, Eval('currency_digits', 2)), readonly=True,
                on_change_with=['lines']), 'get_paid_fields', setter='set_fields')
    amount_balance = fields.Function(fields.Numeric('Balance', digits=(16, Eval('currency_digits', 2)),
                readonly=True, on_change_with=['lines']), 'get_fields')
    lines = fields.One2Many('ekd.document.line.request', 'requestcash', 'Lines Request',
            states=_RECEIVED_STATES, depends=_RECEIVED_DEPENDS, 
            context={
                'document_ref': Eval('document_ref'), 
                'currency_digits': Eval('currency_digits')
                } )

#    currency = fields.Many2One('currency.currency', 'Currency')
    currency_digits = fields.Function(fields.Integer('Currency Digits', 
                on_change_with=['currency']), 'get_currency_digits')

    state_doc = fields.Function(fields.Selection(_STATE_REQUEST, 
                                required=True, readonly=True, 
                                string='State'), 'get_fields', 
                setter='set_fields')
    # Инициализация класса
    def __init__(self):
        super(DocumentRequest, self).__init__()
        self._rpc.update({
            'button_add_number': True,
            'button_draft': True,
            'button_request': True,
            'button_cancel': True,
            'button_issue': True,
            'button_restore': True,
            'button_confirmed': True,
            'button_payment': True,
            })
        self._order.insert(0, ('date_document', 'ASC'))
        self._order.insert(1, ('number_our', 'ASC'))

        self._error_messages.update({
            'you_dont_confirm': 'You can not confirm this request on money!',
            'manager_not_find':"Manager as User don't found",
            'employee_not_find':"Employee as User don't found",
            })
#
#	Заполнение полей значениями по умолчанию
#

    def default_state_doc(self):
        return 'empty'

    def default_type_request(self):
        return 'request_monies'

    def default_date_issued(self):
        return Transaction().context.get('current_date', datetime.datetime.now())

    def default_employee(self):
        return Transaction().context.get('employee', False)

    def default_recipient(self):
        return Transaction().context.get('employee', False)

#    def default_currency(self):
#        company_obj = self.pool.get('company.company')
#        currency_obj = self.pool.get('currency.currency')
#        if context is None:
#            context = {}
#        if context.get('company'):
#            company = company_obj.browse(context['company'],
#                    )
#            return company.currency.id
#        return False

#    def default_currency_digits(self):
#        company_obj = self.pool.get('company.company')
#        if context is None:
#            context = {}
#        if context.get('company'):
#            company = company_obj.browse(context['company'],
#                    )
#            return company.currency.digits
#        return 2


################################################################################
#
# Процедуры заполнения функциональных полей
#
################################################################################

    def get_rec_name(self, ids, name):
        if not ids:
            return {}
        return self.pool.get('ekd.document').get_rec_name(ids, name)

    def get_template_select(self, ids, name):
        template_obj = self.pool.get('ekd.document.template')
        template_ids = template_obj.search(['type_account','=','request_monies'])
        res=[]
        for template in template_obj.browse(template_ids):
            res.append([template.id,template.name])
        return res

    def get_currency_digits(self, ids, name):
        assert name in ('currency_digits'), 'Invalid name %s' % (name)
        res={}.fromkeys(ids, 2)
        for document in self.browse(ids):
            if document.currency:
                res[document.id] = document.currency.digits
        return res


    def get_amount_line(self, ids, names):
        if not ids:
            return {}
        res={}
        amount_request = Decimal('0.0')
        amount_received = Decimal('0.0')
        for request in self.browse(ids):
            for line in request.lines:
                amount_request += abs(line.amount_request)
                amount_received += abs(line.amount_received)
            for name in names:
                res.setdefault(name, {})
                res[name].setdefault(request.id, False)
                if name == 'amount_request':
                    res[name][request.id] = amount_request
                elif name == 'amount_received':
                    res[name][request.id] = amount_received
                elif name == 'amount_balance':
                    res[name][request.id] = amount_request-amount_received
            amount_request = Decimal('0.0')
            amount_received = Decimal('0.0')
        return res

    def get_doc_name(self, ids, name):
        if not ids:
            return
        res={}
        for request in self.browse(ids):
            if request.document_ref:
                model, model_id = request.document_ref.split(',')
                if model and model_id:
                    model_rec = self.pool.get(model).browse(int(model_id))
                    if model_rec.full_name:
                        res[request.id] = model_rec.full_name
                    elif model_rec.rec_name:
                        res[request.id] = model_rec.rec_name
                    elif model_rec.name:
                        res[request.id] = model_rec.name
                    else:
                        res[request.id] = 'name null'
        return res


    def documents_get(self):
        dictions_obj = self.pool.get('ir.dictions')
        res = []
        diction_ids = dictions_obj.search([
                ('model', '=', 'ekd.document.head.request'),
                ('pole', '=', 'document_ref'),
                ])
        for diction in dictions_obj.browse(diction_ids):
            res.append([diction.key, diction.value])
        return res

    def get_documents_ref(ids, model, name, values=None):
        raise Exception('get_documents_ref')

    def invoice_get(self):
        dictions_obj = self.pool.get('ir.dictions')
        res = []
        diction_ids = dictions_obj.search([
                ('model', '=', 'ekd.document.head.request'),
                ('pole', '=', 'invoice_ref'),
                ])
        for diction in dictions_obj.browse(diction_ids):
            res.append([diction.key, diction.value])
        return res

    def get_fields(self, ids, names):
        if not ids:
            return {}
        res = {}
        for request in self.browse(ids):
            for name in names:
                res.setdefault(name, {})
                res[name].setdefault(request.id, False)
                if name == 'manager':
                    res[name][request.id] = request.from_party.id
                elif name == 'employee_':
                    res[name][request.id] = request.employee.id
                elif name == 'recipient':
                    res[name][request.id] = request.to_party.id
                elif name == 'date_issued':
                    res[name][request.id] = request.date_account
                elif name == 'state_doc':
                    res[name][request.id] = request.state
                elif name == 'template_request':
                    res[name][request.id] = request.template.id
                elif name == 'amount_request':
                    res[name][request.id] = request.amount
#                elif name == 'amount_received':
#                    res[name][request.id] = request.amount_payment
                elif name == 'amount_balance':
                    res[name][request.id] = request.amount-request.amount_payment-request.amount_received

        return res

    def set_fields(self, id, name, value):
#        assert name in ('manager', 'employee', 'date_issued', 'state_doc'), 'Invalid name SET PARTY %s' % (name)
        if not value:
            return
        if name == 'manager':
            self.write(id, {'from_party':value, })
        elif name == 'employee':
            self.write(id, {'employee':value, })
        elif name == 'recipient':
            self.write(id, {'to_party':value, })    
        elif name == 'date_issued':
            self.write(id, {'date_account':value, })
        elif name == 'state_doc':
            self.write(id, {'state':value, })
        elif name == 'amount_request':
            self.write(id, {'amount':value, })
        elif name == 'amount_received':
            self.write(id, {'amount_pay':value, })
        elif name == 'template_request':
            self.write(id, { 'template': value, })
        elif name == 'amount_request':
            self.write(id, { 'amount': value, })

    def get_paid_fields(self, ids, name):
        res = {}.fromkeys(ids, Decimal('0.0'))
        cr = Transaction().cursor
        cr.execute("SELECT doc_base, SUM(amount_payment) "\
                    "FROM ekd_document_line_payment "\
                    "WHERE doc_base in ("+','.join(map(str,ids))+") and state='done' "\
                    "GROUP BY doc_base")
        for id, sum in cr.fetchall():
            # SQLite uses float for SUM
            if not isinstance(sum, Decimal):
                sum = Decimal(str(sum))
            res[id] = sum
        return res

################################################################################
#
# События изменения полей
#
################################################################################
    def on_change_with_amount_request(self, values):
        amount = Decimal('0.0')
        for line in values['lines']:
            amount += line['amount_request']
        return amount

    def on_change_with_amount_received(self, values):
        amount = Decimal('0.0')
        for line in values['lines']:
            amount += line['amount_received']
        return amount

    def on_change_with_amount_balance(self, values):
        amount = Decimal('0.0')
        for line in values['lines']:
            amount += abs(line['amount_request'])-abs(line['amount_received'])
        return amount

    def on_change_document_ref(self, value):
        res={}
        if value.get('document_ref'):
            model, model_id = value.get('document_ref').split(',')
            if model_id == '0':
                return res
            if model == 'project.project':
                model_obj = self.pool.get(model)
                model_ids = model_obj.browse(int(model_id))
                if model_ids.manager:
                    res['manager'] = model_ids.manager.id
                if model_ids.employee:
                    res['recepient'] = model_ids.employee.id
                if model_ids.company:
                    res['company'] = model_ids.company.id
        return res

#
#	Обработка клиентских вызовов процедур
#

    def button_draft(self, ids):
        return self.draft(ids)

    def button_confirmed(self, ids):
        return self.confirmed(ids)

    def button_cancel(self, ids):
        return self.draft(ids)

    def button_issue(self, ids):
        return self.paid(ids)

    def button_restore(self, ids):
        return self.draft(ids)

    def button_request(self, ids):
        return self.request(ids)

    def button_payment(self, ids):
        return self.on_payment(ids)

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

    # Изменение состояния документа в Черновик
    def draft(self, ids):
        requestline_obj= self.pool.get('ekd.document.line.request')
        for line in self.browse(ids):
            requestline_obj.write([k.id for k in line.lines], {
                        'state': 'draft',
                        })
            self.write(ids, {
                            'state': 'draft',
                    })
    # Закрытие документа
    def done(self, ids):
        requestline_obj= self.pool.get('ekd.document.line.request')
        for line in self.browse(ids):
            requestline_obj.write([k.id for k in line.lines], {
                        'state': 'done',
                        })
            self.write(ids, {
                            'state': 'done',
                    })
    # Формирование запроса для подтверждения документа
    def request(self, ids):
        sequence_obj = self.pool.get('ir.sequence')
        date_obj = self.pool.get('ir.date')
        request_obj = self.pool.get('res.request')
        req_ref_obj = self.pool.get('res.request.reference')
        user_obj = self.pool.get('res.user')
        requestline_obj= self.pool.get('ekd.document.line.request')
        for requestcash in self.browse(ids):
            if requestcash.manager:
                reference = sequence_obj.get_id(
                                requestcash.template.sequence.id)
                for line in self.browse(ids):
                    requestline_obj.write([k.id for k in line.lines], {
                                        'state': 'request',
                                            })
                self.write(requestcash.id, {
                        'number_our': reference,
                            'state': 'request',
                        'post_date': date_obj.today(),
                    })
                manager_id = user_obj.search(
                                            [('employee','=',requestcash.manager.id)],
                                            limit=1)

                employee_id = user_obj.search(
                                            [('employee','=',requestcash.employee.id)],
                                            limit=1)

                if len(manager_id) == 0:
                    self.raise_user_error(cursor, error="Warning",
                                                  error_description="manager_not_find")
                if len(employee_id) == 0:
                    self.raise_user_error(cursor, error="Warning",
                                              error_description="employee_not_find")

                if isinstance(manager_id, list):
                    manager_id = manager_id[0]

                if isinstance(employee_id, list):
                    employee_id = employee_id[0]

                vals={}
                vals['name'] = u"Пожалуйста подтвердите"\
                    u" - %s с датой выдачи %s"%(requestcash.rec_name,
                                               requestcash.date_issued.strftime('%d.%m.%Y'))

                vals['active'] = True
                vals['priority'] = '1'
                vals['act_from'] = employee_id
                vals['act_to'] = manager_id
                vals['body'] = requestcash.note
                vals['state'] = 'waiting'

                request_id = request_obj.create(vals)

                req_ref_obj.create({
                        'request': request_id ,
                        'reference': '%s,%s' % ('ekd.document.head.request', ids[0]),
                            })
    # Подтверждение документа
    def confirmed(self, requestcash_id):
        sequence_obj = self.pool.get('ir.sequence')
        date_obj = self.pool.get('ir.date')
        requestline_obj= self.pool.get('ekd.document.line.request')
        for document in self.browse(requestcash_id):
            reference = sequence_obj.get_id(
                                        document.template.sequence.id)
            if document.from_party.id == Transaction().context.get('employee', False):
                requestline_obj.write([k.id for k in document.lines], {
                        'state': 'confirmed',
                        })
                self.write(document.id, {
                        'number_our': reference,
                        'state': 'confirmed',
                        'post_date': date_obj.today(),
                        })
            else:
                self.raise_user_error(error="Error",
                              error_description="you_dont_confirm")
        return

    # Постановка на оплату
    def on_payment(self, ids):
        requestline_obj= self.pool.get('ekd.document.line.request')
        for line in self.browse(ids):
            requestline_obj.write([k.id for k in line.lines], {
                        'state': 'payment',
                        })
        self.write(ids, {
                        'state': 'payment',
                        })

    def paid(self, ids):
        self.write(ids, {
                        'state': 'paid',
                        })

    # Создание объекта
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
        if vals.get('invoice_ref') == ',':
            del vals['invoice_ref']
        if vals.get('document_ref') == ',':
            del vals['invoice_ref']
        if cr.nextid(self._table):
            cr.setnextid(self._table, cr.currid(self._table))
        new_id = super(DocumentRequest, self).create(vals)
        request = self.browse(new_id)
        new_id = request.document.id
        cr.execute('UPDATE "' + self._table + '" SET id = %s '\
                        'WHERE id = %s', (request.document.id, request.id))
        ModelStorage.delete(self, request.id)
        self.write(new_id, later)
        res = self.browse(new_id)
        return res.id

DocumentRequest()

# Строки документа (Заявки)
class DocumentRequestLine(ModelSQL, ModelView):
    "Document specifications of Request"
    _name='ekd.document.line.request'
    _description=__doc__

    requestcash = fields.Many2One('ekd.document.head.request', 'Document Request',
        ondelete='CASCADE', select=1)
    type = fields.Selection([
        ('line', 'Line'),
        ('subtotal', 'Subtotal'),
        ], 'Type', select=1, required=True, states={
            'invisible': Bool(Eval('standalone')),
        })
    name = fields.Char('Description', states=_LINE_STATES, depends=_LINE_DEPENDS)
    note = fields.Text('Note', states=_LINE_STATES, depends=_LINE_DEPENDS)
    product = fields.Many2One('product.product', 'Product', states=_LINE_STATES, 
        depends=_LINE_DEPENDS)
    uom = fields.Many2One('product.uom', 'Unit', 
        states={'required': Bool(Eval('product')), 'readonly': Not(Equal(Eval('state'), 'draft'))},
        domain=[('category', '=', ( Eval('product'), 'product.default_uom.category'))],
        context={'category': (Eval('product'), 'product.default_uom.category')})
    quantity = fields.Float('Quantity', digits=(16, Eval('currency_digits', 2)),
        states=_LINE_STATES, depends=_LINE_DEPENDS)
    unit_digits = fields.Function(fields.Integer('Unit Digits', on_change_with=['uom']), 'get_fields')
    unit_price = fields.Numeric('Price Unit', digits=(16, Eval('currency_digits', 2)), states=_LINE_STATES, 
        depends=_LINE_DEPENDS)
    lines_received = fields.One2Many('ekd.document.line.payment', 'line_request',
        'Line Amount Received')
    amount_request = fields.Numeric('Amount Request', digits=(16, Eval('currency_digits', 2)),
        states=_LINE_STATES, depends=_LINE_DEPENDS)
    amount_received = fields.Function(fields.Numeric('Amount Received',
        digits=(16, Eval('currency_digits', 2))), 'get_fields')
    amount_balance = fields.Function(fields.Numeric('Balance', digits=(16, Eval('currency_digits', 2)),
        readonly=True, on_change_with=['amount_request','amount_received']), 'get_fields')
    amount_payment = fields.Function(fields.Numeric('Amount Payment', digits=(16, Eval('currency_digits', 2))), 'get_fields', setter='set_fields')
    currency_digits = fields.Function(fields.Integer('Currency Digits'), 'get_currency_digits')
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

    def default_state(self):
        return 'draft'

    def default_type(self):
        return 'line'

    def default_currency_digits(self):
        return Transaction().context.get('currency_digits', 2)

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
                elif name == 'unit_digits':
                    if request.uom:
                        res[name][request.id] = request.uom.digits
                    else:
                        res[name][request.id] = 2
                elif name == 'amount_payment':
                    amount_payment = Decimal('0.0')
                    for line_received in request.lines_received:
                        if line_received.state == 'payment': 
                            amount_payment += line_received.amount_payment
                    res[name][request.id] = amount_payment
#                    res[name][request.id] = request.amount_request-request.amount_received
                elif name == 'amount_received':
                    amount_received = Decimal('0.0')
                    for line_received in request.lines_received:
                        if line_received.state == 'done': 
                            amount_received += line_received.amount_payment
                    res[name][request.id] = amount_received
        return res

    def set_fields(self, id, name, value):
        if not value:
            return

    def get_currency_digits(self, ids, name):
        res = {}
        for line in self.browse(ids):
            res[line.id] = line.requestcash.currency and line.requestcash.currency.digits or 2
        return res

    def on_change_with_amount_balance(self, vals):
        if vals.get('amount_request') and vals.get('amount_received'):
            return vals.get('amount_request')-vals.get('amount_received')
        elif vals.get('amount_request'):
            return vals.get('amount_request')
        else:
            return Decimal('0.0')

DocumentRequestLine()

class DocumentRequestPrint(Report):
    _name='ekd.document.print.request'

    def parse(self, report, objects, datas, localcontext):
        raise Exception(str(report),str(object),str(datas))
        res = super(DocumentRequestPrint, self).parse(report, objects, datas, localcontext)
        return res

DocumentRequestPrint()
