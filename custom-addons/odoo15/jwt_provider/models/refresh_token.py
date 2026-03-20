from odoo import models, fields, api
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)


class JwtRefreshToken(models.Model):
    _name = 'jwt_provider.refresh_token'
    _description = 'Store Refresh Token'

    refresh_token = fields.Char('Refresh Token', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    expires = fields.Datetime('Expires', required=True)
    is_expired = fields.Boolean(compute='_compute_is_expired')

    @api.depends('expires')
    def _compute_is_expired(self):
        for token in self:
            token.is_expired = datetime.now() > token.expires