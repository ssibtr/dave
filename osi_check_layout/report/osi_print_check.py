# Copyright (C) 2019 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, _

class ReportPrintCheck(models.Model):
    _inherit = 'account.payment'

    def _check_build_page_info(self, i, p):
        chk_info = super(ReportPrintCheck, self)._check_build_page_info(i, p)
        chk_info.update({
            'partner_street': self.partner_id.street,
            'partner_street2': self.partner_id.street2,
            'partner_city': self.partner_id.city,
            'partner_state': self.partner_id.state_id.code,
            'partner_zip': self.partner_id.zip,
            'partner_country': self.partner_id.country_id.name\
                if (self.partner_id.country_id != self.company_id.country_id\
                and self.partner_id.country_id.code == 'US')\
                else False, #Do not print country on check if payee's country is US and is the same as payer's
        })
        return chk_info