from odoo import models, fields, api
from odoo.exceptions import UserError

class RejectStationeryRequestWizard(models.TransientModel):
    _name = 'stationery.request.reject.wizard'
    _description = 'Reject Stationery Request Wizard'

    request_id = fields.Many2one('stationery.request', required=True, readonly=True)
    reject_reason = fields.Text(string="Reason for Rejection", required=True)

    rejected_by = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
    rejected_date = fields.Datetime(default=fields.Datetime.now, readonly=True)

    def action_confirm_reject(self):
        self.ensure_one()

        self.request_id.write({
            'state': 'rejected',
            'rejected_by': self.env.user.id,
            'rejected_date': fields.Datetime.now(),
            'reject_reason': self.reject_reason,
            'approved_by': False,
            'approved_date': False,
        })

        return {'type': 'ir.actions.act_window_close'}