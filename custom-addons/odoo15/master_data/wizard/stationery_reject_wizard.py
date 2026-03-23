from odoo import models, fields, api
from odoo.exceptions import UserError

class StationeryRejectWizard(models.TransientModel):
    _name = 'stationery.transfer.reject.wizard'
    _description = 'Reject Reason Wizard'

    picking_id = fields.Many2one('stock.picking', string='Transfer', required=True)
    reject_reason = fields.Text(string='Reject Reason', required=True)

    def action_confirm_reject(self):
        self.ensure_one()

        picking = self.picking_id

        # Mark picking as rejected with reason
        picking.write({
            'approval_state': 'rejected',
            'reject_reason': self.reject_reason,
        })

        # Cancel the picking if still draft/confirmed
        if picking.state not in ['done', 'cancel']:
            picking.action_cancel()

        # Find linked request via origin
        request = self.env['stationery.request'].search(
            [('name', '=', picking.origin)],
            limit=1
        )

        if request:
            # For request-based transfers, we might want to set request back to submitted
            request.write({
                'state': 'submitted',
                'picking_id': False,
            })

        # Post message
        picking.message_post(body=f"Transfer has been rejected. Reason: {self.reject_reason}")

        return {'type': 'ir.actions.act_window_close'}