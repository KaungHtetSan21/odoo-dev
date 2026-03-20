from odoo import http
from odoo.http import request


class BusinessUnitAPI(http.Controller):

    # ===================== GET ALL =====================
    @http.route('/api/business_units', type='json', auth='user', methods=['GET'], csrf=False)
    def get_business_units(self):
        records = request.env['business.unit'].sudo().search([])
        result = []

        for rec in records:
            result.append({
                'id': rec.id,
                'name': rec.name,
                'business_code': rec.business_code,
                'business_type': rec.business_type,
                'company_id': rec.company_id.id if rec.company_id else None,
                'company_name': rec.company_id.name if rec.company_id else '',
            })

        return {'data': result}


    # ===================== CREATE =====================
    @http.route('/api/business_units/create', type='json', auth='public', methods=['POST'], csrf=False)
    def create_business_unit(self, **kwargs):
        try:
            data = request.jsonrequest

            vals = {
                'name': data.get('name'),
                'business_code': data.get('business_code'),
                'business_type': data.get('business_type'),
                'company_id': data.get('company_id'),
                'bu_br_div_loc': data.get('location_id'),  # Changed from location_id
                'holding_business_id': data.get('warehouse_id'),  # Changed from warehouse_id
            }

            record = request.env['business.unit'].sudo().create(vals)

            return {
                'status': 'success',
                'id': record.id
            }

        except Exception as e:
            return {'error': str(e)}


# ===================== UPDATE =====================
    @http.route('/api/business_units/update/<int:rec_id>', type='json', auth='user', methods=['PUT'], csrf=False)
    def update_business_unit(self, rec_id, **kwargs):
        try:
            rec = request.env['business.unit'].sudo().browse(rec_id)

            if not rec.exists():
                return {'error': 'Record not found'}

            # request.jsonrequest ကနေ data ကိုယူမယ်
            data = request.jsonrequest
            print("DATA RECEIVED:", data)  # Log ထုတ်ကြည့်မယ်
            
            # Field အမည်တွေကိုပြင်ဆင်မယ်
            vals = {}
            
            if data.get('name'):
                vals['name'] = data['name']
                
            if data.get('business_code'):
                vals['business_code'] = data['business_code']
                
            if data.get('business_type'):
                vals['business_type'] = data['business_type']
                
            if data.get('company_id'):
                vals['company_id'] = data['company_id']
                
            # ဒီနေရာမှာ အရေးကြီးတယ် - location_id ကို bu_br_div_loc နဲ့ချိတ်မယ်
            if data.get('location_id'):
                vals['bu_br_div_loc'] = data['location_id']
                
            # warehouse_id ကို holding_business_id နဲ့ချိတ်မယ်
            if data.get('warehouse_id'):
                vals['holding_business_id'] = data['warehouse_id']

            # Update လုပ်မယ်
            if vals:
                rec.write(vals)
                return {'status': 'updated', 'updated_fields': list(vals.keys())}
            else:
                return {'status': 'no_data_to_update'}

        except Exception as e:
            return {'error': str(e)}


    # ===================== DELETE =====================
    @http.route('/api/business_units/delete/<int:rec_id>', type='json', auth='user', methods=['DELETE'], csrf=False)
    def delete_business_unit(self, rec_id):
        try:
            rec = request.env['business.unit'].sudo().browse(rec_id)

            if not rec.exists():
                return {'error': 'Record not found'}

            rec.unlink()

            return {'status': 'deleted'}

        except Exception as e:
            return {'error': str(e)}