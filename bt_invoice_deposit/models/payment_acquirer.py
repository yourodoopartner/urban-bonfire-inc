# coding: utf-8

import datetime

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    
    invoice_deposit = fields.Boolean('Invoice Deposit', copy=False)
    
    
    def _post_process_after_done(self):
        self._reconcile_after_transaction_done()
        self._log_payment_transaction_received()
        self.write({'is_processed': True})
        for trans in self:
            if trans.payment_id and trans.invoice_deposit:
                name = self.env['ir.sequence'].next_by_code('payment.deposit', sequence_date=trans.payment_id.payment_date)
                vals = {
                    'name': name,
                    'partner_id': trans.partner_id and trans.partner_id.id or False,
                    'invoice_id': trans.invoice_ids and trans.invoice_ids[0].id or False,
                    'payment_date': trans.payment_id.payment_date,
                    'payment_amount': self.amount,
                    'payment_id': trans.payment_id.id,
                    'move_id': trans.payment_id.move_line_ids[0].move_id.id
                    }
                deposit = self.env['bt.payment.deposit'].create(vals)
                trans.invoice_ids.deposit_exist = True

        return True
