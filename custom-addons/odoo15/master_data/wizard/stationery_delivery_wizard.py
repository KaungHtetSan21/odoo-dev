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
            }))

        wizard.line_ids = lines

        return wizard

    def action_confirm_delivery(self):
        self.ensure_one()

        # 🚨 MUST CHECK ALL PRODUCTS
        unchecked = self.line_ids.filtered(lambda l: not l.is_checked)
        if unchecked:
            raise UserError(
                "Please check all items before making stock movements."
            )

        request = self.request_id
        picking = request.picking_id

        if picking.state == 'draft':
            picking.action_confirm()

        picking.action_assign()

        for move in picking.move_ids_without_package:
            for ml in move.move_line_ids:
                ml.qty_done = move.product_uom_qty

        picking.with_context(
            from_request_delivery=True
        ).button_validate()

        request.state = 'delivered'
        picking.approval_state = 'done'
        picking.message_post(
            body="Stock physically transferred after delivery confirmation."
        )



class StationeryDeliveryWizardLine(models.TransientModel):
    _name = 'stationery.delivery.wizard.line'

    wizard_id = fields.Many2one(
        'stationery.delivery.wizard',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one('product.product', readonly=True)
    quantity = fields.Float(readonly=True)
    is_checked = fields.Boolean(string="Checked")

    def action_toggle_check(self):
        for line in self:
            line.is_checked = not line.is_checked