# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, SUPERUSER_ID, _


class Picking(models.Model):
    _inherit = "stock.picking"
    
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True)
    
    x_studio_untaxed_amount = fields.Monetary(related='purchase_id.amount_untaxed', string="Untaxed Amount", store=True, readonly=False)


    def _get_company_currency(self):
        for picking in self:
            picking.currency_id = picking.company_id.currency_id
