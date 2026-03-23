from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ________________Stationery Transfer Flag____________
    is_stationery_transfer = fields.Boolean(string='Is Stationery Transfer', default=False)
    move_ids_without_package_count = fields.Integer(string='Product Count', compute='_compute_move_counts')

    # GM Approval Checkbox
    is_gm_approved = fields.Boolean(string='Is GM Approve', default=False,
                                     help='Check this box to confirm GM approval before submission')
    transfer_type = fields.Selection([
                ('normal', 'Normal Transfer'),
                ('emergency', 'Emergency Transfer'),
            ], default='normal', string='Transfer Type')

    # _________________Approval State_________________
    approval_state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'GM Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),  # New temporary state
        ('transferred', 'Transferred'),
        ('done', 'Done'),
    ], default='draft', tracking=True)
    reject_reason = fields.Text(string='Reject Reason')
    from_department_id = fields.Many2one('hr.department', string='From BU/BR/DIV')
    to_department_id = fields.Many2one('hr.department', string='To BU/BR/DIV')
    received_date = fields.Datetime(string='Received Date')
    ga_pic_feedback = fields.Text(string='GA PIC Feedback')
    remark = fields.Text(string="Remark")
    total_qty = fields.Float(string='Total Quantity',
                            compute='_compute_total_qty')
    # In stock_picking class
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Source Purchase Order',
        readonly=True
    )
    return_ids = fields.One2many(
        'stationery.return',
        'source_transfer_id',
        string='Returns'
    )

    @api.depends('move_ids_without_package')
    def _compute_move_counts(self):
        for picking in self:
            picking.move_ids_without_package_count = len(picking.move_ids_without_package)

    @api.depends('move_ids_without_package.product_uom_qty')
    def _compute_total_qty(self):
        for picking in self:
            picking.total_qty = sum(picking.move_ids_without_package.mapped('product_uom_qty'))

    # ==========================================
    # APPROVAL ACTIONS
    # ==========================================

    def action_submit(self):
        for rec in self:
            if not rec.move_ids_without_package:
                raise UserError("Add at least one product before submitting.")
            if not rec.is_gm_approved:
                raise UserError("You must check 'Is GM Approve' before submitting.")
            
            # Write method နဲ့သေချာ update လုပ်
            rec.write({
                'approval_state': 'submitted'
            })
            
            # Optional: Add message in chatter
            rec.message_post(body="Transfer has been submitted for GM approval.")
            
        return True

    def action_gm_approve(self):
        for rec in self:
            rec.approval_state = 'approved'
            rec.received_date = datetime.now()

    def action_open_reject_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Transfer',
            'res_model': 'stationery.transfer.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
            }
        }

    def action_cancel_transfer(self):
        """Handle cancel button click - shows reset to draft button"""
        for rec in self:
            # Only allow cancel in submitted or approved states
            if rec.approval_state not in ['submitted', 'approved']:
                raise UserError("You can only cancel transfers in Submitted or Approved states.")
            
            # Unreserve moves if needed (but don't delete them)
            if rec.state in ['assigned', 'confirmed']:
                rec.move_ids_without_package._do_unreserve()
            
            # Set to cancelled state to show reset button
            rec.write({
                'approval_state': 'cancelled',
                'reject_reason': False,
            })
            
            # Post message
            rec.message_post(body="Transfer has been cancelled. Click 'Reset to Draft' to continue.")
        
        # Return action to reload the view
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


    def action_reset_to_draft(self):
        """Reset from cancelled state back to draft"""
        for rec in self:
            if rec.approval_state != 'cancelled':
                raise UserError("You can only reset transfers from Cancelled state.")
            
            # Reset to draft - preserve all move lines
            rec.write({
                'approval_state': 'draft',
                'reject_reason': False,
            })
            
            # Set picking state back to draft
            rec.state = 'draft'
            
            # Post message
            rec.message_post(body="Transfer has been reset to Draft state.")
        
        # Reload the view
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }



    # BLOCK VALIDATION IF NOT APPROVED
    def button_validate(self):
        for picking in self:

            # Find related request
            request = self.env['stationery.request'].search(
                [('name', '=', picking.origin)],
                limit=1
            )

            # Block ONLY if linked to a request
            if (
                    request
                    and picking.is_stationery_transfer
                    and not self.env.context.get('from_request_delivery')
            ):
                raise UserError(
                    "Stock movement is controlled by the Request. "
                    "Use 'Mark as Delivered' from the Stationery Request."
                )

        return super().button_validate()

    def action_transfer_stationery(self):
        for picking in self:
            if picking.approval_state != 'approved':
                raise UserError("Only GM Approved transfers can be processed.")

            # ========================
            # FLOW 1: Created from Request
            # ========================
            if picking.is_stationery_transfer and picking.origin:
                request = self.env['stationery.request'].search(
                    [('name', '=', picking.origin)], limit=1
                )
                if not request:
                    raise UserError("Related Stationery Request not found.")

                for line in request.line_ids:
                    move_line = picking.move_ids_without_package.filtered(
                        lambda m: m.product_id == line.product_id
                    )
                    if move_line:
                        line.delivered_qty = move_line.product_uom_qty

                request.state = 'in_progress'
                picking.approval_state = 'transferred'
                picking.message_post(body="Logical delivery done. Waiting for physical stock movement.")

            # ========================
            # FLOW 2: Manual Transfer (No Request)
            # ========================
            else:
                if picking.state == 'draft':
                    picking.action_confirm()

                for move in picking.move_ids_without_package:
                    # Ensure at least one move line exists
                    if not move.move_line_ids:
                        self.env['stock.move.line'].create({
                            'picking_id': picking.id,
                            'move_id': move.id,
                            'product_id': move.product_id.id,
                            'product_uom_id': move.product_uom.id,
                            'location_id': picking.location_id.id,
                            'location_dest_id': picking.location_dest_id.id,
                            'qty_done': move.product_uom_qty,
                        })
                    else:
                        for ml in move.move_line_ids:
                            ml.qty_done = move.product_uom_qty

                # Validate without reservation
                picking.with_context(
                    from_request_delivery=True,
                    skip_immediate=True
                ).button_validate()

                picking.approval_state = 'done'
                picking.message_post(body="Manual stationery transfer completed.")

            return True



    # AUTO UPDATE REQUEST IF EXISTS
    def _action_done(self):
        res = super()._action_done()
        return res



    def action_check_department_stock(self):
        self.ensure_one()

        # Order line products
        products = self.move_ids_without_package.mapped('product_id')
        department_location = self.location_dest_id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Department Stock',
            'res_model': 'stock.quant',
            'view_mode': 'tree,form',
            'domain': [
                ('product_id', 'in', products.ids),
                ('location_id', '=', department_location.id),
            ],
            'context': {
                'search_default_on_hand': 1,
            }
        }
    
    def action_view_request(self):
        """View the related stationery request"""
        self.ensure_one()
        
        # Find the related request
        request = self.env['stationery.request'].search([
            ('name', '=', self.origin)
        ], limit=1)
        
        if not request:
            raise UserError("No related Stationery Request found.")
        
        # Return action to open the request
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stationery Request',
            'res_model': 'stationery.request',
            'view_mode': 'form',
            'res_id': request.id,
            'target': 'current',
            'context': {'active_id': request.id},
        }

    def action_create_purchase_order(self):
        """Create Purchase Order from Transfer"""
        self.ensure_one()

        if not self.move_ids_without_package:
            raise UserError("No products found in this transfer.")

        # Check if vendor exists, if not create or use default
        vendor = self.env['res.partner'].search([
            ('name', '=', 'Default Vendor')
        ], limit=1)

        if not vendor:
            # Create a default vendor if none exists
            vendor = self.env['res.partner'].create({
                'name': 'Default Vendor',
                'supplier_rank': 1,
                'company_type': 'company',
            })

        # Create new purchase order with vendor
        purchase_order = self.env['purchase.order'].create({
            'partner_id': vendor.id,  # ✅ Required field
            'date_order': fields.Datetime.now(),
            'origin': self.name,
            'office_location_id': self.location_id.id,
            'requester_name': self.env.user.employee_id.id if self.env.user.employee_id else False,
        })

        # Create purchase order lines from transfer moves
        for move in self.move_ids_without_package:
            self.env['purchase.order.line'].create({
                'order_id': purchase_order.id,
                'product_id': move.product_id.id,
                'name': move.product_id.display_name,
                'product_qty': move.product_uom_qty,
                'product_uom': move.product_uom.id,
                'price_unit': move.product_id.standard_price or 0.0,
                'date_planned': fields.Datetime.now(),
                'taxes_id': [(6, 0, move.product_id.supplier_taxes_id.ids)] if move.product_id.supplier_taxes_id else False,
            })

        # Open the newly created purchase order
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order',
            'res_model': 'purchase.order',
            'res_id': purchase_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_return(self):
        """Create Stationery Return from Transfer"""
        self.ensure_one()

        # Create return lines from transfer moves
        return_lines = []
        for move in self.move_ids_without_package:
            return_lines.append((0, 0, {
                'product_id': move.product_id.id,
                'return_qty': move.product_uom_qty,
                'remark': move.line_remark or '',
            }))

        # Create new stationery return with transfer data
        return_obj = self.env['stationery.return'].create({
            'from_department_id': self.to_department_id.id,
            'from_location_id': self.location_dest_id.id,
            'to_department_id': self.from_department_id.id,
            'to_location_id': self.location_id.id,
            'source_transfer_id': self.id,  # ✅ Use source_transfer_id
            'remark': f"Return from transfer {self.name}",
            'ga_pic_feedback': self.ga_pic_feedback,
            'operation_type': 'internal',
            'line_ids': return_lines,
        })

        # Open the newly created return form
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stationery Return',
            'res_model': 'stationery.return',
            'res_id': return_obj.id,
            'view_mode': 'form',
            'target': 'current',
        }