# -*- coding: utf-8 -*-
#NOTE: Документы - Счета
"Document Invoice"
from trytond.model import ModelWorkflow, ModelStorage, ModelView, ModelSQL, fields
from trytond.tools import safe_eval
from trytond.pyson import In, If, Get, Eval, Not, Equal, Bool, Or, And
from trytond.transaction import Transaction
import time
from decimal import Decimal, ROUND_HALF_EVEN
import datetime
from trytond.report import Report
from pytils import numeral
from ekd_state_document import _STATE_INVOICE

_STATES = {
    'readonly': Not(Equal(Eval('state'), 'draft')),
}
 
class DocumentInvoice(ModelWorkflow, ModelSQL, ModelView):
    "Documents (Invoice) "
    _name='ekd.document.head.invoice'
    _description=__doc__
    #_table='documents_document_stock'
    _inherits = {'ekd.document': 'document'}

    document = fields.Many2One('ekd.document', 'Document', required=True,
            ondelete='CASCADE')

    direct_document = fields.Selection([
                ('invoice_revenue', 'For Customer'),
                ('invoice_expense', 'From Supplier'),
                ], 'Direct Document')

    type_product = fields.Selection([
                ('fixed_assets', 'Fixed Assets'),
                ('intangible', 'Intangible assets'),
                ('material', 'Material'),
                ('goods', 'Goods'),
                ], 'Type Product')

    template_invoice = fields.Function(fields.Many2One('ekd.document.template',
                'Document Name',
                domain=[('type_account', '=',
                    Eval('direct_document',
                        Get(Eval('context', {}), 'direct_document')))]
                ), 'get_fields', setter='set_fields')
    number_doc = fields.Function(fields.Char('Number Document', 
                states={'invisible': And(Not(Bool(Eval('number_doc'))),
                    Not(Equal(Eval('direct_document',''),'invoice_expense')))}), 
                'get_fields', setter='set_fields', searcher='template_search')
    from_to_party = fields.Function(fields.Many2One('party.party',
                'Party'), 'get_fields', setter='set_fields')

    lines = fields.One2Many('ekd.document.line.product', 'invoice', 'Lines',
                context={'type_product':Eval('type_product')})
    amount_doc = fields.Function(fields.Numeric('Amount', digits=(16, Eval('currency_digits', 2))), 
                'get_fields', setter='set_fields')
    amount_tax = fields.Function(fields.Numeric('Amount Tax', digits=(16, Eval('currency_digits', 2))), 
                'get_fields')
    currency = fields.Many2One('currency.currency', 'Currency')
    currency_digits = fields.Function(fields.Integer('Currency Digits', 
                on_change_with=['currency']), 'get_currency_digits')
    payment_term = fields.Many2One('ekd.document.payment_term',
                'Payment Term', required=True, states=_STATES)
    form_payment = fields.Selection([
            ('cash','Cash payment'),
            ('bank','Bank payment'),
            ('post','Post payment'),
            ('internet','Internet payment'),
            ], 'Form of payment')
    kind_payment = fields.Selection([
            ('postpay','Postpay'),
            ('prepayment','Prepayment'),
            ('advance','Down payment'),
            ], 'Kind of payment')
    type_tax = fields.Selection([
            ('not_vat','Not VAT'),
            ('including','Including'),
            ('over_amount','Over Amount'),
            ], 'Type Compute Tax')

    state_doc = fields.Function(fields.Selection(_STATE_INVOICE, required=True, readonly=True, string='State'), 'get_fields',
            setter='set_fields')
    deleting = fields.Boolean('Flag deleting', readonly=True)

    def __init__(self):
        super(DocumentInvoice, self).__init__()
        self._rpc.update({
            'button_add_number': True,
            'button_draft': True,
            'button_to_pay': True,
            'button_part_paid': True,
            'button_paid': True,
            'button_received': True,
            'button_cancel': True,
            'button_restore': True,
            'button_print': True,
            'button_send': True,
            'button_post': True,
            'button_obtained': True,
            'button_delivered': True,
            })

        self._order.insert(0, ('date_document', 'ASC'))
        self._order.insert(1, ('template', 'ASC'))

    def default_state_doc(self):
        return Transaction().context.get('state') or 'draft'

    def default_type_product(self):
        return Transaction().context.get('type_product') or 'material'

    def default_from_to_party_doc(self):
        return Transaction().context.get('from_to_party') or False

    def default_direct_document(self):
        return Transaction().context.get('direct_document') or 'invoice_revenue'

    def default_template_invoice(self):
        context = Transaction().context
        if context.get('template_invoice', False):
            return  context.get('template_invoice')
        else:
            template_obj = self.pool.get('ekd.document.template')
            template_ids = template_obj.search( [
                        ('type_account','=',context.get('direct_document'))
                        ], order=[('sequence','ASC')])
            if len(template_ids) > 0:
                return template_ids[0]

    def default_currency(self):
        company_obj = self.pool.get('company.company')
        company = company_obj.browse(Transaction().context['company'])
        return company.currency.id

    def default_currency_digits(self):
        company_obj = self.pool.get('company.company')
        context = Transaction().context
        if context.get('company'):
            company = company_obj.browse( context['company'])
            return company.currency.digits
        return 2

    def get_currency_digits(self,  ids, name):
        res = {}
        for line in self.browse( ids):
            res[line.id] = line.currency and line.currency.digits or 2
        return res

    def default_payment_term(self):
        payment_term_obj = self.pool.get('ekd.document.payment_term')
        payment_term_ids = payment_term_obj.search(self.payment_term.domain)
        if len(payment_term_ids) == 1:
            return payment_term_ids[0]
        return False

    def default_amount(self):
        return Transaction().context.get('amount') or Decimal('0.0')

    def default_company(self):
        return Transaction().context.get('company') or False

    def get_fields(self,  ids, names):
        if not ids:
            return {}
        res={}
        for line in self.browse( ids):
            for name in names:
                res.setdefault(name, {})
                res[name].setdefault(line.id, False)
                if name == 'number_doc':
                    if line.direct_document == 'invoice_revenue' :
                        res[name][line.id] = line.number_our
                    else:
                        res[name][line.id] = line.number_in
                elif name == 'state_doc':
                    res[name][line.id] = line.state
                elif name == 'amount_doc':
                    for line_spec in line.lines:
                        if line_spec.type == 'line':
                            res[name][line.id] += line_spec.amount
                elif name == 'amount_tax':
                    for line_spec in line.lines:
                        if line_spec.type == 'line':
                            res[name][line.id] += line_spec.amount_tax
                elif name == 'from_to_party':
                        if line.direct_document == 'invoice_revenue':
                            res[name][line.id] = line.from_party.id
                        else:
                            res[name][line.id] = line.to_party.id
                elif name == 'template_invoice':
                        res[name][line.id] = line.template.id
        return res

    def set_fields(self, ids, name, value):
        if isinstance(ids, list):
            ids = ids[0]
        if not value:
            return
        document = self.browse( ids)
        if name == 'state_doc':
            self.write( ids, {'state':value, })
        elif name == 'template_invoice':
            self.write( ids, { 'template': value, })
        elif name == 'number_doc':
            if document.direct_document == 'invoice_revenue' :
                self.write( ids, { 'number_our': value, })
            else:
                self.write( ids, { 'number_in': value, })
        elif name == 'amount_doc':
            self.write( ids, { 'amount': value, })
        elif name == 'from_to_party':
            if document.direct_document == 'invoice_revenue' :
                self.write( ids, { 'from_party': value, })
            else:
                self.write( ids, { 'to_party': value, })

    def template_select_get(self):
        context = Transaction().context
        template_obj = self.pool.get('ekd.document.template')
        raise Exception(str(context))
        template_ids = template_obj.search( ['type_account','=', 
                        context.get('direct_document', 'invoice_revenue')])
        res=[]
        for template in template_obj.browse( template_ids):
            res.append([template.id,template.name])
        return res

    def template_search(self,  name, domain=[]):
        if name == 'template_invoice':
            for table, exp, value in domain:
                return  [('template', 'ilike', value)]
        elif name == 'from_party_doc':
            document_obj = self.pool.get('ekd.document')
            table, exp, value = domain[0]
            find_ids = document_obj.search( [('from_party', 'ilike', value)])
            return [('document', 'in', find_ids)]
        elif name == 'to_party_doc':
            document_obj = self.pool.get('ekd.document')
            table, exp, value = domain[0]
            find_ids = document_obj.search( [('to_party', 'ilike', value)])
            return [('document', 'in', find_ids)]

    def get_rec_name(self,  ids, name):
        if not ids:
            return {}
        return self.pool.get('ekd.document').get_rec_name( ids, name)

    def documents_base_get(self):
        dictions_obj = self.pool.get('ir.dictions')
        res = []
        diction_ids = dictions_obj.search( [
                                ('model', '=', self._name),
                                ('pole', '=', 'document_base'),
                                ], order=[('sequence','ASC')])
        if diction_ids:
            for diction in dictions_obj.browse( diction_ids):
                res.append([diction.key, diction.value])
        return res

    def on_change_document_base(self, vals):
        if not vals.get('document_base'):
            return {}
        model, model_id = vals.get('document_base').split(',')
        if not model or model_id == '0':
            return {}
        model_obj = self.pool.get(model)
        model_line = model_obj.browse(int(model_id))
        lines_new = {}
        field_import = [
        'product_ref', 
        'type_tax', 
        'tax', 
        'type', 
        'currency', 
        'unit', 
        'currency_digits', 
        'unit_price', 
        'amount_tax', 
        'product', 
        'description', 
        'type_product', 
        'unit_digits', 
        'amount', 
        'quantity']

        if hasattr(model_obj, 'lines'):
            for line_new in model_line.lines:
                if line_new.type == 'line':
                    lines_new.setdefault('add', []).append(line_new.read(line_new.id, field_import))
            return {
                'from_to_party': model_line.from_to_party.id,
                'parent': int(model_id),
                'lines':lines_new}
        else:
            return {
                'from_to_party': model_line.from_to_party.id,
                'parent': int(model_id)}

    def create(self, vals):
        later = {}
        vals = vals.copy()
        cursor = Transaction().cursor
        for field in vals:
            if field in self._columns\
                    and hasattr(self._columns[field], 'set'):
                later[field] = vals[field]
        for field in later:
            del vals[field]
        if cursor.nextid(self._table):
            cursor.setnextid(self._table, cursor.currid(self._table))
        new_id = super(DocumentInvoice, self).create( vals)
        invoice = self.browse( new_id)
        new_id = invoice.document.id
        cr = Transaction().cursor
        cr.execute('UPDATE "' + self._table + '" SET id = %s '\
                        'WHERE id = %s', (invoice.document.id, invoice.id))
        ModelStorage.delete(self, invoice.id)
        self.write( new_id, later)
        res = self.browse( new_id)
        return res.id

    def delete(self, ids):
        cr = Transaction().cursor
        doc_lines_obj = self.pool.get('ekd.document.line.product')
        for document in self.browse(ids):
            if document.state == 'deleted' and document.deleting:
                return super(DocumentInvoice, self).delete(ids)
            else:
                doc_lines_obj.write([x.id for x in document.lines], {'state': 'deleted', 'deleting':True})
                self.write(document.id, {'state': 'deleted', 'deleting':True})
        return True

    def button_add_number(self, ids):
        return self.new_number(ids)

    def button_post(self, ids):
        return self.post(ids)

    def button_obtained(self, ids):
        return self.obtained(ids)

    def button_delivered(self, ids):
        return self.delivered(ids)

    def button_paid(self, ids):
        return self.paid(ids)

    def button_part_paid(self, ids):
        return self.part_paid(ids)

    def button_to_pay(self, ids):
        return self.to_pay(ids)

    def button_send(self, ids):
        return self.send(ids)

    def button_print(self, ids):
        return self.print_document(ids)

    def button_cancel(self, ids):
        return self.cancel(ids)

    def button_draft(self, ids):
        return self.draft(ids)

    def button_restore(self, ids):
        return self.draft(ids)

    def new_number(self, ids):
        sequence_obj = self.pool.get('ir.sequence')
        for document in self.browse(ids):
        
            if document.template and document.template.sequence:
                sequence = sequence_obj.get_id(document.template.sequence.id)
            else:
                raise Exception('Error', 'Sequence for document not find!')
            self.write(document.id, {
                    'number_doc': sequence,
                    })

    def post(self, ids):
        return self.write(ids, {
            'state': 'posted',
            })

    def obtained(self, ids):
        return self.write(ids, {
            'state': 'obtained',
            })

    def delivered(self, ids):
        return self.write(ids, {
            'state': 'delivered',
            })

    def send(self, ids):
        return self.write(ids, {
            'state': 'sended',
            })

    def to_pay(self, ids):
        return self.write(ids, {
            'state': 'to_pay',
            })

    def paid(self, ids):
        return self.write(ids, {
            'state': 'paid',
            })

    def part_paid(self, ids):
        return self.write(ids, {
            'state': 'part_paid',
            })

    def print_document(self, ids):
        return self.write(ids, {
            'state': 'printed',
            })

    def draft(self, ids):
        cr = Transaction().cursor
        doc_lines_obj = self.pool.get('ekd.document.line.product')
        for document in self.browse(ids):
            doc_lines_obj.write([x.id for x in document.lines], {
                                    'state': 'draft',
                                    'deleting':False})
            self.write(document.id, {
                    'state': 'draft',
                    'deleting':False
                    })

    def cancel(self, ids):
        return self.write(ids, {
                'state': 'canceled',
                })

DocumentInvoice()

class DocumentInvoiceOutputPrint(Report):
    _name='ekd.document.print.invoice.output'

    def parse(self, report, objects, datas, localcontext={}):
        user = self.pool.get('res.user').browse(Transaction().user)
        localcontext['company'] = user.company
        localcontext['numeral'] = numeral
        res = super(DocumentInvoiceOutputPrint, self).parse(report, objects, datas, localcontext=localcontext)
        return res

DocumentInvoiceOutputPrint()
