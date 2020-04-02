# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _

class Orderpoint(models.Model):
    """ Defines Minimum stock rules. """
    _inherit = "stock.warehouse.orderpoint"

    lead_days = fields.Integer(
        'Lead Time', default=0,
        help="Number of days after the orderpoint is triggered to receive the products or to order to the vendor")
