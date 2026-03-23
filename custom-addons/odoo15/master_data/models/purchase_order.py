from odoo import models, fields, api
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # --------------------------
    # Extra Fields
    # --------------------------
    purchase_request_date = fields.Date(
        string="Purchase Request Date",
        default=fields.Date.context_today,
        store=True
    )
    purchase_approve_date = fields.Date(
        string="Purchase Approve Date",
        default=fields.Date.context_today,
        store=True
    )
    
    manager_name = fields.Many2one('hr.employee', string='Manager', store=True)
    approve_by = fields.Many2one(
        'res.users',
        string="Approved By",
        readonly=True,
        store=True,
        default=lambda self: self.env.user
    )
    
    
    
    
    # holding_business = fields.Many2one(
    #     'stock.warehouse',
    #     string="Holding Business",
    #     required=True
    # )

    # @api.model
    # def _default_office_location(self):
    #     # In default, we pick the first warehouse for the current user as holding business
    #     warehouse = self.env['stock.warehouse'].search([], limit=1)
    #     if warehouse:
    #         # Get the stock location linked to this warehouse
    #         location = warehouse.lot_stock_id
    #         if location:
    #             return location.id
    #     return False

    # office_location_id = fields.Many2one(
    #     'stock.location',
    #     string='Office Location',
    #     required=True,
    #     default=_default_office_location
    # )
    
    


    holding_business = fields.Many2one(
        'stock.warehouse',
        string="Holding Business",
        required=True,
        default=lambda self: self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
    )

    office_location_id = fields.Many2one(
        'stock.location',
        string='Office Location',
        required=True,
        domain=lambda self: self._domain_office_location(),
        default=lambda self: self._default_office_location()
    )

    # ======================
    # Default method
    # ======================
    @api.model
    def _default_office_location(self):
        hb = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        if hb and hb.lot_stock_id:
            return hb.lot_stock_id.id
        return False

    # ======================
    # Dynamic domain
    # ======================
    def _domain_office_location(self):
        if self.holding_business:
            return [('id', '=', self.holding_business.lot_stock_id.id)]
        return []

    # ======================
    # Update domain on onchange
    # ======================
    @api.onchange('holding_business')
    def _onchange_holding_business(self):
        if self.holding_business:
            # Get all internal locations under this warehouse
            locations = self.env['stock.location'].search([
                ('id', 'child_of', self.holding_business.view_location_id.id),
                ('usage', '=', 'internal')
            ])
            # Set the domain for the office_location_id field
            self.office_location_id = self.holding_business.lot_stock_id  # auto-set default
            return {'domain': {'office_location_id': [('id', 'in', locations.ids)]}}
        else:
            self.office_location_id = False
            return {'domain': {'office_location_id': []}}
    
    
    
    
    
    
    
    
    
    
    
    
    
    total_purchase_amount = fields.Float(
        string="Total Purchase Amount",
        compute='_compute_total_purchase_amount',
        store=True
    )
    remark = fields.Text(string="Remark", store=True)
    manager_remark = fields.Text(string="Manager Remark", store=True)
    management_approval = fields.Binary(string="Management Approval", attachment=True , store=True)
    ask_approval = fields.Boolean(string="Ask Approval", default=False)
    manager_approved = fields.Boolean(string="Manager Approved", default=False)
    approval_locked = fields.Boolean(string="Approval Locked", default=False)
    requester_name = fields.Many2one(
        'hr.employee',
        string="Employee",
        default=lambda self: self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1
        ),
    )
    

    # --------------------------
    # Default Values
    # --------------------------
    
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        office_loc = self.env['stock.location'].search([('name', '=', 'Office Stock')], limit=1)
        if office_loc:
            defaults['office_location_id'] = office_loc.id
        return defaults
    

    # --------------------------
    # Compute Total Amount
    # --------------------------
    @api.depends('amount_total')
    def _compute_total_purchase_amount(self):
        for order in self:
            order.total_purchase_amount = order.amount_total

    # --------------------------
    # Extend states properly
    # --------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_confirmation', 'Waiting Confirmation'),
        ('approved', 'Approved'),
        ('denied','Denied'),
        ('sent', 'RFQ Sent'),
        # ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True,
    tracking=True, default='draft')

    # --------------------------
    # Manager requests confirmation
    # --------------------------
    def button_request_confirmation(self):
        for order in self:
            if order.state != 'draft':
                continue
            order.write({
                'state': 'waiting_confirmation',
                'ask_approval': True
            })
        return True

    # --------------------------
    # Manager confirms order
    # --------------------------
    def button_manager_confirm_order(self):
        for order in self:
            if not self.env.user.has_group('purchase.group_purchase_manager'):
                raise UserError("Only managers can confirm this order!")

            if not order.approve_by:
                raise UserError("Manager Name is required.")

            if not order.management_approval:
                raise UserError("Management Approval image is required.")

            # Set approved state and lock
            order.write({
                'manager_approved': True,
                'approval_locked': True,
                'state': 'approved'
            })
            order.message_post(body="Manager approved this order")

        return True

    # --------------------------
    # Manager declines order
    # --------------------------
    
    decline_reason = fields.Selection([
    ('location_unavailable', 'Location unavailable'),
    ('requirement_error', 'Requirements error'),
    ('exceed_quantity', 'Exceed the expected quantity'),
    ('quantity_enough', 'Available quantity still enough'),
    ('other', 'Other'),
    ], string="Decline Reason", readonly=True)

    decline_reason_note = fields.Text(string="Decline Details", readonly=True)

    declined_by = fields.Many2one(
        'res.users',
        string="Declined By",
        readonly=True
    )

    declined_date = fields.Datetime(
        string="Declined On",
        readonly=True
    )
        
    def action_open_decline_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.decline.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_id': self.id,
            }
        }
            
    def button_set_to_draft(self):
        for rec in self:
            rec.write({
                'state': 'draft'
            })
            rec.message_post(body="Order reset to Draft")

    # --------------------------
    # Override Confirm
    # --------------------------
    def button_confirm(self):
        for order in self:
            if order.total_purchase_amount >= 2000:
                # Require manager approval for high-value POs
                if not order.manager_approved:
                    raise UserError("Manager approval required before confirming this order.")
                
            if order.state == 'approved':
                order.state = 'draft'

 
        return super().button_confirm()
    
    def action_create_invoice(self):
        for order in self:
            # 1️⃣ Ensure PO is confirmed (creates pickings)
            if order.state in ('draft', 'approved'):
                super(PurchaseOrder, order).button_confirm()

            # 2️⃣ Auto-receive products if needed
            for picking in order.picking_ids.filtered(
                lambda p: p.picking_type_id.code == 'incoming'
                and p.state not in ('done', 'cancel')
            ):
                for move in picking.move_ids_without_package:
                    if move.product_id.tracking != 'none':
                        raise UserError(
                            f"Product {move.product_id.display_name} requires lot/serial number."
                        )
                    move.quantity_done = move.product_uom_qty

                picking.with_context(skip_backorder=True).button_validate()

        # 3️⃣ Create vendor bill
        result = super(PurchaseOrder, self).action_create_invoice()

        # 4️⃣ Set invoice date + auto-post
        today = fields.Date.context_today(self)

        for order in self:
            for bill in order.invoice_ids.filtered(
                lambda m: m.move_type == 'in_invoice' and m.state == 'draft'
            ):
                if not bill.invoice_date:
                    bill.invoice_date = today
                bill.action_post()

        return result
    