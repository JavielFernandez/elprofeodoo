from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    auto_consumo = fields.Boolean(string='Auto Consumo')
    # ...existing code...