from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


class StationeryRequest(models.Model):
    _name = 'stationery.request'
    _description = 'Stationery Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'



    name = fields.Char(string='Request Reference', required=True, copy=False, readonly=True, default='New')
    #Requested
    requested_by = fields.Many2one('hr.employee', string="Requested By",
                                   domain="""
                                           [
                                               ('department_id','=',user_employee_department_id),
                                               ('business_unit_ids','in',business_unit_ids)
                                           ]
                                       """,
                                   required=True)
    user_employee_department_id = fields.Many2one('hr.department', compute='_compute_user_department')
    contact = fields.Char(related='requested_by.work_phone', string="Phone", store=True)
    department_id = fields.Many2one('hr.department', related='requested_by.department_id',
                                    string="Department", store=True, readonly=True)
    company_id = fields.Many2one('res.company', 'Holding Business', default=lambda self: self.env.company, index=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', store=True, readonly=False)
    business_unit_ids = fields.Many2many(related='requested_by.business_unit_ids', string="Business Units", readonly=True)
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now, required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    line_ids = fields.One2many('stationery.request.line','request_id', string='Items Requested')
    #Approve & Reject
    approved_by = fields.Many2one('res.users', string='Approved By')
    approved_date = fields.Datetime(string='Approval Date')
    rejected_by = fields.Many2one('res.users', string='Rejected By', readonly=True)
    rejected_date = fields.Datetime(string='Rejected Date', readonly=True)
    reject_reason = fields.Text(string='Rejection Reason', readonly=True)
    readonly_state = fields.Boolean(string='Readonly', compute='_compute_readonly_state',
                                    help='Controls if the form is readonly')
    stock_location_id = fields.Many2one('stock.location', string='Stock Location', domain="[('id','in', allowed_location_ids)]",
                                        help="Destination stock location for this stationery request.", required='True')
    # Notes
    notes = fields.Text(string='Remark')
    picking_id = fields.Many2one('stock.picking', string="Transfer", readonly=True)
    allowed_location_ids = fields.Many2many('stock.location',
        compute='_compute_allowed_locations')

    def _compute_user_department(self):
        for rec in self:
            rec.user_employee_department_id = self.env.user.employee_id.department_id

    @api.depends('employee_id')
    def _compute_allowed_locations(self):
        for rec in self:
            if rec.employee_id and rec.employee_id.business_unit_ids:
                rec.allowed_location_ids = rec.employee_id.business_unit_ids.mapped('bu_br_div_loc')
            else:
                rec.allowed_location_ids = False



    # ========== COMPUTE READONLY STATE ==========
    @api.depends('state')
    def _compute_readonly_state(self):
        for record in self:
            record.readonly_state = record.state not in ['draft', 'submitted', 'rejected', 'cancelled']


    # @api.onchange('department_id')
    # def _onchange_department_filter_user(self):
    #     if self.department_id:
    #         employees = self.env['hr.employee'].search([
    #             ('department_id', '=', self.department_id.id)
    #         ])
    #         user_ids = employees.mapped('user_id').ids
    #         return {
    #             'domain': {
    #                 'requested_by': [('id', 'in', user_ids)]
    #             }
    #         }

    @api.onchange('requested_by')
    def _onchange_requested_by(self):
        user_employee = self.env.user.employee_id

        if user_employee:
            return {
                'domain': {
                    'requested_by': [
                        ('department_id', '=', user_employee.department_id.id),
                        ('business_unit_ids', 'in', user_employee.business_unit_ids.ids)
                    ]
                }
            }


    #_________________Compute Requested By with Users_____________________
    @api.depends('requested_by')
    def _compute_allowed_locations(self):
        for rec in self:
            if rec.requested_by and rec.requested_by.business_unit_ids:
                rec.allowed_location_ids = rec.requested_by.business_unit_ids.mapped('bu_br_div_loc')
            else:
                rec.allowed_location_ids = False

    #__________________State Methods___________________

    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Cannot submit an empty request. Please add at least one item.")

            if rec.name == 'New':
                rec.name = self.env['ir.sequence'].next_by_code('stationery.request')

            rec.state = 'submitted'

    def action_approve(self):
        for request in self:
            if request.picking_id:
                raise UserError("Transfer already created for this request.")

        if not request.line_ids:
            raise UserError("Please add at least one item.")

        picking_type = self.env.ref('stock.picking_type_internal')

        src = picking_type.default_location_src_id
        dest = request.stock_location_id  # Department stock

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
        # picking.action_confirm() #This line will make transfer form to confirm state but wil conflict with transfer's available_qty
        request.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
            'picking_id': picking.id,
        })

    def action_view_transfer(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transfer',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.picking_id.id,
        }

    def action_reject(self):
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
        self.write({'state': 'cancelled'})

    def action_mark_in_progress(self):
        for request in self:
            for line in request.line_ids:
                line.delivered_qty = line.quantity

            request.state = 'in_progress'

    def action_mark_delivered(self):
        self.ensure_one()

        if not self.picking_id:
            raise UserError("No transfer exists for this request.")

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


    def action_reset_to_draft(self):
        if self.state in ['approved', 'rejected', 'cancelled']:
            self.write({
                'state': 'draft',
                'approved_by': False,
                'approved_date': False
            })

    def action_open_inventory_check(self):
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

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.department_id and hasattr(self.department_id, 'stock_location_id'):
            self.stock_location_id = self.department_id.stock_location_id






    # ==========________________ CONSTRAINTS _________________==========
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

    @api.constrains('stock_location_id', 'employee_id')
    def _check_stock_location_matches_bu(self):
        for rec in self:
            if rec.employee_id and rec.stock_location_id:
                allowed_locations = rec.employee_id.business_unit_ids.mapped('bu_br_div_loc')
                if rec.stock_location_id not in allowed_locations:
                    raise ValidationError(
                        "Selected stock location does not belong to employee's Business Units."
                    )












class stationeryRequestLine(models.Model):
    _name = 'stationery.request.line'
    _description = 'stationery Request Line'


    request_id = fields.Many2one('stationery.request', string='Request', ondelete='cascade', required=True)
    request_state = fields.Selection(related='request_id.state', string='Request State', store=True, readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, domain="[('categ_id.name', 'ilike', 'stationery')]")
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True, store=True)
    quantity = fields.Float(string='Quantity', required=True, default=1.0)
    delivered_qty = fields.Float(string='Delivered Quantity', readonly=True, default=0.0)
    notes = fields.Char(string='Line Notes')
    available_qty = fields.Float(
        string='Available Qty',
        readonly=True
    )

    # @api.depends('product_id', 'request_id.stock_location_id')
    # def _compute_available_qty(self):
    #     for line in self:
    #         if line.product_id and line.request_id.stock_location_id:
    #             quants = self.env['stock.quant'].search([
    #                 ('product_id', '=', line.product_id.id),
    #                 ('location_id', '=', line.request_id.stock_location_id.id)
    #             ])
    #             # line.available_qty = sum(quants.mapped(lambda q: q.quantity - q.reserved_quantity))
    #             line.available_qty = sum(quants.mapped(lambda q: q.quantity))
    #         else:
    #             line.available_qty = 0.0




    # ==============================CONSTRAINTS ==================================
    @api.constrains('quantity')
    def _check_quantity(self):
        """Ensure quantity is positive"""
        for line in self:
            if line.quantity <= 0:
                raise ValidationError("Quantity must be greater than 0.")



    # ==========================WRITE METHOD OVERRIDE=================================
    def write(self, vals):
        for line in self:
            if line.request_state not in ['draft', 'submitted']:
                if set(vals) - {'delivered_qty'}:
                    raise UserError(
                        "You can only modify product lines in Draft or Submitted state."
                    )
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
        return super(stationeryRequestLine, self).unlink()

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






