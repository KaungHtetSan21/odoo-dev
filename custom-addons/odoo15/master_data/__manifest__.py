{
    'name': 'Master_Data',
    'version': '1.0',
    'summary': 'Manage Business Units',
    'description': 'Custom module for Business Unit management',
    'author': 'Your Name',
    'depends': ['base', 'mail', 'stock'],  # IMPORTANT
    'data': [
        'security/ir.model.access.csv',
        'views/business_unit_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
}