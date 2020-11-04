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
    move_id = fields.Many2one('account.move', 'Account Move', copy=False)
    
    
        
