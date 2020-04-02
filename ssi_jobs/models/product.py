# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.addons import decimal_precision as dp

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    hide_on_print = fields.Boolean('Do Not Print', default=False)
    hs_code = fields.Char(
        string="HS Code",
        help="Standardized code for international shipping and goods declaration. At the moment, only used for the FedEx shipping provider.",
    )

class ProductCategory(models.Model):
    _inherit = "product.category"

    hide_on_print = fields.Boolean('Do Not Print', default=False)
    profit_center = fields.Selection(
        [('Disassembly', 'Disassembly'), ('Machine Shop', 'Machine Shop'), ('Winding', 'Winding'), ('Assembly', 'Assembly'), ('Field Services', 'Field Services'), ('New Product Sales', 'New Product Sales'), ('Storage', 'Storage'), ('Training', 'Training')], string='Profit Center')

class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    rebate_amount = fields.Float('Rebate Amount', digits=dp.get_precision('Product Price'))
    
class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _anglo_saxon_sale_move_lines(self, name, product, uom, qty, price_unit, currency=False, amount_currency=False, fiscal_position=False, account_analytic=False, analytic_tags=False):
        res = super()._anglo_saxon_sale_move_lines(
            name,
            product,
            uom,
            qty,
            price_unit,
            currency=currency,
            amount_currency=amount_currency,
            fiscal_position=fiscal_position,
            account_analytic=account_analytic,
            analytic_tags=analytic_tags,
        )
        if res:
            res[0]['account_analytic_id'] = account_analytic and account_analytic.id
            res[0]['analytic_tag_ids'] = analytic_tags and analytic_tags.ids and [(6, 0, analytic_tags.ids)] or False
        return res

