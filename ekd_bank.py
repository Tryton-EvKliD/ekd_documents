# -*- coding: utf-8 -*-

"Document"
from trytond.model import ModelStorage, ModelView, ModelSQL, fields
from trytond.tools import safe_eval
from trytond.transaction import Transaction
from decimal import Decimal, ROUND_HALF_EVEN
from trytond.pyson import In, Eval, Not, In, Equal, If, Get, Bool
from ekd_state_document import _STATE_STATEMENT, _STATE_BANK
import time
import datetime
import base64
import logging

HAS_CODECS = False
NAME_CODECS = [('', '')]

try:
    import encodings
    HAS_CODECS = True
    test_code=[]
    for codec in encodings.aliases.aliases.values():
        if codec not in test_code:
            NAME_CODECS.append((codec,codec))
            test_code.append(codec)
except ImportError:
    logging.getLogger('ekd_document_ru').warning(
            'Unable to import codecs. Encode file disabled.')

_STATES = {
    'readonly': In(Eval('state'), ['posted', 'in_bank']),
        }
_DEPENDS = ['state']

_pole_delimiter=','
_key_delimiter='='

class DocumentBankStatement(ModelSQL, ModelView):
    "Bank Statement"
    _name='ekd.document.bank.statement'
    _description=__doc__
    _inherits = {'ekd.document': 'document'}

    document = fields.Many2One('ekd.document', 'Document', required=True,
            ondelete='CASCADE')

    template_bank = fields.Function(fields.Many2One('ekd.document.template', 'Document Name',
            states=_STATES, depends=_DEPENDS, help="Template documents",
            domain=[('type_account','=','bank_documents')],
            on_change=['type_transaction', 'template_bank'], order_field="template"),
            'get_fields', setter='set_fields', searcher='template_search')
    number_doc = fields.Function(fields.Char('Number Document', states=_STATES, depends=_DEPENDS),
            'get_fields', setter='set_fields', searcher='template_search')
    date_start = fields.Date('Date Start')
    date_end = fields.Date('Date End')
    from_bank = fields.Many2One('ekd.party.bank_account', 'From Bank Account',
            states=_STATES, depends=['state', 'from_party'],
            domain=[('party', '=', Eval('from_party'))])
    balance_start = fields.Numeric('Balance Start', digits=(16, 2))
    turnover_income = fields.Numeric('Income', digits=(16, 2))
    turnover_expense = fields.Numeric('Expense', digits=(16, 2))
    balance_end = fields.Numeric('Balance End', digits=(16, 2))
    state_doc = fields.Function(fields.Selection(_STATE_STATEMENT, required=True, readonly=True, string='State'),'get_fields', setter='set_fields')

    documents = fields.One2Many('ekd.document.bank', 'child', 'Lines imported')


DocumentBankStatement()

class DocumentBank(ModelSQL, ModelView):
    "Documents of bank"
    _name='ekd.document.head.bank'
    _description=__doc__
    _inherits = {'ekd.document': 'document'}

    document = fields.Many2One('ekd.document', 'Document', required=True,
            ondelete='CASCADE')

    template_bank = fields.Function(fields.Many2One('ekd.document.template', 'Document Name',
            states=_STATES, depends=_DEPENDS, help="Template documents",
            domain=[('type_account','=','bank_documents'), ('code_call','=',Eval('type_transaction'))],
            on_change=['type_transaction', 'template_bank'], order_field="template"), 
            'get_fields', setter='set_fields', searcher='template_search')

    number_doc = fields.Function(fields.Char('Number Document', states=_STATES, depends=_DEPENDS),
            'get_fields', setter='set_fields', searcher='template_search')

#    from_party_doc = fields.Function('get_fields', type="many2one", relation='party.party', setter='set_fields', fnct_search='template_search',
#                        string='From Party', states=_STATES, depends=_DEPENDS)
#    to_party_doc = fields.Function('get_fields', type="many2one", relation='party.party', setter='set_fields', fnct_search='template_search',
#                        string='To Party', states=_STATES, depends=_DEPENDS)

    type_transaction = fields.Selection([
                    ('income_bank','Income'),
                    ('income_bank_tax','Income_tax'),
                    ('expense_bank','Expense'),
                    ('expense_bank_tax','Expense_tax'),
                    ], 'Type Transaction')

    from_bank = fields.Many2One('ekd.party.bank_account', 'From Bank Account',
                    states=_STATES, domain=[('party', '=', Eval('from_party'))])

    to_bank = fields.Many2One('ekd.party.bank_account', 'To Bank Account',
                    domain=[('party', '=', Eval('to_party'))])
    document_base = fields.Many2One('ekd.document', 'Document Base')
    document_base_ref = fields.Reference('Document Base', selection='documents_get',
                    states=_STATES, depends=_DEPENDS,
                    on_change=['type_transaction', 'document_base_ref'])

    type_reference = fields.Selection([
                ('electron', 'Electron'),
                ('mail', 'Mail'),
                ('cw', 'CW'),
                ('urgetly', 'Urgently'),
                ], string='Type of payment')
    percent_vat = fields.Selection([
                ('18%', '18%'),
                ('10%', '10%'),
                ('0%', '0%'),
                ('not_included', 'Not included'),
                ], string='Percentage of VAT')

    content = fields.Function(fields.Text('Content payment', help=u'Назначение платежа'), 'get_fields', setter='set_fields_add')
    add_options = fields.Text('Add options')
    pole_type = fields.Function(fields.Char('Payment Type', help=u'Вид оплаты'),'get_fields', setter='set_fields_add')
    pole_maturity = fields.Function(fields.Date('Maturity', help=u'Срок платежа'),'get_fields', setter='set_fields_add')
    pole_detail = fields.Function(fields.Char('Details of payment', help=u'Назначение платежа'),'get_fields', setter='set_fields_add')
    pole_order = fields.Function(fields.Char('Order of payments',
            help=u'Очер.плат.—очередность платежа от 1 до 6.\n'\
            u'1-По исполнительным документам: возмещение вреда жизни и здоровью, алименты\n'\
            u'2-По исполнительным документам: оплата труда, выплата выходного пособия, выплата авторского вознаграждения\n'\
            u'3-Оплата труда, отчисления в Пенсионный фонд, Фонд социального страхования, фонды обязательного медицинского страхования\n'\
            u'4-Платежи в бюджет и внебюджетные фонды (кроме перечисленных в очередности 3)\n'\
            u'5-Другие платежи по исполнительным документам, не попадающие под очередность 1 и 2\n'\
            u'6-Другие платежи в порядке календарной очередности'
            ),'get_fields', setter='set_fields_add')
    pole_code = fields.Function(fields.Char('Code', help=u'Код'),'get_fields', setter='set_fields_add')
    pole_reserve = fields.Function(fields.Char('Backing field', help=u'Резевное поле'),'get_fields', setter='set_fields_add')
    status_payer_tax = fields.Function(fields.Char('Status Payer',
            help=u'01-Плательщик налогов (сборов) — юридическое лицо\n'\
            u'02-Налоговый агент\n'\
            u'03-Сборщик налогов и сборов\n'\
            u'04-Налоговый орган\n'\
            u'05-Территориальные органы Федеральной службы судебных приставов\n'\
            u'06-Участник внешнеэкономической деятельности\n'\
            u'07-Таможенный орган\n'\
            u'08-Плательщик иных платежей в бюджетную систему, кроме платежей, управляемых налоговыми органами\n'\
            u'09-Плательщик налогов (сборов) — индивидуальный предприниматель\n'\
            u'10-Плательщик налогов (сборов) — частный нотариус\n'\
            u'11-Плательщик налогов (сборов) — адвокат, учредивший адвокатский кабинет\n'\
            u'12-Плательщик налогов (сборов) — глава крестьянского (фермерского) хозяйства\n'\
            u'13-Плательщик налогов (сборов) — иное физическое лицо — владелец счета\n'\
            u'14-Плательщик страховых взносов, производящий выплаты физическим лицам\n'\
            u'15-Кредитные организации, оформляющие расчетные документы на перечисление налогов, сборов и иных платежей в бюджет, уплачиваемых физическими лицами без открытия банковского счета'
            ),'get_fields', setter='set_fields_add')
    kbk_indicator = fields.Function(fields.Char('KBK', help=u'КБК — код классификации доходов бюджетов Российской Федерации\n'\
                     u' из 20 цифр Заполняется только для бюджетных платежей'),'get_fields', setter='set_fields_add')
    okato_indicator = fields.Function(fields.Char('OKATO', help=u'ОКАТО'),'get_fields', setter='set_fields_add')
    tax_period = fields.Function(fields.Char('Tax period', help=
            u'Налоговый период — показатель налогового периода для периодического платежа\n'\
            u' или определенная дата Указывается в формате «XX.NN.YYYY». Все возможные значения\n'\
            u'элементов показателя налогового периода приведены в таблице ниже\n'\
            u'(коды декадных платежей исключены с 2005 года).\n'\
            u'                           XX	NN	                YYYY\n'\
            u'Месячный платеж	        МС	месяц (01–12)	        год (4 цифры)\n'\
            u'Квартальный платеж	        КВ	номер квартала (01–04)	год (4 цифры)\n'\
            u'Полугодовой платеж	        ПЛ	номер полугодия (01–02)	год (4 цифры)\n'\
            u'Годовой платеж	        ГД	00 (два ноля)	        год (4 цифры)\n'\
            u'Платеж по определ. дате  число (01–31)	месяц (01–12)	год (4 цифры)'
            ),'get_fields', setter='set_fields_add')

    payment_details_tax = fields.Function(fields.Char('Payment Details',
                help=u'Основание платежа — код из двух букв, отражающий основание платежа в соответствии с таблицей\n'\
                u'ТП-Платежи текущего года без нарушения сроков\n'\
               	u'ЗД-Добровольное погашение задолженности по истекшим налоговым периодам без требования от налогового органа\n'\
               	u'БФ-Текущие платежи физических лиц — клиентов банка со своего банковского счета\n'\
               	u'ТР-Погашение задолженности по требованию налогового органа\n'\
               	u'РС-Погашение рассроченной задолженности\n'\
               	u'ОТ-Погашение отсроченной задолженности\n'\
               	u'РТ-Погашение реструктурируемой задолженности\n'\
               	u'ВУ-Погашение отсроченной задолженности в связи с введением внешнего управления\n'\
               	u'ПР-Погашение задолженности, приостановленной ко взысканию\n'\
               	u'АП-Погашение задолженности по акту проверки\n'\
               	u'АР-Погашение задолженности по исполнительному документу'
               	),'get_fields', setter='set_fields_add')
    kind_payment_tax = fields.Function(fields.Char('Payment Details',
                help=u'Тип платежа — двухбуквенный показатель типа платежа в"\
                u" соответствии с таблицей ниже. Существует взаимосвязь между типом платежа и КБК.\n'\
               	u'НС-Уплата налога или сбора\n'\
               	u'ПЛ-Уплата платежа\n'\
               	u'ГП-Уплата пошлины\n'\
               	u'ВЗ-Уплата взноса\n'\
               	u'АВ-Уплата аванса или предоплата\n'\
               	u'ПЕ-Уплата пени\n'\
               	u'ПЦ-Уплата процентов\n'\
               	u'СА-Налоговые санкции, установленные Налоговым кодексом РФ\n'\
               	u'АШ-Административные штрафы\n'\
               	u'ИШ-Иные штрафы, установленные законодательными или иными нормативными актами'
               	),'get_fields', setter='set_fields_add')

    number_doc_base_tax = fields.Function(fields.Char('Number and date',
                help=u"Номер документа-основания и его дата — номер и дата документа, "\
                u"на основании которого производится уплата налога (сбора). Эти два поля "\
                u"зависят от значения полей «статус плательщика» и «основание платежа»."
                ),'get_fields', setter='set_fields_add')

#    file_import = fields.Many2One('ekd.document.bank.import', 'Ref file Import')
    state_doc = fields.Function(fields.Selection(_STATE_BANK, 'State', required=True, readonly=True, ),'get_fields', setter='set_fields')

    lines_payment = fields.One2Many('ekd.document.line.payment', 'doc_payment', 'Line Spec Amounts')
    deleting = fields.Boolean('Flag deleting', readonly=True)

    def __init__(self):
        super(DocumentBank, self).__init__()
        self._rpc.update({
            'button_post': True,
            'button_bank': True,
            'button_draft': True,
            'button_cancel': True,
            'button_restore': True,
            })

        self._order.insert(0, ('date_document', 'ASC'))
        self._order.insert(1, ('template', 'ASC'))

    def default_state_doc(self):
        return Transaction().context.get('state') or 'draft'

    def default_pole_maturity(self):
        return Transaction().context.get('pole_maturity') or datetime.datetime.now()

    def default_document_base(self):
        return Transaction().context.get('document_base') or False

    def default_document_base_ref(self):
        return Transaction().context.get('document_base_ref') or False

    def default_bank_account(self):
        return Transaction().context.get('bank_account') or False

    def default_from_party_doc(self):
        return Transaction().context.get('from_party') or False

    def default_to_party_doc(self):
        return Transaction().context.get('to_party') or False

    def default_amount(self):
        return Transaction().context.get('amount') or Decimal('0.0')

    def default_type_transaction(self):
        return Transaction().context.get('type_transaction') or 'expense'

    def default_currency_digits(self):
        return 2

    def default_second_currency_digits(self):
        return 2

    def default_company(self):
        return Transaction().context.get('company') or False

    def set_fields_add(self, ids, name, value):
        if isinstance(ids, list):
            ids = ids[0]
        if not value:
            return
        all_add_options = {}
        document = self.browse(ids)
        if document.add_options:
            all_add_options = safe_eval(document.add_options, {
                    'Decimal': Decimal,
                    'datetime': datetime})

        if name == 'pole_order':
            all_add_options['pole_order'] = value
        elif name == 'pole_type':
            all_add_options['pole_type'] = value
        elif name == 'pole_maturity':
            all_add_options['pole_maturity'] = value
        elif name == 'pole_detail':
            all_add_options['pole_detail'] = value
        elif name == 'pole_code':
            all_add_options['pole_code'] = value
        elif name == 'pole_reserve':
            all_add_options['pole_reserve'] = value
        elif name == 'kind_payment_tax':
            all_add_options['kind_payment_tax'] = value
        elif name == 'status_payer_tax':
            all_add_options['status_payer_tax'] = value
        elif name == 'kbk_indicator':
            all_add_options['kbk_indicator'] = value
        elif name == 'okato_indicator':
            all_add_options['okato_indicator'] = value
        elif name == 'payment_details_tax':
            all_add_options['payment_details_tax'] = value
        elif name == 'number_doc_base_tax':
            all_add_options['number_doc_base_tax'] = value
        elif name == 'tax_period':
            all_add_options['tax_period'] = value

        self.write(ids, {'add_options': str(all_add_options)})

    def get_fields(self, ids, names):
        if not ids:
            return {}
        res={}
        for line in self.browse(ids):
            all_add_options = False
            if line.add_options:
                all_add_options = safe_eval(line.add_options,{
                    'Decimal': Decimal,
                    'datetime': datetime})
            for name in names:
                res.setdefault(name, {})
                res[name].setdefault(line.id, False)
                if name == 'number_doc':
                    if name == 'number_doc':
                        if line.type_transaction in ('expense', 'expense_tax') :
                            res[name][line.id] = line.number_our
                        else:
                            res[name][line.id] = line.number_in
                elif name == 'state_doc':
                    res[name][line.id] = line.state
                elif name == 'from_party_doc':
                    res[name][line.id] = line.from_party.id
                elif name == 'to_party_doc':
                    res[name][line.id] = line.to_party.id
                elif name == 'template_bank':
                    res[name][line.id] = line.template.id
                elif name == 'content':
                    res[name][line.id] = line.note
                elif all_add_options and name == 'pole_order':
                    res[name][line.id] = all_add_options.get('pole_order')
                elif all_add_options and name == 'pole_type':
                    res[name][line.id] = all_add_options.get('pole_type')
                elif all_add_options and name == 'pole_maturity':
                    res[name][line.id] = all_add_options.get('pole_maturity')
                elif all_add_options and name == 'pole_detail':
                    res[name][line.id] = all_add_options.get('pole_detail')
                elif all_add_options and name == 'pole_code':
                    res[name][line.id] = all_add_options.get('pole_code')
                elif all_add_options and name == 'pole_reserve':
                    res[name][line.id] = all_add_options.get('pole_reserve')
                elif all_add_options and name == 'kind_payment_tax':
                    res[name][line.id] = all_add_options.get('kind_payment_tax')
                elif all_add_options and name == 'status_payer_tax':
                    res[name][line.id] = all_add_options.get('status_payer_tax')
                elif all_add_options and name == 'kbk_indicator':
                    res[name][line.id] = all_add_options.get('kbk_indicator')
                elif all_add_options and name == 'okato_indicator':
                    res[name][line.id] = all_add_options.get('okato_indicator')
                elif all_add_options and name == 'payment_details_tax':
                    res[name][line.id] = all_add_options.get('payment_details_tax')
                elif all_add_options and name == 'number_doc_base_tax':
                    res[name][line.id] = all_add_options.get('number_doc_base_tax')
                elif all_add_options and name == 'tax_period':
                    res[name][line.id] = all_add_options.get('tax_period')
        return res

    def set_fields(self, ids, name, value):
        if isinstance(ids, list):
            ids = ids[0]
        if not value:
            return
        document = self.browse(ids)
        if name == 'state_doc':
            self.write(ids, {'state':value, })
        elif name == 'template_bank':
            self.write(ids, { 'template': value, })
        elif name == 'number_doc':
            if name == 'number_doc':
                if document.type_transaction in ('expense', 'expense_tax'):
                    self.write(ids, { 'number_our': value, })
                else:
                    self.write(ids, { 'number_in': value, })
        elif name == 'content':
            self.write(ids, { 'note': value, })
        elif name == 'from_party_doc':
            self.write(ids, { 'from_party': value, })
        elif name == 'to_party_doc':
            self.write(ids, { 'to_party': value, })

    def get_template_select(self, ):
        template_obj = self.pool.get('ekd.document.template')
        template_ids = template_obj.search(['type_account','=','bank_documents'])
        res=[]
        for template in template_obj.browse(template_ids):
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

    def get_rec_name(self, ids, name):
        if not ids:
            return {}
        return self.pool.get('ekd.document').get_rec_name( ids, name)

    def documents_get(self):
        dictions_obj = self.pool.get('ir.dictions')
        res = []
        diction_ids = dictions_obj.search( [
                                ('model', '=', 'ekd.document.bank'),
                                ('pole', '=', 'document_base_ref'),
                                ])
        if diction_ids:
            for diction in dictions_obj.browse( diction_ids):
                res.append([diction.key, diction.value])
        res.append(["", ""])
        return res

    def get_currency_digits(self, ids, name):
        assert name in ('currency_digits'), 'Invalid name %s' % (name)
        res={}.fromkeys(ids, 2)
        for document in self.browse( ids):
            if document.bank_account:
                res[document.id] = document.bank_account.currency_digits
        return res

    def on_change_document_base_ref(self, values):
        if not values.get('document_base_ref'):
            return {}
        res={}
        model, model_ids = values.get('document_base_ref').split(',')
        if model and model_ids != '0':
            model_obj = self.pool.get(str(model))
            model_id = model_obj.browse( int(model_ids))
            res['amount'] = model_id.amount
            res['child'] = model_ids
            res['from_party'] = model_id.from_party.id
            res['amount'] = model_id.amount
            res['parent'] = model_id.id
            res['to_party'] = model_id.to_party.id
        return res

    def on_change_template_bank(self,  values):
        if not values.get('template_bank'):
            return {}
        res={}
        template_obj = self.pool.get('ekd.document.template')
        template_ids = template_obj.browse( int(values.get('template_bank')))
        values['type_transaction'] = template_ids.code_call
        if values.get('document_base_ref'):
            model, model_ids = values.get('document_base_ref').split(',')
            if model and model_ids != '0':
                model_obj = self.pool.get(str(model))
                model_id = model_obj.browse( int(model_ids))
                res['amount']= model_id.amount
                res['from_party']=model_id.from_party.id
                res['to_party']=model_id.to_party.id
        return res


    def button_post(self, ids):
        return self.post(ids)

    def button_cancel(self, ids):
        return self.cancel(ids)

    def button_draft(self, ids):
        return self.draft(ids)

    def button_bank(self, ids):
        return self.draft(ids)

    def button_restore(self, ids):
        return self.in_bank(ids)

    def post(self, ids):
        self.write( document.id, {
                'number_our': reference,
                'state': 'posted',
                'post_date': date_obj.today( ),
                })

    def draft(self, ids):
        self.write( ids, {
                'state': 'draft',
                })
        return

    def in_bank(self, ids):
        self.write( ids, {
                'state': 'in_bank',
                })
        return

    def cancel(self,  ids):
        self.write( ids, {
                'state': 'canceled',
                })
        return

    def post_move(self,  ids, post_value):
        pass

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
        new_id = super(DocumentBank, self).create(vals)
        bank = self.browse( new_id)
        new_id = bank.document.id
        cr = Transaction().cursor
        cr.execute('UPDATE "' + self._table + '" SET id = %s '\
                        'WHERE id = %s', (bank.document.id, bank.id))
        ModelStorage.delete(self,  bank.id)
        self.write( new_id, later)
        res = self.browse( new_id)
        return res.id

    def delete(self, ids):
        cr = Transaction().cursor
        for document in self.browse(ids):
            if document.state == 'deleted' and document.deleting:
                cr.execute('DELETE FROM "documents_document_bank" WHERE id=%s', (document.id,))
                cr.execute('DELETE FROM "documents_document" WHERE id=%s', (document.id,))
                cr.execute('DELETE FROM "documents_payment_line" WHERE doc_payment=%s', (document.id,))
            else:
                self.write(document.id, {'state': 'deleted', 'deleting':True})
        return True

DocumentBank()
