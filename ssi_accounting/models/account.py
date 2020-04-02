# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.osv import expression


class AccountReconciliation(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    @api.model
    def _domain_move_lines_for_reconciliation(self, st_line, aml_accounts, partner_id, excluded_ids=None, search_str=False):
        """ Return the domain for account.move.line records which can be used for bank statement reconciliation.

            :param aml_accounts:
            :param partner_id:
            :param excluded_ids:
            :param search_str:
        """

        domain_reconciliation = [
            '&', '&',
            ('statement_line_id', '=', False),
            ('account_id', 'in', aml_accounts),
            ('balance', '!=', 0.0),
        ]

        # default domain matching
        domain_matching = [
            '&', '&',
            ('reconciled', '=', False),
            ('account_id.reconcile', '=', True),
            ('balance', '!=', 0.0),
        ]

        domain = expression.OR([domain_reconciliation, domain_matching])
        if partner_id:
            domain = expression.AND([domain, [('partner_id', '=', partner_id)]])

        # Domain factorized for all reconciliation use cases
        if search_str:
            str_domain = self._domain_move_lines(search_str=search_str)
            str_domain = expression.OR([
                str_domain,
                [('partner_id.name', 'ilike', search_str)]
            ])
            domain = expression.AND([
                domain,
                str_domain
            ])

        if excluded_ids:
            domain = expression.AND([
                [('id', 'not in', excluded_ids)],
                domain
            ])
        # filter on account.move.line having the same company as the statement line
        domain = expression.AND([domain, [('company_id', '=', st_line.company_id.id)]])

        if st_line.company_id.account_bank_reconciliation_start:
            domain = expression.AND([domain, [('date', '>=', st_line.company_id.account_bank_reconciliation_start)]])
        return domain

