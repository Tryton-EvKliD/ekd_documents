# -*- coding: utf-8 -*-

"Document"
from trytond.model import ModelView, ModelSQL, fields
from trytond.tools import safe_eval
from decimal import Decimal, ROUND_HALF_EVEN
from trytond.pyson import In, Eval, Not, In, Equal, If, Get, Bool
from trytond.transaction import Transaction
import time
import datetime

class DocumentLineProduct(ModelSQL, ModelView):
    "Document specifications of product"
    _name='ekd.document.line.product'
    _description=__doc__

#    inovice_goods = fields.Many2One('ekd.document.head.invoice_goods', 'Document Head', 
#            ondelete='CASCADE', select=1)
    invoice = fields.Many2One('ekd.document', 'Invoice Head', 
            ondelete='CASCADE', select=1)
    invoice_tax = fields.Many2One('ekd.document.head.invoice_tax', 'Invoice Tax Head', 
            ondelete='CASCADE', select=1)
    parent = fields.Many2One('ekd.document.line.product', 'Parent')
    child = fields.One2Many('ekd.document.line.product', 'parent', 'Childs')
    type = fields.Selection([
            ('line', 'Line'),
            ('subtotal', 'Subtotal'),
            ('title', 'Title'),
            ('comment', 'Comment'),
            ], 'Type line', select=1, required=True)
    type_product = fields.Selection([
            ('fixed_assets', 'Fixed Assets'),
            ('intangible', 'Intangible assets'),
            ('material', 'Material'),
            ('goods', 'Goods'),
            ('service', 'Service'),
            ], 'Type Product',
            states={
                'invisible': Not(Equal(Eval('type'), 'line')),
            })

    product_ref = fields.Reference('Product ref', 'get_product_ref',
            states={
                'invisible': Not(Equal(Eval('type'), 'line')),
            }, on_change=['product_ref', 'description'])

    product = fields.Many2One('product.product', 'Product',
            states={
                'invisible': Not(Equal(Eval('type'), 'line')),
            }, on_change_with=['product_ref'])
    quantity = fields.Float('Quantity',
            digits=(16, Eval('currency_digits', 2)),
            states={
                'invisible': Not(Equal(Eval('type'), 'line')),
                'required': Not(Equal(Eval('type'), 'line')),
            })
    unit = fields.Many2One('product.uom', 'Unit',
            states={
                'required': Bool(Eval('product')),
                'invisible': Not(Equal(Eval('type'), 'line')),
            }, domain=[('category', '=', 
                    (Eval('product'), 'product.default_uom.category'))],
            context={'category': (Eval('product'), 'product.default_uom.category')})
    unit_digits = fields.Function(fields.Integer('Unit Digits', 
            on_change_with=['unit']), 'get_unit_digits')
    description = fields.Text('Description', size=None, required=True)
    unit_price = fields.Numeric('Unit Price', digits=(16, 4),
            states={
                'invisible': Not(Equal(Eval('type'), 'line')),
                'required': Not(Equal(Eval('type'), 'line')),
            })

    type_tax = fields.Selection([
            ('including','Including'),
            ('over_amount','Over Amount')
            ], 'Type Amount')

    tax = fields.One2Many('ekd.document.line.product.tax', 'line', 'Taxes and Excises')
    amount_tax = fields.Function(fields.Numeric('Amount Tax', digits=(16, 2),
            states={
                    'invisible': Not(In(Eval('type'), ['line', 'subtotal'])),
                    }), 'get_amount_tax')

    amount = fields.Numeric('Amount', digits=(16, 2),
             on_change_with=['type', 'quantity', 'unit_price',
                    '_parent_head.currency', 'currency'],
            states={
                    'invisible': Not(In(Eval('type'), ['line', 'subtotal'])),
            })
    currency = fields.Many2One('currency.currency', 'Currency', 
            states={
                'invisible': Not(Equal(Eval('type'), 'line')),
                'required': Not(Equal(Eval('type'), 'line')),
            })
    currency_digits = fields.Function(fields.Integer('Currency Digits', 
            on_change_with=['currency']), 'get_currency_digits')

    state = fields.Selection([
            ('draft', 'Draft'),
            ('open', 'Opened'),
            ('paid', 'Paid'),
            ('part_paid', 'Partial payment'),
            ('to_pay', 'To pay'),
            ('canceled', 'Canceled'),
            ('deleted', 'Deleted'),
            ], 'State', states={
                'invisible': Not(Equal(Eval('type'), 'line')),
            }, readonly=True)

    def __init__(self):
        super(DocumentLineProduct, self).__init__()
        self._rpc.update({
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

        self._order.insert(0, ('state', 'ASC'))

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

    def default_state(self):
        return 'draft'

    def default_type(self):
        return 'line'

    def default_type_product(self):
        return Transaction().context.get('type_product') or 'service'

    def default_quantity(self):
        return 0.0

    def default_unit_price(self):
        return Decimal('0.0')

    def get_product_ref(self):
        dictions_obj = self.pool.get('ir.dictions')
        res = []
        diction_ids = dictions_obj.search([
                    ('model', '=', 'ekd.document.line.product'),
                    ('pole', '=', 'product_ref'),
                    ])
        for diction in dictions_obj.browse(diction_ids):
            res.append([diction.key, diction.value])
        return res

    def get_unit_digits(self, ids, name):
        res = {}
        for line in self.browse(ids):
            if line.unit:
                res[line.id] = line.unit.digits
            else:
                res[line.id] = 2
        return res

    def on_change_with_amount(self, vals):
        currency_obj = self.pool.get('currency.currency')
        if vals.get('type') == 'line':
            currency = vals.get('_parent_head.currency') or vals.get('currency')
            if isinstance(currency, (int, long)) and currency:
                currency = currency_obj.browse(currency)
            amount = Decimal(str(vals.get('quantity') or '0.0')) * \
                    (vals.get('unit_price') or Decimal('0.0'))
            if currency:
                return currency_obj.round(currency, amount)
            return amount
        return Decimal('0.0')

    def on_change_product_ref(self, vals):
        model, model_id = vals.get('product_ref').split(',')
        if model_id != '0':
            model_obj = self.pool.get(model)
            model_rec = model_obj.browse(int(model_id))
            if vals.get('description') and not isinstance(vals.get('description'), unicode):
                description = vals.get('description').decode('utf8')
            else:
                description = vals.get('description')

            if not vals.get('description') and model_rec.description:
                return {'description': model_rec.rec_name+u',\n'+model_rec.description,
                        'unit': model_rec.default_uom.id}
            elif not vals.get('description'):
                return {'description': model_rec.rec_name,
                        'unit': model_rec.default_uom.id}
            elif model_rec.description:
                #if isinstance(model_rec.rec_name, unicode):
                #    pass
                #else:
                #    raise Exception(model_rec.rec_name)
                #if isinstance(vals.get('description'), unicode):
                #    pass
                #else:
                #    raise Exception(vals.get('description'))
                return {'description': description + u',\n' 
                                       + model_rec.rec_name + u',\n'
                                       + model_rec.description,
                        'unit': model_rec.default_uom.id}
            else:
                return {'description': description + u',\n'
                                       + model_rec.rec_name,
                        'unit': model_rec.default_uom.id}
            
        return {}

    def on_change_with_unit_digits(self, vals):
        uom_obj = self.pool.get('product.uom')
        if vals.get('unit'):
            uom = uom_obj.browse(vals['unit'])
            return uom.digits
        return 2

    def on_change_with_currency_digits(self, vals):
        currency_obj = self.pool.get('currency.currency')
        if vals.get('currency'):
            currency = currency_obj.browse(vals['currency'])
            return currency.digits
        return 2

    def get_currency_digits(self, ids, name):
        res = {}
        for line in self.browse(ids):
            res[line.id] = line.currency and line.currency.digits or 2
        return res

    def get_amount_tax(self, ids, name):
        res = {}.fromkeys(ids, Decimal('0.0'))
        for line in self.browse(ids):
            for tax in line.tax:
                res[line.id] += tax.amount

        return res

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

    def draft(self, ids):
        self.write(ids, {
                    'state': 'draft',
                    'deleting':False
                    })

    def cancel(self, ids):
        return self.write(ids, {
                'state': 'canceled',
                })

DocumentLineProduct()

class DocumentLineProductTax(ModelSQL, ModelView):
    "Document specifications of product"
    _name='ekd.document.line.product.tax'
    _description=__doc__

    line = fields.Many2One('ekd.document.line.product', 'Line', ondelete='CASCADE')
    percentage = fields.Numeric('Percentage Tax', digits=(3, 0))
    amount = fields.Numeric('Amount Tax', digits=(16, 2))
    type_tax = fields.Selection([
            ('vat','VAT'),
            ('sales_tax','Sales Tax'),
            ('excise','Excise'),
            ], 'Type Tax')

    type_compute = fields.Selection([
            ('including','Including'),
            ('over_amount','Over Amount')
            ], 'Type Compute')

    def default_tax(self):
        pass

    def persentage(self):
        pass

    def type_tax(self):
        return 'vat'

    def type_tax(self):
        return 'including'

DocumentLineProductTax()
