from odoo import models, fields, api
from odoo.exceptions import AccessDenied
from ..user_jwt_request import jwt_request
import logging
_logger = logging.getLogger(__name__)

class Users(models.Model):
    _inherit = "res.users"

    access_token_ids = fields.One2many(
        string='Access Tokens',
        comodel_name='jwt_provider.access_token',
        inverse_name='user_id',
    )

    refresh_token_ids = fields.One2many(
        string='Refresh Tokens',
        comodel_name='jwt_provider.refresh_token',
        inverse_name='user_id',
    )
    
    @api.model
    def _check_credentials(self, password, user_agent_env={}):
        try:
            super(Users, self)._check_credentials(password, user_agent_env)
        except AccessDenied:
            # verify password as token
            if not jwt_request.verify(password):
                raise