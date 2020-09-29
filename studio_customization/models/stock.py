# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, SUPERUSER_ID, _


class Picking(models.Model):
    _inherit = "stock.picking"
    
    x_studio_untaxed_amount = fields.Monetary(related='purchase_id.amount_untaxed', string="Untaxed Amount", store=True, readonly=False)



