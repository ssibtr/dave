from odoo import api, fields, models, _
from odoo.exceptions import UserError


class JobsStage(models.Model):
    _name = 'ssi_jobs_stage'
    _description = 'Jobs Stage'
    
    name = fields.Char(string='Name')
    display_name = fields.Char(string='Display Name', readonly=True, track_visibility="onchange")

    @api.model
    def add_default_records_on_install(self):
        self.create({'name': 'New Job'})
        self.create({'name': 'Inspection'})
        self.create({'name': 'Review'})
        self.create({'name': 'Quotation Sent'})
        self.create({'name': 'Awaiting Parts'})
        self.create({'name': 'Under Repair'})
        self.create({'name': 'Job Complete'})
                