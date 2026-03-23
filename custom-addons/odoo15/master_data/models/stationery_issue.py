from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError

class InternalIssueRequest(models.Model):
    _name = 'internal.issue.request'
    _description = 'Internal Issue Request'
    _rec_name = 'name'

    # ======================
    # BASIC FIELDS
    # ======================
    name = fields.Char(string="Request Reference", copy=False, readonly=True, default='New')
    company_id = fields.Many2one('res.company', string="BU / BR / DIV", default=lambda self: self.env.company, required=True)
    issue_date = fields.Date(string="Issue Date", default=fields.Date.context_today, required=True)

    office_location_id = fields.Many2one(
        'stock.location',
        string="Office Location",
        required=True
    )

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string="BU / BR / DIV Location",
        domain="[('company_id','=',company_id)]",
        required=True
    )

    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string="Operation Type",
        domain="[('code','=','internal')]",
        required=True
    )

    sequence_id = fields.Many2one(
        'ir.sequence',
        string="Sequence",
        domain="[('code','=','internal.issue.request'), '|', ('company_id','=',company_id), ('company_id','=',False)]",
        required=True
    )

    issue_photo = fields.Binary(string="Issue Photo", attachment=True)
    remark = fields.Text(string="Remark")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
    ], default='draft', tracking=True)

    line_ids = fields.One2many(
        'internal.issue.request.line',
        'request_id',
        string="Issue Lines"
    )

    # ======================
    # ONCHANGE METHODS
    # ======================
    @api.onchange('office_location_id')
    def _onchange_office_location_id(self):
        """Auto-fill picking type and warehouse based on office location"""
        if self.office_location_id:
            # Find warehouse for this office location
            warehouse = self.env['stock.warehouse'].search([
                ('lot_stock_id', '=', self.office_location_id.id)
            ], limit=1)
            if warehouse:
                self.warehouse_id = warehouse.id
                # Find picking type only for Internal Issue sequence
                picking_type = self.env['stock.picking.type'].search([
                    ('sequence_code', '=', 'internal.issue.request'),
                    '|', ('warehouse_id', '=', warehouse.id), ('warehouse_id', '=', False)
                ], limit=1)
                if picking_type:
                    self.picking_type_id = picking_type.id

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Auto-select sequence based on company"""
        seq = self.env['ir.sequence'].search([
            ('code', '=', 'internal.issue.request'),
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)
        ], limit=1)
        if seq:
            self.sequence_id = seq.id

    # ======================
    # CREATE METHOD
    # ======================
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            prefix = 'GEN'  # fallback prefix
            if vals.get('office_location_id'):
                location = self.env['stock.location'].browse(vals['office_location_id'])
                prefix = location.name.split('/')[0]  # first part of location name, e.g., 'YGN' or 'MDY'
            
            # use the sequence and pass prefix in context
            seq = self.env['ir.sequence'].search([('code', '=', 'internal.issue.request')], limit=1)
            if not seq:
                raise UserError("No sequence found for Internal Issue Request")
            vals['name'] = seq.with_context(prefix=prefix).next_by_id()

        return super().create(vals)

    # ======================
    # BUTTON METHODS
    # ======================
    def action_submit(self):
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'submitted'

    def action_approve(self):
        for rec in self:
            if not self.env.user.has_group('purchase.group_purchase_manager'):
                raise UserError("Only managers can approve this request.")
            rec.state = 'approved'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'

    # ======================
    # OVERRIDE WRITE / UNLINK
    # ======================
    def write(self, vals):
        for rec in self:
            if rec.state == 'approved' and ('state' not in vals or vals['state'] != 'draft'):
                raise UserError("Cannot edit an approved request. Reset to draft first.")
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.state == 'approved':
                raise UserError("Cannot delete an approved request. Reset to draft first.")
        return super().unlink()


class InternalIssueRequestLine(models.Model):
    _name = 'internal.issue.request.line'
    _description = 'Internal Issue Request Line'

    request_id = fields.Many2one(
        'internal.issue.request',
        string="Request Reference",
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'product.product',
        string="Product",
        required=True
    )

    remaining_qty = fields.Float(
        string="Remaining Qty",
        compute="_compute_remaining_qty",
        store=True
    )

    issue_qty = fields.Float(
        string="Issue Qty",
        required=True
    )

    uom_id = fields.Many2one('uom.uom', string="UoM")
    department = fields.Char(string="Department")
    received_by = fields.Many2one('hr.employee', string="Received By")    
    remark = fields.Char(string="Remark")
    location_id = fields.Many2one('stock.location', string="Location", store=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id

    @api.depends('product_id', 'request_id.office_location_id', 'issue_qty', 'request_id.state')
    def _compute_remaining_qty(self):
        for line in self:
            if line.product_id and line.request_id.office_location_id:
                loc = line.request_id.office_location_id
                physical_qty = line.product_id.with_context(location=loc.id).qty_available
                issued_total = sum(
                    self.env['internal.issue.request.line'].search([
                        ('product_id', '=', line.product_id.id),
                        ('request_id.office_location_id', '=', loc.id),
                        ('request_id.state', '=', 'approved')
                    ]).mapped('issue_qty')
                )
                line.remaining_qty = max(physical_qty - issued_total, 0)
            else:
                line.remaining_qty = 0