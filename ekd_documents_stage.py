# -*- coding: utf-8 -*- 
"Document Stage"
from trytond.model import ModelView, ModelSQL, fields
from trytond.transaction import Transaction

class DocumentTemplateStage(ModelSQL, ModelView):
    "Document Template"
    _name='ekd.document.template.stage'
    _description=__doc__
    _order_name = "sequence"

    template = fields.Many2One('ekd.document.template', 'Template')
    name = fields.Char('Name', size=128)
    shortcut = fields.Char('ShortCut', size=32)
    sequence = fields.Integer('Sequence', help="Change with *10")
    date_start = fields.Date('Date Start')
    date_end = fields.Date('Date end')
    code_call = fields.Char('Code Call')
    active = fields.Boolean('Active')

    def default_active(self):
        return True

DocumentTemplateStage()

class Document(ModelSQL, ModelView):
    _name='ekd.document.template'

    stages = fields.One2Many('ekd.document.template.stage', 'template', 'Stages')

Document()

class Document(ModelSQL, ModelView):
    _name='ekd.document'

    stage = fields.Many2One('ekd.document.template.stage', 'Stage')

Document()
