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
from ekd_state_document import _STATE_INVOICE_GOODS

_STATES = {
    'readonly': Not(Equal(Eval('state'), 'draft')),
}
 
class DocumentInvoiceGoods(ModelWorkflow, ModelSQL, ModelView):
    "Documents (Invoice) "
    _name='ekd.document.head.invoice_goods'
    _description=__doc__
    _inherits = {'ekd.document': 'document'}

    document = fields.Many2One('ekd.document', 'Document', required=True,
            ondelete='CASCADE')

    direct_document = fields.Selection([
                ('output_goods', 'For Customer'),
                ('move_goods', 'Internal Move'),
                ('input_goods', 'From Supplier'),
                ], 'Direct Document')

    type_product = fields.Selection([
                ('fixed_assets', 'Fixed Assets'),
                ('intangible', 'Intangible assets'),
                ('material', 'Material'),
                ('goods', 'Goods'),
                ], 'Type Product')

    template_invoice = fields.Function(fields.Many2One('ekd.document.template',
                'Name',
                domain=[('type_account', '=',
                    Eval('direct_document', 
                        Get(Eval('context', {}), 'direct_document')))]
                ), 'get_fields', setter='set_fields')
    number_doc = fields.Function(fields.Char('Number',
                states={'invisible': And(Not(Bool(Eval('number_doc'))),
                    Not(Equal(Eval('direct_document',''),'input_goods')))}),
                'get_fields', setter='set_fields', searcher='template_search')
    from_to_party = fields.Function(fields.Many2One('party.party',
                'Party',
                states={'invisible': Equal(Eval('direct_document'),'move_goods')}
                ), 'get_fields', setter='set_fields')
    from_party_fnc = fields.Function(fields.Many2One('party.party',
                'From Party',
                states={'invisible': Not(Equal(Eval('direct_document'),'move_goods'))}
                ), 'get_fields', setter='set_fields')
    to_party_fnc = fields.Function(fields.Many2One('party.party',
                'To Party',
                states={'invisible': Not(Equal(Eval('direct_document'),'move_goods'))}
                ), 'get_fields', setter='set_fields')
    from_to_stock = fields.Function(fields.Many2One('ekd.company.department.stock',
                'Stock',
                states={'invisible': Equal(Eval('direct_document'),'move_goods')}
                ), 'get_fields', setter='set_fields')
    from_stock_fnc = fields.Function(fields.Many2One('ekd.company.department.stock',
                'From Stock',
                states={'invisible': Not(Equal(Eval('direct_document'),'move_goods'))}
                ), 'get_fields', setter='set_fields')
    to_stock_fnc = fields.Function(fields.Many2One('ekd.company.department.stock',
                'To Stock',
                states={'invisible': Not(Equal(Eval('direct_document'),'move_goods'))}
                ), 'get_fields', setter='set_fields')
    shipper = fields.Many2One('party.party', 'Shipper',
                states={'invisible': Eval('as_shipper', True)})
    consignee = fields.Many2One('party.party', 'Consignee',
                states={'invisible': Eval('as_consignee', True)})
    as_shipper = fields.Boolean('As Shipper')
    as_consignee = fields.Boolean('As Consignee')

    amount_doc = fields.Function(fields.Numeric('Amount', digits=(16, Eval('currency_digits', 2))), 
                'get_fields', setter='set_fields')
    amount_tax = fields.Function(fields.Numeric('Amount Tax', digits=(16, Eval('currency_digits', 2))), 
                'get_fields')
    currency = fields.Many2One('currency.currency', 'Currency')
    currency_digits = fields.Function(fields.Integer('Currency Digits',
                on_change_with=['currency']), 'get_currency_digits')
    type_tax = fields.Selection([
            ('not_vat','Not VAT'),
            ('including','Including'),
            ('over_amount','Over Amount')
            ], 'Type Compute Tax')
    lines = fields.One2Many('ekd.document.line.product', 'invoice', 'Lines',
                context={'type_product':Eval('type_product')})
    state_doc = fields.Function(fields.Selection(_STATE_INVOICE_GOODS, required=True, readonly=True, string='State'), 'get_fields', 
                setter='set_fields')
    deleting = fields.Boolean('Flag deleting', readonly=True)

    def __init__(self):
        super(DocumentInvoiceGoods, self).__init__()
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

    def default_as_shipper(self):
        return True

    def default_as_consignee(self):
        return True

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
        currency_obj = self.pool.get('currency.currency')
        context = Transaction().context
        if context.get('company'):
            company = company_obj.browse( context['company'])
            return company.currency.id
        return False

    def default_currency_digits(self):
        company_obj = self.pool.get('company.company')
        context = Transaction().context
        if context.get('company'):
            company = company_obj.browse( context['company'])
            return company.currency.digits
        return 2

    def default_state_doc(self):
        return Transaction().context.get('state_doc', 'draft')

    def get_currency_digits(self,  ids, name):
        res = {}
        for line in self.browse( ids):
            res[line.id] = line.currency and line.currency.digits or 2
        return res

    def default_amount(self):
        return Transaction().context.get('amount') or Decimal('0.0')

    def default_company(self):
        return Transaction().context.get('company') or False

    def documents_base_get(self):
        dictions_obj = self.pool.get('ir.dictions')
        res = []
        diction_ids = dictions_obj.search([
            ('model', '=', 'ekd.document.head.invoice_goods'),
            ('pole', '=', 'document_base'),
            ], order=[('sequence','ASC')])
        for diction in dictions_obj.browse(diction_ids):
            res.append([diction.key, diction.value])
        return res

    def get_fields(self,  ids, names):
        if not ids:
            return {}
        res={}
        for line in self.browse( ids):
            for name in names:
                res.setdefault(name, {})
                res[name].setdefault(line.id, False)
                if name == 'number_doc':
                    if line.direct_document == 'input_goods' :
                        res[name][line.id] = line.number_in
                    else:
                        res[name][line.id] = line.number_our
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
                    if line.direct_document == 'input_goods' :
                        res[name][line.id] = line.from_party.id
                    else:
                        res[name][line.id] = line.to_party.id
                elif name == 'from_party_fnc':
                    res[name][line.id] = line.from_party.id
                elif name == 'to_party_fnc':
                    res[name][line.id] = line.to_party.id
                elif name == 'template_invoice':
                    res[name][line.id] = line.template.id
                elif name == 'note_cash':
                    res[name][line.id] = line.note
        return res

    def set_fields(self,  ids, name, value):
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
            if document.direct_document == 'input_goods':
                self.write( ids, { 'number_in': value, })
            else:
                self.write( ids, { 'number_our': value, })
        elif name == 'amount_doc':
            self.write( ids, { 'amount': value, })
        elif name == 'from_party_doc':
            if document.direct_document == 'input_goods':
                self.write( ids, { 'from_party': value, })
            else:
                self.write( ids, { 'to_party': value, })
        elif name == 'from_party_fnc':
            self.write( ids, { 'from_party': value, })
        elif name == 'to_party_fnc':
            self.write( ids, { 'to_party': value, })

    def template_select_get(self):
        context = Transaction().context
        template_obj = self.pool.get('ekd.document.template')
        raise Exception(str(context))
        template_ids = template_obj.search( ['type_account','=', 
                        context.get('direct_document', 'input_goods')])
        res=[]
        for template in template_obj.browse( template_ids):
            res.append([template.id,template.name])
        return res

    def template_search(self,  name, domain=[]):
        if name == 'template_bank':
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

    def on_change_document_base(self, vals):
        if not vals.get('document_base'):
            return {}
        model, model_id = vals.get('document_base').split(',')
        model_obj = self.pool.get(model)
        if model_id == '0':
            return {}
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
                    tmp_line = line_new.read(line_new.id, field_import)
                    tmp_line['state'] = 'draft'
                    lines_new.setdefault('add', []).append(tmp_line)
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
        new_id = super(DocumentInvoiceGoods, self).create( vals)
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
                return super(DocumentInvoiceGoods, self).delete(ids)
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
        return self.write(ids, {
                'state': 'draft',
                'deleting':False
                })

    def cancel(self, ids):
        return self.write(ids, {
                'state': 'canceled',
                })

DocumentInvoiceGoods()
