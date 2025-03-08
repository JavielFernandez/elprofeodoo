from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    cost_at_date = fields.Float(
        string='Costo en Fecha',
        compute='_compute_cost_at_date',
        store=False
    )

    @api.depends('product_id', 'date', 'move_line_ids.qty_done')
    def _compute_cost_at_date(self):
        for move in self:
            cost = 0.0
            if move.product_id and move.date:
                # Calcular usando qty_done de move lines
                qty_done = sum(move.move_line_ids.mapped('qty_done'))
                if qty_done:
                    product = move.product_id.with_context(to_date=move.date)
                    cost = product.standard_price * qty_done
            move.cost_at_date = cost