# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockRule(models.Model):
    _inherit = 'stock.rule'


    def _make_po_get_domain(self, company_id, values, partner):
        domain = super(StockRule, self)._make_po_get_domain(company_id, values, partner)
        
        if 'group_id' in values and values['group_id'] and values['group_id'].sale_id:
            domain += (('origin', '=', values['group_id'].sale_id.name),)
        return domain

