# -*- encoding: utf-8 -*-

"Document"
from trytond.model import ModelView, ModelSQL, fields
from trytond.tools import safe_eval
import time
from decimal import Decimal, ROUND_HALF_EVEN
import datetime

class DocumentLetter(ModelSQL, ModelView):
    "Documents of letter"
    _name='ekd.document.head.letter'
    _description=__doc__
    _inherits = {'ekd.document': 'document'}

    document = fields.Many2One('ekd.document', 'Document', required=True,
            ondelete='CASCADE')
    description = fields.Text('Text Letter', size=None, required=True)

DocumentLetter()