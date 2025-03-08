{
    'name': 'Gestión de Requisiciones de Compra',
    'version': '17.0.1.0.0',
    'summary': 'Módulo para la gestión de requisiciones de compra',
    'description': """
        Este módulo permite gestionar el proceso de requisiciones de compra, desde la solicitud hasta la compra.
    """,
    'author': 'Javiel Fernandez',
    'website': 'http://www.odoo.com',  # Error corregido aquí
    'category': 'Compras',
    'depends': ['base', 'product', 'stock', 'purchase', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/requisicion_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'requisiciones_compra/static/src/js/requisicion.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': True,
}