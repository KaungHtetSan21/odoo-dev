import jwt
from odoo.http import request
import logging
_logger = logging.getLogger(__name__) 

def access_key():
    access_key = request.env['key.config'].search([]).access_key
    return access_key

def refresh_key():
    refresh_key = request.env['key.config'].search([]).refresh_key
    return refresh_key


def sign_token(payload):
    token = jwt.encode(
        payload,
        access_key(),
        algorithm='HS256'
    )
    return token.decode('utf-8')

def sign_refresh_token(payload):
    refresh_token = jwt.encode(
        payload,
        refresh_key(),
        algorithm='HS256'
    )
    return refresh_token.decode('utf-8')

def decode_access_token(token):
    return jwt.decode(token, access_key())

def decode_refresh_token(token):
    return jwt.decode(token,refresh_key())

