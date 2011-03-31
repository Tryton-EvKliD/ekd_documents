# -*- coding: utf-8 -*-
"Document"

_STATE_CASH=[
            ('draft', 'Draft'),
            ('payment', 'Payment'),
            ('posted', 'Posted'),
            ('error', 'Error'),
            ('deleted', 'Deleted'),
            ]

_STATE_STATEMENT=[
                ('draft', 'Draft'),
                ('import', 'Import'),
                ('posted', 'Posted'),
                ('error', 'Error'),
                ('deleted', 'Deleted'),
                ]

_STATE_BANK=[
                ('draft', 'Draft'),
                ('in_bank', 'In bank'),
                ('canceled', 'Canceled'),
                ('posted', 'Posted'),
                ('error', 'Error'),
                ('deleted', 'Deleted'),
                ]

_STATE_INVOICE=[
            ('draft', 'Draft'),
            ('paid', 'Paid'),
            ('part_paid', 'Partial payment'),
            ('to_pay', 'To pay'),
            ('posted', 'Posted'),
            ('printed', 'Printed'),
            ('sended', 'Sended'),
            ('canceled', 'Canceled'),
            ('obtained', 'Obtained'),
            ('delivered', 'Delivered'),
            ('deleted', 'Deleted'),
            ]

_STATE_INVOICE_GOODS=[
            ('draft', 'Draft'),
            ('part_paid', 'Partial payment'),
            ('paid', 'Paid'),
            ('to_pay', 'To pay'),
            ('posted', 'Posted'),
            ('printed', 'Printed'),
            ('sended', 'Sended'),
            ('canceled', 'Canceled'),
            ('obtained', 'Obtained'),
            ('delivered', 'Delivered'),
            ('deleted', 'Deleted'),
                ]

_STATE_INVOICE_TAX=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('canceled', 'Canceled'),
            ]

_STATE_REQUEST=[
                ('empty', 'Empty'),
                ('draft', 'Draft'),
                ('request', 'Request'),
                ('confirmed', 'Confirmed'),
                ('payment', 'Payment'),
                ('paid', 'Paid'),
                ('partially', 'Partially'),
                ('done', 'Done'),
                ('deleted', 'Deleted'),
                ]

_STATES_FULL=[]

for line in _STATE_CASH+\
            _STATE_STATEMENT+\
            _STATE_BANK+\
            _STATE_INVOICE+\
            _STATE_INVOICE_TAX+\
            _STATE_INVOICE_GOODS+\
            _STATE_REQUEST:
    if line not in _STATES_FULL:
        _STATES_FULL.append(line)
