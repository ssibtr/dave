
from odoo import api, fields, models, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp
import requests


class Jobs(models.Model):
    _name = 'ssi_jobs'
    _description = 'Jobs'
    _order = "create_date,display_name desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    so_ids = fields.One2many('sale.order', 'ssi_job_id', string='SO')
    order_total = fields.Monetary(
        string='Order Total', track_visibility='always', related='so_ids.amount_total')
#     po_count = fields.Integer(string='Purchase Order', compute='_get_po_count')
    po_count = fields.Integer(string='Purchase Order', default=0)
    ai_count = fields.Integer(string='Vendor Bills', compute='_get_ai_count')
    prod_count = fields.Integer(string='Operations', compute='_get_prod_count')
    wo_count = fields.Integer(string='Work Orders', compute='_get_wo_count')
    wc_count = fields.Integer(string='Job Count', compute='_get_wc_count')
    sm_count = fields.Integer(string='Delivery', compute='_get_sm_count')
    currency_id = fields.Many2one('res.currency', string='Account Currency',
                                  help="Forces all moves for this account to have this account currency.")
    stage_id = fields.Many2one('ssi_jobs_stage', group_expand='_read_group_stage_ids',
                               default=lambda self: self.env['ssi_jobs_stage'].search([('name', '=', 'New Job')]), string='Stage',
                               track_visibility='onchange')
    name = fields.Char(string="Job Name", required=True, copy=False, readonly=True,
                       index=True, default=lambda self: _('New'))
#     name = fields.Char(string="Job Name", required=True, copy=False, index=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', ondelete='restrict', required=True,
        domain=[('parent_id', '=', False)])
    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', domain="[('type', '=', 'opportunity')]")
    user_id = fields.Many2one('res.users', related='partner_id.user_id', string='Salesperson')
    project_manager = fields.Many2one('res.users', string='Project Manager')
#     project_manager = fields.Many2one('res.users', related='partner_id.project_manager_id', string='Project Manager', store=True)
    customer_category = fields.Selection(
        [('Top Account', 'Top Account'), ('Key Account', 'Key Account'), ('Account', 'Account'), ('Business Development', 'Business Development'), ('House Account', 'House Account')], string='Customer Category')
    active = fields.Boolean(default=True)
    equipment_id = fields.Many2one('maintenance.equipment', string='Equipment')
#     deadline_date = fields.Datetime(string='Customer Deadline', required=True, default=datetime.today())
    deadline_date = fields.Datetime(string='Customer Deadline')
    org_deadline_date = fields.Datetime(string='Original Deadline')
    deadline_days = fields.Integer(string='Deadline Days', compute='_get_deadline_days', store=True)
#     ready_for_pickup = fields.Datetime(string='Ready for Pickup')
    type = fields.Selection(
        [('Shop', 'Shop'), 
         ('Field Service', 'Field Service'), 
         ('Modification', 'Modification'), 
         ('Inspection Fee', 'Inspection Fee')], 
        string='Job Type', default='Shop')
    urgency = fields.Selection(
        [('straight_quote', 'Straight time quote before repair'), ('straight', 'Straight time'), ('overtime_quote', 'Overtime quote before repair'), ('overtime', 'Overtime')], string='Urgency')
    po_number = fields.Char(string='PO Number')
    notes = fields.Text(string='Notes')
#     status = fields.Selection(
#         [('ready', 'Ready'), ('process', 'In Process'), ('done', 'Complete'), ('blocked', 'Blocked')], string='Status')
    color = fields.Integer(string='Color')
    serial = fields.Char(String="Serial #")
    aa_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    warranty_claim = fields.Boolean(default=False, string="Warranty Claim")
    warranty_status = fields.Selection(
        [('warranty', 'Warranty'), ('concession', 'Customer Concession'), ('not warrantied', 'Not Warrantied')], 
        string='Warranty Status', track_visibility='onchange')
    hide_in_kiosk = fields.Boolean(default=False, string="Hide in Kiosk")
    completed_on = fields.Datetime(string='Completed On')
    line_ids = fields.One2many('ssi_jobs.line', 'ssi_jobs_id', 'Jobs Lines', copy=True)
    # job_account_position_id = fields.Many2one('account.fiscal.position', company_dependent=True,
        # string="Fiscal Position", help="The fiscal position will override the customers when used.")
    
    _sql_constraints = [(
        'name_unique',
        'unique(name)',
        'This job name already exists in the system!'
    )]

    # ACTIONS AND METHODS
    def _track_subtype(self, init_values):
        # init_values contains the modified fields' values before the changes
        #
        # the applied values can be accessed on the record as they are already
        # in cache
        self.ensure_one()
#         if 'warranty_status' in init_values and self.warranty_status == 'not warrantied':
        if 'warranty_status' in init_values:
            if self.warranty_status != '':
                employees = self.env['hr.employee'].search(
                    [('department_id', '=', 21)])
                followers = []
                for emp in employees:
                    if emp.user_id:
                        followers.append(emp.user_id.partner_id.id)
                # Add Ann Kendrick also
                followers.append(57)
                self.message_subscribe(followers)
            return 'ssi_jobs.job_warranty_change'  # Full external id
        return super(Jobs, self)._track_subtype(init_values)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'ssi_job_sequence') or _('New')
        res = super(Jobs, self).create(vals)
        name = res.name
        group = self.env['account.analytic.group'].search(
            [('name', '=', 'Jobs')], limit=1).id
        partner = res.partner_id.id
        aa = self.env['account.analytic.account'].sudo().create(
            {'name': name, 'ssi_job_id': res.id, 'group_id': group, 'partner_id': partner})
        res.write({'aa_id': aa.id})
        
        #QM Wizard dead as of 2.5.2020
        # login_response = requests.post(
            # 'http://api.springpt.com:38136/api/v1/login',
            # headers={'Content-Type': 'application/json'},
            # json={"user_name": "RS_API_USER", "password": "b+PHhK2M", "company_id": "RedStick"},
        # )
        # json_login_response = login_response.json()
        # token = json_login_response['data']['token']

        # create_qm_job = requests.post(
            # 'http://api.springpt.com:38136/api/v1/RSImportJob',
            # headers={'Content-Type': 'application/json', 'x-access-token': token},
            # json= [{
                # "JobID" : res.name,
                # "CustomerID" : res.partner_id.id,
                # "CustomerName" : res.partner_id.name,
                # "Notes" : "",
                # "Make" : "",
                # "Model" : "",
                # "SerialNumber" : "",
                # "RatingUnit" : res.equipment_id.rating_unit,
                # "Poles" : "",
                # "RPM" : "",
                # "Frame" : "",
                # "Enclosure" : "",
                # "Voltage" : "",
                # "Amps" : "",
                # "ODEBearing" : "",
                # "DEBearing" : "",
                # "CustomerStock" : "",
                # "CustomerIDMotor" : "",
                # "Phase" : "",
                # "Mounting" : "",
                # "Duty" : "",
                # "NEMADesign" : "",
                # "ServiceFactor" : "",
                # "Weight" : "",
                # "BearingType" : "",
                # "StatorWindingType" : "",
                # "LubeType": ""
            # }]
        # )      
        return res
        # raise UserError(_(res.id))


    @api.onchange('org_deadline_date')
    def _onchange_org_deadline(self):
        # When updating original deadline, copy to the customer deadline.
        if self.org_deadline_date:
            self.deadline_date = self.org_deadline_date
                
    @api.onchange('partner_id')
    def _onchange_partner_pm(self):
        # When updating partner, auto set project manager.
        if not self.opportunity_id:
            if self.partner_id.project_manager_id:
                self.project_manager = self.partner_id.project_manager_id.id
            if self.partner_id.customer_category:
                self.customer_category = self.partner_id.customer_category
        else:
            if self.opportunity_id.project_manager:
                self.project_manager = self.opportunity_id.project_manager.id
            if self.opportunity_id.customer_category:
                self.customer_category = self.opportunity_id.customer_category
                
    # @api.onchange('type', 'partner_id')
    # def _onchange_type(self):
        # When updating job type, check fiscal postion.
        # if self.partner_id:
            # if self.type == 'Field&nbsp;Service' and self.partner_id.job_fs_account_position_id.id:
                # self.job_account_position_id = self.partner_id.job_fs_account_position_id.id
            # if self.type == 'Modification' and self.partner_id.job_mod_account_position_id.id:
                # self.job_account_position_id = self.partner_id.job_mod_account_position_id.id
            # else:
                # self.job_account_position_id = self.partner_id.property_account_position_id.id
                
    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        stage_ids = self.env['ssi_jobs_stage'].search([])
        return stage_ids

    @api.multi  # DONE
    def action_view_estimates(self):
        action = self.env.ref(
            'ssi_jobs.sale_order_estimate_line_action').read()[0]
#        raise UserError(_(action))
        action['domain'] = [('ssi_job_id', '=', self.id)]
        return action

    @api.multi
    def action_view_po_count(self):
        po_lines = self.env['purchase.order.line'].search([('account_analytic_id', '=', self.aa_id.id)])
        po_ids = []
        for line in po_lines:
            po_ids.append(line.order_id.id)
        action = self.env.ref(
            'ssi_jobs.purchase_order_line_action').read()[0]
        action['domain'] = [('id', 'in', po_ids)]
        return action

    @api.multi
    def action_view_ai_count(self):
        action = self.env.ref(
            'ssi_jobs.sale_order_ai_line_action').read()[0]
        action['domain'] = [('ssi_job_id', '=', self.id)]
        return action

    @api.multi
    def action_view_prod_count(self):
        action = self.env.ref(
            'ssi_jobs.sale_order_prod_line_action').read()[0]
        action['domain'] = [('ssi_job_id', '=', self.id)]
        return action

    @api.multi
    def action_view_wo_count(self):
        action = self.env.ref(
            'ssi_jobs.sale_order_wo_line_action').read()[0]
        action['domain'] = [('ssi_job_id', '=', self.id)]
        return action

    @api.multi
    def action_view_wc_count(self):
        action = self.env.ref(
            'ssi_jobs.sale_order_wc_line_action').read()[0]
        action['domain'] = [('ssi_job_id', '=', self.id)]
        return action

    @api.multi
    def action_view_sm_count(self):
        action = self.env.ref(
            'ssi_jobs.sale_order_sm_line_action').read()[0]
        action['domain'] = ['|',('so_job_id', '=', self.id),('po_job_id', '=', self.id)]
        return action

#     @api.multi
#     def action_view_aa_count(self):
#         action = self.env.ref(
#             'ssi_jobs.sale_order_aa_line_action').read()[0]
#         action['domain'] = [('ssi_job_id', '=', self.id)]
#         return action

    @api.multi
    def ssi_jobs_new_so_button(self):
        action = self.env.ref(
            'ssi_jobs.ssi_jobs_new_so_action').read()[0]
        action['domain'] = [('ssi_job_id', '=', self.id)]
#         ord_lines = []
#         ord_line_vals = (
#             'product_id': self.jobs_line_ids[0].product_id.id,
#             'product_uom_qty': self.jobs_line_ids[0].product_qty or 1,
#         )

#         if self.jobs_line_ids[0].product_id:
#             ord_lines = (0, 0, ord_line_vals)
# #             ord_lines.append((0, 0, ord_line_vals))
#         action['context'] = {
#             'default_order_line': ord_lines,
#         }
        return action

    @api.multi
    def ssi_jobs_new_mrp_prod_button(self):
        if not self.line_ids:
            raise UserError(_('You must have a product defined before starting a job.'))
        action = self.env.ref(
            'ssi_jobs.ssi_jobs_new_prod_action').read()[0]
        action['domain'] = [('ssi_job_id', '=', self.id)]
        action['context'] = {
            'default_product_id': self.line_ids[0].product_id.id,
            'default_origin': self.name,
        }
        return action

    @api.multi
    def ssi_jobs_new_po_button(self):
        action = self.env.ref(
            'ssi_jobs.ssi_jobs_new_po_action').read()[0]
        action['domain'] = [('ssi_job_id', '=', self.id)]
        return action

#     @api.depends('order_total')
#     def _get_po_count(self):
#         results = self.env['purchase.order.line'].read_group(
#             domain=[('account_analytic_id', '=', self.aa_id.id)],
#             fields=['account_analytic_id'], groupby=['account_analytic_id']
#         )
#         for res in results:
#             for job in self:
#                 job.po_count = res['account_analytic_id_count']
#         self.po_count = 0

    @api.depends('order_total')
    def _get_ai_count(self):
        results = self.env['account.invoice.line'].sudo().read_group(
            [('ssi_job_id', 'in', self.ids)], 'ssi_job_id', 'ssi_job_id')
        dic = {}
        for x in results:
            dic[x['ssi_job_id'][0]] = x['ssi_job_id_count']
        for record in self:
            record.ai_count = dic.get(
                record.id, 0)

    @api.depends('order_total')
    def _get_prod_count(self):
        results = self.env['mrp.production'].sudo().read_group(
            [('ssi_job_id', 'in', self.ids)], 'ssi_job_id', 'ssi_job_id')
        dic = {}
        for x in results:
            dic[x['ssi_job_id'][0]] = x['ssi_job_id_count']
        for record in self:
            record.prod_count = dic.get(
                record.id, 0)

    @api.depends('order_total')
    def _get_wo_count(self):
        results = self.env['mrp.workorder'].sudo().read_group(
            [('ssi_job_id', 'in', self.ids)], 'ssi_job_id', 'ssi_job_id')
        dic = {}
        for x in results:
            dic[x['ssi_job_id'][0]] = x['ssi_job_id_count']
        for record in self:
            record.wo_count = dic.get(
                record.id, 0)

    @api.depends('order_total')
    def _get_wc_count(self):
        results = self.env['mrp.workcenter.productivity'].sudo().read_group(
            [('ssi_job_id', 'in', self.ids)], 'ssi_job_id', 'ssi_job_id')
        dic = {}
        for x in results:
            dic[x['ssi_job_id'][0]] = x['ssi_job_id_count']
        for record in self:
            record.wc_count = dic.get(
                record.id, 0)

    @api.depends('order_total')
    def _get_sm_count(self):
        for record in self:
            so_count = self.env['stock.picking'].sudo().search_count([('so_job_id', '=', record.id)])
            po_count = self.env['stock.picking'].sudo().search_count([('po_job_id', '=', record.id)])
            record.sm_count = so_count + po_count

    @api.multi
    def write(self, vals):
        # stage change: update date_last_stage_update
        if 'stage_id' in vals: 
            if vals['stage_id'] >= 7 and not self.completed_on:
                vals['completed_on'] = fields.Datetime.now()
            elif vals['stage_id'] < 7: 
                vals['completed_on'] = False
        return super(Jobs, self).write(vals)

#     @api.onchange('stage_id')
#     def _change_complete(self):
#         if self.stage_id.id == 15:
#             self.completed_on = fields.Datetime.now()
#         else:
#             self.completed_on = ''
        
    @api.model
    def run_job_kiosk_scheduler(self):
        # Flip hid flag on kiosk for jobs completed 24 hours ago
        jobs = self.env['ssi_jobs'].search([('stage_id', '>=', 7)])
        for job in jobs:
            delta = fields.Datetime.now()-job.completed_on
            if delta > timedelta(minutes=5):
                job.hide_in_kiosk = True

#     @api.depends('order_total')
#     def _get_aa_count(self):
#         results = self.env['account.analytic.account'].read_group(
#             [('ssi_job_id', 'in', self.ids)], 'ssi_job_id', 'ssi_job_id')
#         dic = {}
#         for x in results:
#             dic[x['ssi_job_id'][0]] = x['ssi_job_id_count']
#         for record in self:
#             record.wc_count = dic.get(
#                 record.id, 0)

    def _get_name(self):
        """ Utility method to allow name_get to be overrided without re-browse the partner """
        partner = self.partner_id
        name = partner.name or ''

#         raise UserError(partner.parent_id)
        if partner.company_name or partner.parent_id:
            if not name and partner.type in ['invoice', 'delivery', 'other']:
                name = dict(self.fields_get(['type'])['type']['selection'])[partner.type]
            if not partner.is_company:
#                 raise UserError(partner.parent_id)
                name = "%s, %s" % (partner.commercial_company_name or partner.parent_id.name, name)
        if self._context.get('show_address_only'):
            name = partner._display_address(without_company=True)
        if self._context.get('show_address'):
            name = name + "\n" + partner._display_address(without_company=True)
        name = name.replace('\n\n', '\n')
        name = name.replace('\n\n', '\n')
        if self._context.get('address_inline'):
            name = name.replace('\n', ', ')
        if self._context.get('show_email') and partner.email:
            name = "%s <%s>" % (name, partner.email)
        if self._context.get('html_format'):
            name = name.replace('\n', '<br/>')
        if self._context.get('show_vat') and partner.vat:
            name = "%s ‒ %s" % (name, partner.vat)
        name = "%s ‒ %s" % (self.name, name)
        return name

    @api.multi
    def _get_deadline_days(self):
        # calc # of days job was completed compared to deadline.
        for record in self:
            if record.completed_on and record.deadline_date:
                record.deadline_days = (record.deadline_date - record.completed_on).days
            else:
                record.deadline_days = 0
        
    @api.multi
    def name_get(self):
        res = []
        for partner in self:
            name = partner._get_name()
            res.append((partner.id, name))
        return res


class JobsLine(models.Model):
    _name = 'ssi_jobs.line'
    _order = "sequence, id"
    _rec_name = "product_id"
    _description = 'SSI Jobs Product Lines'

    ssi_jobs_id = fields.Many2one('ssi_jobs', 'Jobs ID', index=True, required=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_uom_qty = fields.Float('Quantity', default=1.0, digits=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    sequence = fields.Integer('Sequence', default=1, help="Gives the sequence order when displaying.")
    mo_exists = fields.Boolean('MO Exists', help="A Manufacture Order already exists for this product.", compute='_get_mo_exists')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.ensure_one()
        if self.product_id:
#             name = self.product_id.name_get()[0][1]
#             if self.product_id.description_sale:
#                 name += '\n' + self.product_id.description_sale
#             self.name = name
#             self.price_unit = self.product_id.lst_price
            self.product_uom_id = self.product_id.uom_id.id
            domain = {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
            return {'domain': domain}

    @api.multi
    def ssi_jobs_new_mrp_prod_button(self):
        action = self.env.ref(
            'ssi_jobs.ssi_jobs_new_prod_action').read()[0]
        action['domain'] = [('ssi_job_id', '=', self.ssi_jobs_id.id)]
        action['context'] = {
            'default_product_id': self.product_id.id,
            'default_origin': self.ssi_jobs_id.name,
            'default_ssi_job_id' : self.ssi_jobs_id.id,
        }
        return action

    @api.multi
    def _get_mo_exists(self):
        for record in self:
            mo_count = self.env['mrp.production'].search_count([('ssi_job_id', '=', record.ssi_jobs_id.id), ('product_id', '=', record.product_id.id)])
            if mo_count > 0:
                record.mo_exists = True
            else:
                record.mo_exists = False
