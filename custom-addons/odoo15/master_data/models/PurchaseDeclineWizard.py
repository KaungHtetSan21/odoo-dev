from odoo import models, fields, api
from odoo.exceptions import UserError

class PurchaseDeclineWizard(models.TransientModel):
    _name = 'purchase.decline.wizard'
    _description = 'Purchase Decline Reason'

    purchase_id = fields.Many2one('purchase.order', required=True)

    decline_reason = fields.Selection([
        ('location_unavailable', 'Location unavailable'),
        ('requirement_error', 'Requirements error'),
        ('exceed_quantity', 'Exceed the expected quantity'),
        ('quantity_enough', 'Available quantity still enough'),
        ('other', 'Other'),
    ], string="Decline Reason", required=True)

    decline_reason_note = fields.Text(string="Other Reason")

    def action_confirm_decline(self):
        self.ensure_one()

        if self.decline_reason == 'other' and not self.decline_reason_note:
            raise UserError("Please provide details for 'Other' reason.")

        self.purchase_id.write({
            'state': 'denied',
            'ask_approval': False,
            'manager_approved': False,
            'approval_locked': False,
            'decline_reason': self.decline_reason,
            'decline_reason_note': self.decline_reason_note,
            'declined_by': self.env.user.id,
            'declined_date': fields.Datetime.now(),
        })

        return {'type': 'ir.actions.act_window_close'}