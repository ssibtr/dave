# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import datetime
import requests


class CrossoveredBudget(models.Model):
    _inherit = "crossovered.budget"

    budget_category = fields.Selection(
        [('executive', 'Executive'), ('storage', 'Storage'), ('job', 'Job'), ('other', 'Other')], string='Budget Category')

class CrossoveredBudgetLines(models.Model):
    _inherit = "crossovered.budget.lines"

    remaining_amount = fields.Monetary('Remaining Amount', compute='_compute_remaining',
        help="Amount remaining to spend.")
    reference = fields.Char(string='Reference')

    @api.multi
    def _compute_remaining(self):
        for line in self:
            line.remaining_amount = float(line.planned_amount - line.practical_amount)

