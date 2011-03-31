# -*- encoding: utf-8 -*-

"Document"
from trytond.model import ModelView, ModelSQL, fields
from trytond.tools import safe_eval
import time
from decimal import Decimal, ROUND_HALF_EVEN
import datetime

class DocumentOrder(ModelSQL, ModelView):
    "Documents of order"
    _name='ekd.document.head.order'
    _description=__doc__
    _inherits = {'ekd.document': 'document'}

    document = fields.Many2One('ekd.document', 'Document', required=True,
            ondelete='CASCADE')

    description = fields.Text('Text Order', size=None, required=True)

DocumentOrder()