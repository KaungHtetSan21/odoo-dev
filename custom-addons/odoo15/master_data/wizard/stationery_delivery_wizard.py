from odoo import models, fields, api
from odoo.exceptions import UserError


class StationeryDeliveryWizard(models.TransientModel):
    _name = 'stationery.delivery.wizard'
    _description = 'Stationery Delivery Confirmation Wizard'

    request_id = fields.Many2one('stationery.request', required=True)
    line_ids = fields.One2many(
        'stationery.delivery.wizard.line',
        'wizard_id',
        string='Products'
    )

    @api.model
    def create(self, vals):
        wizard = super().create(vals)
        request = wizard.request_id
        lines = []

        for line in request.line_ids:
            lines.append((0, 0, {
                'wizard_id': wizard.id,
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'delivered_qty': line.delivered_qty,
            }))

        wizard.line_ids = lines
        return wizard

    def action_confirm_delivery(self):
        self.ensure_one()
        
        # Check all products are checked
        unchecked = self.line_ids.filtered(lambda l: not l.is_checked)
        if unchecked:
            raise UserError(
                "Please check all items before confirming delivery."
            )

        request = self.request_id
        picking = request.picking_id

        if not picking:
            raise UserError("No transfer found for this request.")

        # Confirm picking if still in draft
        if picking.state == 'draft':
            picking.action_confirm()

        # Assign stock
        picking.action_assign()

        # Set done quantities
        for move in picking.move_ids_without_package:
            for line in self.line_ids:
                if line.product_id == move.product_id:
                    move.quantity_done = line.quantity
                    # Update delivered quantity in request line
                    request_line = request.line_ids.filtered(
                        lambda l: l.product_id == line.product_id
                    )
                    if request_line:
                        request_line.delivered_qty = line.quantity
                    break

        # Validate picking
        picking.with_context(
            from_request_delivery=True
        ).button_validate()

        # Update request state
        request.state = 'delivered'
        picking.approval_state = 'done'
        
        request.message_post(
            body=f"Request has been delivered. Transfer {picking.name} has been validated."
        )

        return {'type': 'ir.actions.act_window_close'}


class StationeryDeliveryWizardLine(models.TransientModel):
    _name = 'stationery.delivery.wizard.line'
    _description = 'Stationery Delivery Wizard Line'

    wizard_id = fields.Many2one(
        'stationery.delivery.wizard',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one('product.product', readonly=True)
    quantity = fields.Float(readonly=True)
    delivered_qty = fields.Float(string='Delivered Qty', readonly=True)
    is_checked = fields.Boolean(string="Checked", default=False)

    def action_toggle_check(self):
        for line in self:
            line.is_checked = not line.is_checked