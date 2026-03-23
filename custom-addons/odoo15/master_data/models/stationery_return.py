from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

class StationeryReturn(models.Model):
    _name = 'stationery.return'
    _description = 'Stationery Return'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(
        string='Return Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    picking_move_ids = fields.One2many(
        related='picking_id.move_ids_without_package',
        string='Transfer Moves',
        readonly=True
    )
    
    def action_view_transfer(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transfer',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    return_date = fields.Datetime(
        string='Return Date',
        default=fields.Datetime.now,
        required=True
    )
    
    operation_type = fields.Selection([
        ('customer', 'Customer Returns'),
        ('supplier', 'Supplier Returns'),
        ('internal', 'Internal Returns'),
        ('damaged', 'Damaged Goods'),
    ], string='Operation Type', required=True, default='internal')
    
    from_department_id = fields.Many2one(
        'hr.department',
        string='From BU/BR/DIV',
        required=True
    )
    
    from_location_id = fields.Many2one(
        'stock.location',
        string='From Location',
        domain="[('usage', '=', 'internal')]",
        required=True
    )
    
    to_department_id = fields.Many2one(
        'hr.department',
        string='To BU/BR/DIV',
        required=True
    )
    
    to_location_id = fields.Many2one(
        'stock.location',
        string='To Location',
        domain="[('usage', '=', 'internal')]",
        required=True
    )
    
    remark = fields.Text(string='Remark')
    ga_pic_feedback = fields.Text(string='GA PIC Feedback')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('done', 'Done'),
    ], default='draft', tracking=True)
    
    line_ids = fields.One2many(
        'stationery.return.line',
        'return_id',
        string='Return Lines'
    )
    
    # Source Transfer (from transfer form)
    source_transfer_id = fields.Many2one(
        'stock.picking',
        string='Source Transfer',
        readonly=True
    )

    # Return Transfer (created by return)
    picking_id = fields.Many2one(
        'stock.picking',
        string='Return Picking',
        readonly=True
    )
    
    total_products = fields.Integer(
        compute='_compute_totals',
        string='Total Products'
    )
    
    total_qty = fields.Float(
        compute='_compute_totals',
        string='Total Quantity'
    )
    
    @api.depends('line_ids')
    def _compute_totals(self):
        for rec in self:
            rec.total_products = len(rec.line_ids)
            rec.total_qty = sum(rec.line_ids.mapped('return_qty'))
    
    # @api.model
    # def create(self, vals):
    #     if not vals.get('name') or vals.get('name') == 'New':
    #         vals['name'] = self.env['ir.sequence'].next_by_code('stationery.return') or 'New'
    #     return super().create(vals)

    @api.model
    def create(self, vals):
        # Always generate sequence if name is not explicitly provided
        if not vals.get('name') or vals.get('name') == 'New':
            sequence = self.env['ir.sequence'].next_by_code('stationery.return')
            if sequence:
                vals['name'] = sequence
            else:
                # Fallback if sequence not found
                vals['name'] = 'RET/' + fields.Datetime.now().strftime('%Y%m%d/%H%M%S')
        return super().create(vals)
    
    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Please add at least one product to return.")
            rec.state = 'submitted'
    
    def action_approve(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError("Only submitted returns can be approved.")

            rec._create_return_picking()
            rec.state = 'done'
    
    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'
    
    # def action_done(self):
    #     for rec in self:
    #         rec.state = 'done'
    
    # def _create_return_picking(self):
    #     """Create stock picking for return and auto-validate it"""
    #     for rec in self:
    #         if rec.picking_id:
    #             raise UserError("Return picking already created.")
            
    #         # Find return picking type by name
    #         return_type = self.env['stock.picking.type'].search([
    #             ('name', '=', 'Stationery Return'),
    #             ('code', '=', 'internal')
    #         ], limit=1)
            
    #         # If not found, create it
    #         if not return_type:
    #             return_type = self.env['stock.picking.type'].create({
    #                 'name': 'Stationery Return',
    #                 'sequence_code': 'RET',
    #                 'sequence': 110,
    #                 'code': 'internal',
    #                 'warehouse_id': self.env.ref('stock.warehouse0').id,
                    
    #                 'default_location_src_id': self.env.ref('stock.stock_location_stock').id,
    #                 'default_location_dest_id': self.env.ref('stock.stock_location_stock').id,
    #                 'color': 4,
    #             })
            
    #         # Create picking
    #         picking = self.env['stock.picking'].create({
    #             'picking_type_id': return_type.id,
    #             'location_id': rec.from_location_id.id,
    #             'location_dest_id': rec.to_location_id.id,
    #             'origin': rec.name,
    #             'is_stationery_transfer': True,
    #             # 'transfer_type': 'return',
    #             'from_department_id': rec.from_department_id.id,
    #             'to_department_id': rec.to_department_id.id,
    #             'remark': rec.remark,
    #             'ga_pic_feedback': rec.ga_pic_feedback,
    #         })

    #         # Bypass GM approval for return transfers
    #         picking.approval_state = 'approved'

    #         # Create stock moves and set quantity_done immediately
    #         for line in rec.line_ids:
    #             move = self.env['stock.move'].create({
    #                 'name': line.product_id.display_name,
    #                 'product_id': line.product_id.id,
    #                 'product_uom_qty': line.return_qty,
    #                 'product_uom': line.product_id.uom_id.id,
    #                 'location_id': picking.location_id.id,
    #                 'location_dest_id': picking.location_dest_id.id,
    #                 'picking_id': picking.id,
    #                 'is_stationery_transfer': True,
    #             })
    #             # Crucial: set the done quantity so validation actually moves stock
    #             move.quantity_done = line.return_qty

    #         # Validate the picking – this will now move stock
    #         picking.button_validate()

    #         rec.picking_id = picking.id
    #         rec.state = 'done'

    def _create_return_picking(self):
        for rec in self:

            # ==========================================
            # 1️⃣ Prevent duplicate picking
            # ==========================================
            if rec.picking_id:
                raise UserError("Return picking already created.")

            if not rec.line_ids:
                raise UserError("Please add at least one product to return.")

            # ==========================================
            # 2️⃣ Validate return quantity
            # ==========================================
            for line in rec.line_ids:
                if line.return_qty <= 0:
                    raise UserError(
                        f"Return quantity must be greater than zero "
                        f"for {line.product_id.display_name}."
                    )

            # ==========================================
            # 3️⃣ Validate stock availability
            # (Same philosophy as transfer logic)
            # ==========================================
            for line in rec.line_ids:
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', rec.from_location_id.id)
                ])

                available_qty = sum(
                    quants.mapped(lambda q: q.quantity - q.reserved_quantity)
                )

                if available_qty < line.return_qty:
                    raise UserError(
                        f"Not enough stock for {line.product_id.display_name}. "
                        f"Available: {available_qty}, "
                        f"Trying to return: {line.return_qty}"
                    )

            # ==========================================
            # 4️⃣ Get Picking Type (from XML)
            # ==========================================
            return_type = self.env.ref(
                'stationery.stock_picking_type_stationery_return'
            )

            # ==========================================
            # 5️⃣ Create Picking
            # ==========================================
            picking = self.env['stock.picking'].create({
                'picking_type_id': return_type.id,
                'location_id': rec.from_location_id.id,
                'location_dest_id': rec.to_location_id.id,
                'origin': rec.name,
                'is_stationery_transfer': True,
                'from_department_id': rec.from_department_id.id,
                'to_department_id': rec.to_department_id.id,
                'remark': rec.remark,
                'ga_pic_feedback': rec.ga_pic_feedback,
                'approval_state': 'approved',  # bypass GM for return
            })

            # ==========================================
            # 6️⃣ Create Stock Moves
            # ==========================================
            for line in rec.line_ids:
                self.env['stock.move'].create({
                    'name': line.product_id.display_name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.return_qty,
                    'product_uom': line.product_id.uom_id.id,
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'picking_id': picking.id,
                    'is_stationery_transfer': True,
                })

            # ==========================================
            # 7️⃣ Confirm Picking
            # ==========================================
            picking.action_confirm()

            # ==========================================
            # 8️⃣ Assign Stock
            # ==========================================
            picking.action_assign()

            # ==========================================
            # 9️⃣ Set Done Quantity
            # ==========================================
            for move in picking.move_ids_without_package:
                move.quantity_done = move.product_uom_qty

            # ==========================================
            # 🔟 Validate Picking
            # ==========================================
            picking.button_validate()

            # ==========================================
            # 1️⃣1️⃣ Link back & finalize
            # ==========================================
            rec.picking_id = picking.id
            rec.state = 'done'

            # Post message to source transfer (if exists)
            if rec.source_transfer_id:
                rec.source_transfer_id.message_post(
                    body=f"Return {rec.name} has been completed."
                )

    @api.onchange('from_department_id')
    def _onchange_from_department(self):
        if self.from_department_id and self.from_department_id.stock_location_id:
            self.from_location_id = self.from_department_id.stock_location_id   # record, not id

    @api.onchange('to_department_id')
    def _onchange_to_department(self):
        if self.to_department_id and self.to_department_id.stock_location_id:
            self.to_location_id = self.to_department_id.stock_location_id       # record, not id

    @api.constrains('from_department_id', 'to_department_id')
    def _check_same_department(self):
        for rec in self:
            if rec.from_department_id == rec.to_department_id:
                raise UserError("From and To Department cannot be the same.")
    

class StationeryReturnLine(models.Model):
    _name = 'stationery.return.line'
    _description = 'Stationery Return Line'

    return_id = fields.Many2one(
        'stationery.return',
        string='Return',
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('type', '=', 'product')]
    )
    
    return_qty = fields.Float(
        string='Return Qty',
        required=True,
        default=1.0
    )
    
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True
    )
    
    remark = fields.Char(string='Remark')