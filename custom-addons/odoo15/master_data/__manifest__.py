{
    'name': 'Stationery Management System',
    'version': '1.0',
    'summary': 'Complete Stationery Management System',
    'description': """
        Stationery Management System for managing:
        - Business Units (BU/BR/DIV)
        - Stationery Products
        - Stationery Requests with approval workflow
        - Internal Transfers with GM approval
        - Stationery Returns
        - Internal Issue Requests
        - Purchase Orders with manager approval
        - Office Stock Reports
    """,
    'author': 'Your Team',
    'category': 'Inventory/Stationery',
    'depends': [
        'base',
        'mail',
        'stock',
        'purchase',
        'product',
        'hr',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Data Files (Sequences, Picking Types)
        'data/stationery_issue_sequence.xml',
        'data/request_sequence_data.xml',
        'data/sequence.xml',
        'data/emergency_transfer_data.xml',
        'data/internal_issue_picking_type.xml',

        # Wizard Views
        'wizard/reject_stationery_request_wizard.xml',
        'wizard/stationery_reject_wizard_views.xml',
        'wizard/purchase_decline_wizard_view.xml',
        'wizard/stationery_delivery_wizard.xml',

        # Main Views - IMPORTANT: Action views MUST come before menu.xml
        'views/business_unit_views.xml',
        'views/hr_department_views.xml',
        'views/hr_employee_views.xml',
        'views/product_template_views.xml',      # ← action ရှိတယ် (အရင်ဆုံးဖတ်ရမယ်)
        'views/stationery_product_view.xml',
        'views/stationary_request_views.xml',    # ← action ရှိတယ်
        'views/stationery_transfer.xml',         # ← action ရှိတယ်
        'views/stationery_return_views.xml',     # ← action ရှိတယ်
        'views/stationery_issue_view.xml',       # ← action ရှိတယ်
        'views/stationery_quent.xml',            # ← action ရှိတယ်
        'views/purchase_order_view.xml',         # ← action ရှိတယ်
        'views/stock_view.xml',
        'views/menu.xml',                         # ← menu ကို နောက်ဆုံးမှဖတ်ရမယ်
    ],
    'assets': {
        'web.assets_backend': [
            # Add any custom CSS/JS here if needed
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}