# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PaymentDeposit(models.Model):
    _name = 'bt.payment.deposit'
    _description = 'Deposits'
    
    _order = "name desc, id desc"
    
    name = fields.Char('Name')
    partner_id = fields.Many2one('res.partner', 'Customer')
    invoice_id = fields.Many2one('account.move', 'Invoice', copy=False)
    payment_date = fields.Date('Payment Date')
    payment_amount = fields.Float('Payment Amount')
    payment_id = fields.Many2one('account.payment', 'Customer Payment Ref', copy=False)
    move_id = fields.Many2one('account.move', 'Deposit Collect Move', copy=False)
    deduct_move_id = fields.Many2one('account.move', 'Deposit Deduct Move', copy=False)
    
        
class DepositJournal(models.Model):
    _name = 'bt.deposit.journal'
    _description = 'Deposit Journal'
    
    
    name = fields.Char('Name')
    journal_id = fields.Many2one('account.journal', 'Journal', copy=False, required=True)


    @api.model
    def create(self, values):
        if 'name' in values and not values['name'] and 'journal_id' in values:
            values['name'] = self.env['account.journal'].browse(values['journal_id']).name
        return super(DepositJournal, self).create(values)
    