# -*- coding: utf-8 -*-
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
{
    'name': 'Main class documents',
    'name_ru_RU': 'Основной класс объектов Документы + Документы',
    'version': '1.8.0',
    'author': 'Dmitry Klimanov',
    'email': 'k-dmitry2@narod.ru',
    'website': 'http://www.delfi2000.ru/',
    'description': '''Documents:
''',
    'description_ru_RU': '''модуль документы:
    Основной класс для все документов в системе
    реализует общие поля и функции для всех документов.
    +
    Кассовые документы - ПКО, РКО. - готова
    Платежные банковские документы - П/П. - реализуется
    Счет - готова
    Счет-фактура - тестируется
    Накладная - реализуется
    Авансовый отчет - планируется
    Доверенность - планируется
''',
    'depends': [
        'ir',
        'res',
        'currency',
        'ekd_system',
        'ekd_product',
        'ekd_party',
        'ekd_company',
    ],
    'xml': [
        'xml/ekd_system.xml',
        'xml/ekd_documents_view.xml',
        'xml/ekd_documents_stage_view.xml',
        'xml/ekd_template.xml',
        'xml/ekd_order_view.xml',
        'xml/ekd_letter_view.xml',
        'xml/ekd_bank_view.xml',
#        'xml/ekd_bank_import.xml',
        'xml/ekd_cash_view.xml',
#        'xml/ekd_product_view.xml',
        'xml/ekd_invoice_view.xml',
        'xml/ekd_invoice_tax_view.xml',
        'xml/ekd_invoice_goods_view.xml',
        'xml/ekd_payment_term_view.xml',
#        'xml/ekd_payment_view.xml',
        'xml/ekd_request_view.xml',
        'xml/ekd_advance_view.xml',
        'xml/ekd_wizard_view.xml',
        'xml/ekd_print.xml',
    ],
    'translation': [
        'ru_RU.csv',
    ],
}
