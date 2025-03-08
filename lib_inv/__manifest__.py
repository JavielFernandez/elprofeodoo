{
    'name': 'Libro de Inventario',
    'version': '1.0',
    'summary': 'Genera un libro de inventario en Excel.',
    'description': 'Este módulo permite generar un libro de inventario en formato Excel.',
    'author': 'JavielF',
    'website': 'http://www.tuwebsite.com',
    'category': 'Inventory',
    'depends': ['base', 'stock', 'product', 'sale'],
    'data': [
        'views/lib_inv_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}