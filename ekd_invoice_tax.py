# -*- coding: utf-8 -*-
#NOTE: Документы - Счета фактуры
"Document Invoice Tax"
from trytond.model import ModelStorage, ModelView, ModelSQL, fields
from trytond.report import Report
from pytils import numeral
from trytond.tools import safe_eval
from trytond.pyson import In, If, Get, Eval, Not, Equal, Bool, Or, And
from trytond.transaction import Transaction
import time
from decimal import Decimal, ROUND_HALF_EVEN
from ekd_state_document import _STATE_INVOICE_TAX
import datetime

class DocumentInvoiceTax(ModelSQL, ModelView):
    "Documents (Invoice Tax) "
    _name='ekd.document.head.invoice_tax'
    _description=__doc__
    _inherits = {'ekd.document': 'document'}

    document = fields.Many2One('ekd.document', 'Document', required=True,
            ondelete='CASCADE')

    direct_document = fields.Selection([
                ('invoice_tax_output', 'For Customer'),
                ('invoice_tax_input', 'From Supplier'),
                ], 'Direct Document')

    template_invoice = fields.Function(fields.Many2One('ekd.document.template',
                'Name',
                domain=[('type_account', '=', Eval('direct_document', 
                        Get(Eval('context', {}), 'direct_document')))]
                ), 'get_fields', setter='set_fields')
    number_doc = fields.Function(fields.Char('Number',
                states={'invisible': And(Not(Bool(Eval('number_doc'))),
                    Not(Equal(Eval('direct_document',''),'invoice_tax_input')))}),
                'get_fields', setter='set_fields', searcher='template_search')
    from_to_party = fields.Function(fields.Many2One('party.party', 
                'Party'), 'get_fields', setter='set_fields')
    shipper = fields.Many2One('party.party', 'Shipper',
                states={'invisible': Eval('as_shipper', True)})
    consignee = fields.Many2One('party.party', 'Consignee',
                states={'invisible': Eval('as_consignee', True)})

    amount_doc = fields.Function(fields.Numeric('Amount', digits=(16, Eval('currency_digits', 2))), 
                'get_fields', setter='set_fields')
    amount_tax = fields.Function(fields.Numeric('Amount Tax', digits=(16, Eval('currency_digits', 2))), 
                'get_fields')
    currency = fields.Many2One('currency.currency', 'Currency')
    currency_digits = fields.Function(fields.Integer('Currency Digits', on_change_with=['currency']),'get_currency_digits')
    type_tax = fields.Selection([
            ('not_vat','Not VAT'),
            ('including','Including'),
            ('over_amount','Over Amount')
            ], 'Type Compute Tax')
    lines = fields.One2Many('ekd.document.line.product', 'invoice_tax', 'Lines')
    state_doc = fields.Selection(_STATE_INVOICE_TAX, 'State', readonly=True)
    as_shipper = fields.Boolean('As Shipper')
    as_consignee = fields.Boolean('As Consignee')

    deleting = fields.Boolean('Flag deleting', readonly=True)

    def __init__(self):
        super(DocumentInvoiceTax, self).__init__()
        self._rpc.update({
            'button_add_number': True,
            'button_draft': True,
            'button_post': True,
            'button_cancel': True,
            'button_restore': True,
            })

    def default_state(self):
        return 'draft'

    def default_from_to_party_doc(self):
        return Transaction().context.get('from_to_party') or False

    def default_direct_document(self):
        return Transaction().context.get('direct_document') or 'invoice_tax_output'

    def default_as_shipper(self):
        return True

    def default_as_consignee(self):
        return True

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

    def default_company(self):
        return Transaction().context.get('company') or False

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

    def get_currency_digits(self,  ids, name):
        res = {}
        for line in self.browse( ids):
            res[line.id] = line.currency and line.currency.digits or 2
        return res

    def get_rec_name(self,  ids, name):
        if not ids:
            return {}
        return self.pool.get('ekd.document').get_rec_name( ids, name)

    def get_fields(self,  ids, names):
        if not ids:
            return {}
        res={}
        for line in self.browse( ids):
            for name in names:
                res.setdefault(name, {})
                res[name].setdefault(line.id, False)
                if name == 'number_doc':
                    if line.direct_document == 'invoice_tax_output':
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
                        if line.direct_document == 'invoice_tax_input' :
                            res[name][line.id] = line.from_party.id
                        else:
                            res[name][line.id] = line.to_party.id
                elif name == 'template_invoice':
                        res[name][line.id] = line.template.id
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
            if document.direct_document == 'invoice_tax_output':
                self.write( ids, { 'number_our': value, })
            else:
                self.write( ids, { 'number_in': value, })
        elif name == 'amount_doc':
            self.write( ids, { 'amount': value, })
        elif name == 'from_party_doc':
            if document.direct_document == 'invoice_tax_input':
                self.write( ids, { 'from_party': value})
            else:
                self.write( ids, { 'to_party': value})

    def documents_base_get(self):
        dictions_obj = self.pool.get('ir.dictions')
        res = []
        diction_ids = dictions_obj.search( [
                                ('model', '=', self._name),
                                ('pole', '=', 'document_base'),
                                ])
        if diction_ids:
            for diction in dictions_obj.browse( diction_ids):
                res.append([diction.key, diction.value])
        return res

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
        new_id = super(DocumentInvoiceTax, self).create(vals)
        invoice_tax = self.browse( new_id)
        new_id = invoice_tax.document.id
        cr = Transaction().cursor
        cr.execute('UPDATE "' + self._table + '" SET id = %s '\
                        'WHERE id = %s', (invoice_tax.document.id, invoice_tax.id))
        ModelStorage.delete(self, invoice_tax.id)
        self.write(new_id, later)
        res = self.browse(new_id)
        return res.id

    def delete(self, ids):
        cr = Transaction().cursor
        for document in self.browse(ids):
            if document.state == 'deleted' and document.deleting:
                return super(DocumentInvoiceTax, self).delete(ids)
                #cr.execute('DELETE FROM "documents_document_invoice" WHERE id=%s', (document.id,))
                #cr.execute('DELETE FROM "documents_document" WHERE id=%s', (document.id,))
            else:
                self.write(document.id, {'state': 'deleted', 'deleting':True})
        return True

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
                    lines_new.setdefault('add', []).append(line_new.read(line_new.id, field_import))
            return {
                'from_to_party': model_line.from_to_party.id,
                'parent': int(model_id),
                'lines':lines_new,
                    }
        else:
            return {
                'from_to_party': model_line.from_to_party.id,
                'parent': int(model_id),
                    }

    def button_add_number(self, ids):
        return self.new_number(ids)

    def button_post(self, ids):
        return self.post(ids)

    def button_send(self, ids):
        return self.send(ids)

    def button_print(self, ids):
        return self.print_document(ids)

    def button_cancel(self, ids):
        return self.cancel(ids)

    def button_draft(self, ids):
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

DocumentInvoiceTax()

class DocumentInvoiceTaxPrint(Report):
    _name='ekd.document.print.invoice_tax.output'

    def parse(self, report, objects, datas, localcontext={}):
        user = self.pool.get('res.user').browse(Transaction().user)
        localcontext['company'] = user.company
        localcontext['numeral'] = numeral
        res = super(DocumentInvoiceTaxPrint, self).parse(report, objects, datas, localcontext=localcontext)
        return res

DocumentInvoiceTaxPrint()
