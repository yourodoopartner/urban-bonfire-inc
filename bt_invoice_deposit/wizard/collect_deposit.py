# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class CollectDeposit(models.TransientModel):
    _name = 'bt.collect.deposit'
    _description = 'Collect Deposits'

    payment_date = fields.Date('Payment Date', required=True, default=fields.Date.context_today)
    payment_amount = fields.Float('Payment Amount', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, 
                            tracking=True, domain="[('type', 'in', ('bank', 'cash'))]")
    
    
    @api.model
    def default_get(self, default_fields):
        rec = super(CollectDeposit, self).default_get(default_fields)
        active_id = self._context.get('active_id')

        invoices = self.env['account.move'].browse(active_id)

        rec.update({
            'payment_amount': invoices[0].amount_total
        })
        return rec
    
    def create_deposit(self):
        invoice_ids = self._context.get('active_ids')
        invoice_objs = self.env['account.move'].browse(invoice_ids)
        for invoice_obj in  invoice_objs:
            name = self.env['ir.sequence'].next_by_code('payment.deposit', sequence_date=self.payment_date)
            vals = {
                'name': name,
                'partner_id': invoice_obj.partner_id and invoice_obj.partner_id.id or False,
                'invoice_id': invoice_obj.id,
                'payment_date': self.payment_date,
                'payment_amount': self.payment_amount,
                }
            deposit = self.env['bt.payment.deposit'].create(vals)
            
            payment_vals = {
                'company_id': invoice_obj.company_id and invoice_obj.company_id.id or False,
                'partner_id': invoice_obj.partner_id and invoice_obj.partner_id.id or False,
                'amount': self.payment_amount,
                'currency_id': invoice_obj.currency_id.id,
                'journal_id': self.journal_id.id,
                'communication': invoice_obj.partner_id and 'Deposit: ' + invoice_obj.partner_id.name or 'Deposit',
                'payment_date': self.payment_date,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'payment_method_id': self.journal_id.inbound_payment_method_ids and self.journal_id.inbound_payment_method_ids[0].id or False
                }
            payment_obj = self.env['account.payment']\
                    .with_context(active_ids=[deposit.id], active_model='bt.payment.deposit', active_id=deposit.id)\
                    .create(payment_vals)
            payment_obj.post()
            
            deposit.payment_id = payment_obj.id
            deposit.move_id = payment_obj.move_line_ids[0].move_id.id
            invoice_obj.deposit_exist = True
            invoice_obj.deposit_amount_collected = self.payment_amount
            invoice_obj.inv_balance_owed = invoice_obj.amount_total - self.payment_amount

        return True
    