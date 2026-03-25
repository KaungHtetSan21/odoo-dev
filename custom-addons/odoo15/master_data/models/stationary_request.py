from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


class StationeryRequest(models.Model):
    _name = 'stationery.request'
    _description = 'Stationery Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Request Reference', required=True, copy=False, readonly=True, default='New')
    
    # ========== HIERARCHY FIELDS ==========
    business_unit_id = fields.Many2one(
        'business.unit',
        string='Business Unit',
        required=True,
        help="Select Business Unit first"
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        domain="[('business_unit_id', '=', business_unit_id)]",
        help="Departments under selected Business Unit"
    )
    
    requested_by = fields.Many2one(
        'hr.employee',
        string='Requested By',
        required=True,
        domain="[('department_id', '=', department_id)]",
        help="Employees under selected Department"
    )

    # picking_state = fields.Char(
    #     string='Transfer Status',
    #     related='picking_id.state',
    #     readonly=True,
    #     store=False
    # )
    
    contact = fields.Char(related='requested_by.work_phone', string="Phone", store=True)
    company_id = fields.Many2one('res.company', 'Holding Business', default=lambda self: self.env.company, index=True)
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now, required=True)
    
    # ========== STATE (In Progress ပါအောင် ပြင်ထား) ==========
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('delivered', 'Delivered'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    line_ids = fields.One2many('stationery.request.line', 'request_id', string='Items Requested')
    
    # Approve & Reject
    approved_by = fields.Many2one('res.users', string='Approved By')
    approved_date = fields.Datetime(string='Approval Date')
    rejected_by = fields.Many2one('res.users', string='Rejected By', readonly=True)
    rejected_date = fields.Datetime(string='Rejected Date', readonly=True)
    reject_reason = fields.Text(string='Rejection Reason', readonly=True)
    readonly_state = fields.Boolean(string='Readonly', compute='_compute_readonly_state')
    
    stock_location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        domain="[('id','in', allowed_location_ids)]",
        help="Destination stock location for this stationery request.",
        required=True
    )
    
    notes = fields.Text(string='Remark')
    picking_id = fields.Many2one('stock.picking', string="Transfer", readonly=True)
    allowed_location_ids = fields.Many2many('stock.location', compute='_compute_allowed_locations')

    # ========== ONCHANGE METHODS ==========
    
    @api.onchange('business_unit_id')
    def _onchange_business_unit_id(self):
        """Clear department and employee when business unit changes"""
        self.department_id = False
        self.requested_by = False
        if self.business_unit_id:
            return {
                'domain': {
                    'department_id': [('business_unit_id', '=', self.business_unit_id.id)]
                }
            }
        return {'domain': {'department_id': []}}
    
    @api.onchange('department_id')
    def _onchange_department_id(self):
        """Clear employee when department changes, and set stock location"""
        self.requested_by = False
        
        if self.department_id:
            if hasattr(self.department_id, 'stock_location_id'):
                self.stock_location_id = self.department_id.stock_location_id
            
            return {
                'domain': {
                    'requested_by': [('department_id', '=', self.department_id.id)]
                }
            }
        return {'domain': {'requested_by': []}}
    
    @api.onchange('requested_by')
    def _onchange_requested_by(self):
        """Update contact when employee changes"""
        if self.requested_by:
            self.contact = self.requested_by.work_phone

    # ========== COMPUTE METHODS ==========
    
    def _compute_readonly_state(self):
        for record in self:
            record.readonly_state = record.state not in ['draft', 'submitted', 'rejected', 'cancelled']
    
    @api.depends('requested_by')
    def _compute_allowed_locations(self):
        for rec in self:
            if rec.requested_by and rec.requested_by.department_id and rec.requested_by.department_id.business_unit_id:
                business_unit = rec.requested_by.department_id.business_unit_id
                if business_unit.bu_br_div_loc:
                    rec.allowed_location_ids = business_unit.bu_br_div_loc
                else:
                    rec.allowed_location_ids = False
            else:
                rec.allowed_location_ids = False

    # ========== STATE METHODS (In Progress Workflow) ==========
    
    def action_submit(self):
        """Submit request for approval"""
        for rec in self:
            if not rec.line_ids:
                raise UserError("Cannot submit an empty request. Please add at least one item.")
            
            if rec.name == 'New':
                rec.name = self.env['ir.sequence'].next_by_code('stationery.request')
            
            rec.state = 'submitted'
            rec.message_post(body="Request has been submitted for approval.")
    
    def action_approve(self):
        """Approve request and create transfer in draft state"""
        for request in self:
            if request.picking_id:
                raise UserError("Transfer already created for this request.")
            
            if not request.line_ids:
                raise UserError("Please add at least one item.")
            
            picking_type = self.env.ref('stock.picking_type_internal')
            src = picking_type.default_location_src_id
            dest = request.stock_location_id
            
            if not src or not dest:
                raise UserError("Source or destination stock location is not configured.")
            
            move_lines = []
            for line in request.line_ids:
                move_lines.append((0, 0, {
                    'name': line.product_id.display_name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_id.uom_id.id,
                    'location_id': src.id,
                    'location_dest_id': dest.id,
                }))
            
            picking_vals = {
                'picking_type_id': picking_type.id,
                'location_id': src.id,
                'location_dest_id': dest.id,
                'origin': request.name,
                'is_stationery_transfer': True,
                'approval_state': 'draft',
                'to_department_id': request.department_id.id,
                'move_ids_without_package': move_lines,
            }
            
            picking = self.env['stock.picking'].create(picking_vals)
            request.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
                'picking_id': picking.id,
            })
            request.message_post(body=f"Request has been approved. Transfer {picking.name} created.")
    
    def action_mark_in_progress(self):
        """Mark request as in progress and confirm the transfer"""
        for request in self:
            if not request.picking_id:
                raise UserError("No transfer exists for this request.")
            
            # Confirm the picking (Mark as Todo)
            if request.picking_id.state == 'draft':
                request.picking_id.action_confirm()
                request.message_post(body="Transfer has been confirmed and is ready for processing.")
            
            request.state = 'in_progress'
            request.message_post(body="Request is now in progress.")
    
    def action_mark_delivered(self):
        """Mark request as delivered and validate the transfer"""
        self.ensure_one()
        
        if not self.picking_id:
            raise UserError("No transfer exists for this request.")
        
        # Check if picking is in confirmed state, if not, confirm it
        if self.picking_id.state == 'draft':
            self.picking_id.action_confirm()
        
        # Assign stock
        self.picking_id.action_assign()
        
        # Open delivery wizard to confirm physical delivery
        wizard = self.env['stationery.delivery.wizard'].create({
            'request_id': self.id
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirm Delivery',
            'res_model': 'stationery.delivery.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }
    
    def action_reject(self):
        """Open reject wizard"""
        self.ensure_one()
        return {
            'name': 'Reject Request',
            'type': 'ir.actions.act_window',
            'res_model': 'stationery.request.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
            }
        }
    
    def action_cancel(self):
        """Cancel the request"""
        for request in self:
            if request.picking_id and request.picking_id.state not in ['done', 'cancel']:
                request.picking_id.action_cancel()
            request.state = 'cancelled'
            request.message_post(body="Request has been cancelled.")
    
    def action_reset_to_draft(self):
        """Reset request to draft state"""
        if self.state in ['approved', 'rejected', 'cancelled']:
            self.write({
                'state': 'draft',
                'approved_by': False,
                'approved_date': False,
                'picking_id': False,
            })
    
    def action_view_transfer(self):
        """View the associated transfer"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transfer',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.picking_id.id,
        }
    
    def action_open_inventory_check(self):
        """Check available stock"""
        self.ensure_one()
        product_ids = self.line_ids.mapped('product_id').ids
        
        domain = [
            ('product_id', 'in', product_ids),
            ('location_id.usage', '=', 'internal'),
        ]
        
        if self.stock_location_id:
            domain.append(('location_id', '=', self.stock_location_id.id))
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Available Stocks',
            'res_model': 'stock.quant',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('stationery.view_stock_quant_office_tree').id, 'tree'),
                (False, 'form'),
            ],
            'domain': domain if product_ids else [],
            'context': {
                'inventory_mode': True,
            },
        }

    # ========== CONSTRAINTS ==========
    
    @api.constrains('line_ids')
    def _check_line_ids(self):
        for request in self:
            if request.state in ['submitted', 'approved', 'in_progress'] and not request.line_ids:
                raise ValidationError("A request must have at least one item.")
    
    def unlink(self):
        for rec in self:
            if rec.state in ['approved', 'in_progress', 'delivered']:
                raise UserError("You cannot delete a request once it is approved or processed.")
        return super().unlink()
    
    @api.constrains('stock_location_id', 'requested_by')
    def _check_stock_location_matches_bu(self):
        for rec in self:
            if rec.requested_by and rec.stock_location_id:
                if rec.requested_by.department_id and rec.requested_by.department_id.business_unit_id:
                    allowed_location = rec.requested_by.department_id.business_unit_id.bu_br_div_loc
                    if rec.stock_location_id != allowed_location:
                        raise ValidationError(
                            "Selected stock location does not belong to the Business Unit."
                        )


class StationeryRequestLine(models.Model):
    _name = 'stationery.request.line'
    _description = 'Stationery Request Line'

    request_id = fields.Many2one('stationery.request', string='Request', ondelete='cascade', required=True)
    request_state = fields.Selection(related='request_id.state', string='Request State', store=True, readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, domain="[('categ_id.name', 'ilike', 'stationery')]")
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True, store=True)
    quantity = fields.Float(string='Quantity', required=True, default=1.0)
    delivered_qty = fields.Float(string='Delivered Quantity', readonly=True, default=0.0)
    notes = fields.Char(string='Line Notes')
    available_qty = fields.Float(string='Available Qty', readonly=True)

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError("Quantity must be greater than 0.")

    def write(self, vals):
        for line in self:
            if line.request_state not in ['draft', 'submitted']:
                if set(vals) - {'delivered_qty'}:
                    raise UserError("You can only modify product lines in Draft or Submitted state.")
        return super().write(vals)

    @api.model
    def create(self, vals):
        line = super().create(vals)
        if line.product_id and line.request_id.stock_location_id:
            quants = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.request_id.stock_location_id.id)
            ])
            line.available_qty = sum(quants.mapped('quantity'))
        return line

    def unlink(self):
        for line in self:
            if line.request_id.state in ['approved', 'in_progress', 'delivered']:
                raise UserError(
                    f"Cannot delete line items after request is approved. "
                    f"Request {line.request_id.name} is in {line.request_id.state} state."
                )
        return super(StationeryRequestLine, self).unlink()

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id and line.request_id.stock_location_id:
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', line.request_id.stock_location_id.id)
                ])
                line.available_qty = sum(quants.mapped('quantity'))
            else:
                line.available_qty = 0