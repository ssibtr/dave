# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _


class QualityCheck(models.Model):
    _inherit = "quality.check"

    product_id = fields.Many2one('product.product', 'Product', domain="[('type', 'in', ['consu', 'product'])]", required=False)
    ssi_job_id = fields.Many2one('ssi_jobs', related='workorder_id.ssi_job_id', string='Job', store=True)
    wo_notes = fields.Char(string="Notes")

