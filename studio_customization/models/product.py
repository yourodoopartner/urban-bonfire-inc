# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    x_product_tmpl_id__purchase_report_count = fields.Integer(compute='_compute_purchase_report_count', string="Product Template count")
    
    def _compute_purchase_report_count(self):
        datas = self.env['purchase.report'].read_group([('product_tmpl_id', 'in', self.ids)], ['product_tmpl_id'], ['product_tmpl_id'])
        mapped_data = dict([(data['product_tmpl_id'][0], data['product_tmpl_id_count']) for data in datas])
        for product in self:
            product.x_product_tmpl_id__purchase_report_count = mapped_data.get(product.id, 0)

