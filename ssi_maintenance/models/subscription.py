# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools import format_date

import datetime
import requests


class SaleSubscription(models.Model):
    _inherit = 'sale.subscription'
    
#     equip_id = fields.Char(string='Equip_id')
    storage_id = fields.One2many('storage', 'subscription_id', string='Storage')
    square_foot_total = fields.Float(string='Square Foot Total', compute='_get_sqf_total')
    last_invoice_date = fields.Date(string='Last Invoiced Date', compute='_get_last_invoice')
    ext_invoice_date = fields.Date(string='External Invoice Date')
    project_manager = fields.Many2one('res.users', string='Project Manager')
#     project_manager = fields.Many2one('res.users', related='partner_id.project_manager_id', string='Project Manager', store=True)
    customer_category = fields.Selection(
        [('Top Account', 'Top Account'), ('Key Account', 'Key Account'), ('Account', 'Account'), ('House Account', 'House Account'), ('New Account', 'New Account')], string='Customer Category')

    # ACTIONS AND METHODS
    @api.onchange('partner_id')
    def _onchange_partner_pm(self):
        # When updating partner, auto set project manager.
        if self.partner_id.project_manager_id:
            self.project_manager = self.partner_id.project_manager_id.id
        if self.partner_id.customer_category:
            self.customer_category = self.partner_id.customer_category

    def recurring_invoice(self):
        self.ssi_update_lines()
        self._recurring_create_invoice()
        current_date = datetime.date.today()
        for strg in self.storage_id:
            strg.last_invoiced = current_date
        
        return self.action_subscription_invoice()

    @api.depends('storage_id')
    def _get_sqf_total(self):
        total = 0
        for record in self:
            for strg in record.storage_id:
                total = total + strg.equip_square_feet
            record.square_foot_total = total

    def _get_last_invoice(self):
        Invoice = self.env['account.invoice']
        can_read = Invoice.check_access_rights('read', raise_exception=False)
        for subscription in self:
            current_invoice = Invoice.search([('invoice_line_ids.subscription_id', '=', subscription.id)],order="id desc",limit=1)
            if current_invoice:
                subscription.last_invoice_date = current_invoice.date_invoice
            elif subscription.ext_invoice_date:
                subscription.last_invoice_date = subscription.ext_invoice_date
            else:
                subscription.last_invoice_date = 0

    @api.multi
    def _cron_ssi_update_lines(self):
        # Update subsctiption lines
        current_date = datetime.date.today()
        if len(self) > 0:
            subscriptions = self
        else:
            domain = [('recurring_next_date', '<=', current_date),
                      '|', ('in_progress', '=', True), ('to_renew', '=', True)]
            subscriptions = self.search(domain)
        if subscriptions:
            sub_data = subscriptions.read(fields=['id', 'company_id'])
            for company_id in set(data['company_id'][0] for data in sub_data):
                sub_ids = [s['id'] for s in sub_data if s['company_id'][0] == company_id]
                subs = self.with_context(company_id=company_id, force_company=company_id).browse(sub_ids)
                context_company = dict(self.env.context, company_id=company_id, force_company=company_id)
                for subscription in subs:
                    lines = subscription.recurring_invoice_line_ids
                    lines_to_remove = lines.filtered(lambda l: l.product_id.storage_subscription)
            #         raise UserError(_(lines_to_remove))
                    lines_to_remove.unlink()
                    lines = []
                    product =  self.env['product.product'].search([('storage_subscription', '=', True)], limit=1)
                    for strg in subscription.storage_id:
                        if not strg.last_invoiced:
                            last_inv = datetime.date(1, 1, 1)
                        else:
                            last_inv = strg.last_invoiced
                        if not strg.check_out or (strg.check_out.date() > last_inv):
                            line_name = '%s (%s)' % (strg.equipment_id.name, strg.equip_serial_no)
                            uom =  self.env['uom.uom'].search([('id', '=', strg.subscription_uom.id)], limit=1)
                            price = uom.factor_inv * strg.subscription_price
                            vals = {
                                "product_id": product.id,
                                "name": line_name,
                                "quantity": strg.equip_square_feet,
                                "price_unit": price
                            }
                            if strg.subscription_uom:
                                vals.update({"uom_id": strg.subscription_uom})
                            lines.append(vals)
                    subscription.update({"recurring_invoice_line_ids": lines})
        
    @api.multi
    def ssi_update_lines(self):
        # Update subsctiption lines
        lines = self.recurring_invoice_line_ids
        lines_to_remove = lines.filtered(lambda l: l.product_id.storage_subscription)
#         raise UserError(_(lines_to_remove))
        lines_to_remove.unlink()
        lines = []
        product =  self.env['product.product'].search([('storage_subscription', '=', True)], limit=1)
        for strg in self.storage_id:
            if not strg.last_invoiced:
                last_inv = datetime.date(1, 1, 1)
            else:
                last_inv = strg.last_invoiced
            if not strg.check_out or (strg.check_out.date() > last_inv):
                line_name = '%s (%s)' % (strg.equipment_id.name, strg.equip_serial_no)
                uom =  self.env['uom.uom'].search([('id', '=', strg.subscription_uom.id)], limit=1)
                price = uom.factor_inv * strg.subscription_price
                vals = {
                    "product_id": product.id,
                    "name": line_name,
                    "quantity": strg.equip_square_feet,
                    "price_unit": price
                }
                if strg.subscription_uom:
                    vals.update({"uom_id": strg.subscription_uom})
                lines.append(vals)
        self.update({"recurring_invoice_line_ids": lines})

    def _prepare_invoice_data(self):
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("You must first select a Customer for Subscription %s!") % self.name)

        if 'force_company' in self.env.context:
            company = self.env['res.company'].browse(self.env.context['force_company'])
        else:
            company = self.company_id
            self = self.with_context(force_company=company.id, company_id=company.id)

        fpos_id = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id)
        journal = self.template_id.journal_id or self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', company.id)], limit=1)
        if not journal:
            raise UserError(_('Please define a sale journal for the company "%s".') % (company.name or '', ))

        next_date = fields.Date.from_string(self.recurring_next_date)
        if not next_date:
            raise UserError(_('Please define Date of Next Invoice of "%s".') % (self.display_name,))
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        if self.template_id.pre_paid:
            first_date = next_date
            last_date = next_date + relativedelta(**{periods[self.recurring_rule_type]: self.recurring_interval})
            last_date = last_date - relativedelta(days=1)     # remove 1 day as normal people thinks in term of inclusive ranges.
        else:
            first_date = next_date - relativedelta(**{periods[self.recurring_rule_type]: self.recurring_interval})
            first_date = first_date + relativedelta(days=1)     # remove 1 day as normal people thinks in term of inclusive ranges.
            last_date = next_date
        addr = self.partner_id.address_get(['delivery', 'invoice'])

        sale_order = self.env['sale.order'].search([('order_line.subscription_id', 'in', self.ids)], order="id desc", limit=1)
        return {
            'account_id': self.partner_id.property_account_receivable_id.id,
            'type': 'out_invoice',
            'partner_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'currency_id': self.pricelist_id.currency_id.id,
            'journal_id': journal.id,
            'origin': self.code,
            'fiscal_position_id': fpos_id,
            'payment_term_id': sale_order.payment_term_id.id if sale_order else self.partner_id.property_payment_term_id.id,
            'company_id': company.id,
            'comment': _("This invoice covers the following period: %s - %s") % (format_date(self.env, first_date), format_date(self.env, last_date)),
            'user_id': self.user_id.id,
            'name': sale_order.client_order_ref,
        }

class SaleSubscription(models.Model):
    _inherit = 'sale.subscription.template'
    
    pre_paid = fields.Boolean('Pre Paid Flag', help="Check this box if the subscription is pre paid.")
