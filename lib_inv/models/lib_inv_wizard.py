from odoo import models, fields, api

class LibInvWizard(models.TransientModel):
    _name = 'lib.inv.wizard'
    _description = 'Library Inventory Wizard'

    date_from = fields.Date(string='Fecha de inicio', required=True)
    date_to = fields.Date(string='Fecha de fin', required=True)
    location_ids = fields.Many2many('stock.location', string='Ubicaciones', domain=[('is_library', '=', True)])
    category_ids = fields.Many2many('product.category', string='Categorías', domain=[('is_library_category', '=', True)])

    @api.multi
    def generate_report(self):
        # Implementar la lógica para generar el informe
        pass
