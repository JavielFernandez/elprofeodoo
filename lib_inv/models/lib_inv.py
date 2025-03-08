from odoo import models, fields, api
from datetime import datetime
import xlsxwriter
import base64
from io import BytesIO
from odoo.exceptions import UserError

class LibInvWizard(models.TransientModel):
    _name = 'lib.inv.wizard'
    _description = 'Wizard para generar el Libro de Inventario'

    date_from = fields.Date(
        string='Fecha Inicio',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='Fecha Fin',
        required=True,
        default=fields.Date.today
    )
    location_ids = fields.Many2many('stock.location', string='Ubicaciones')
    category_ids = fields.Many2many('product.category', string='Categorías')
    data = fields.Binary('Archivo')
    filename = fields.Char('Nombre del Archivo')

    def _get_initial_inventory(self, product, locations):
        moves_in = self.env['stock.move'].search([
            ('product_id', '=', product.id),
            ('date', '<', self.date_from),
            ('state', '=', 'done'),
            ('location_dest_id', 'in', locations.ids)
        ])
        
        moves_out = self.env['stock.move'].search([
            ('product_id', '=', product.id),
            ('date', '<', self.date_from),
            ('state', '=', 'done'),
            ('location_id', 'in', locations.ids)
        ])

        qty_in = sum(move.move_line_ids.mapped('qty_done') for move in moves_in)
        qty_out = sum(move.move_line_ids.mapped('qty_done') for move in moves_out)
        
        initial_qty = qty_in - qty_out
        initial_cost = initial_qty * product.with_context(to_date=self.date_from).standard_price
        return initial_qty, initial_cost

    def generate_report(self):
        self.ensure_one()
        locations = self.location_ids or self.env['stock.location'].search([('usage', '=', 'internal')])
        products = self.env['product.product'].search([('type', '=', 'product')])
        if self.category_ids:
            products = products.filtered(lambda p: p.categ_id in self.category_ids)

        if not products:
            raise UserError("No existen productos para generar el reporte.")
        if not locations:
            raise UserError("No existen ubicaciones para generar el reporte.")

        output = BytesIO()
        try:
            workbook = xlsxwriter.Workbook(output)
            worksheet = workbook.add_worksheet('Libro de Inventario')
            
            header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})
            currency_format = workbook.add_format({'num_format': '#,##0.00'})

            headers = ['Producto', 'Inicial (Cant.)', 'Inicial (Bs)', 'Entradas', 'Salidas', 'Final (Cant.)', 'Final (Bs)', 'Unidad de Medida']
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            row = 1
            for product in products:
                initial_qty, initial_cost = self._get_initial_inventory(product, locations)
                
                moves_in = self.env['stock.move'].search([
                    ('product_id', '=', product.id),
                    ('date', '>=', self.date_from),
                    ('date', '<=', self.date_to),
                    ('state', '=', 'done'),
                    ('location_dest_id', 'in', locations.ids)
                ])
                in_qty = sum(move.move_line_ids.mapped('qty_done') for move in moves_in)
                
                moves_out = self.env['stock.move'].search([
                    ('product_id', '=', product.id),
                    ('date', '>=', self.date_from),
                    ('date', '<=', self.date_to),
                    ('state', '=', 'done'),
                    ('location_id', 'in', locations.ids)
                ])
                out_qty = sum(move.move_line_ids.mapped('qty_done') for move in moves_out)
                
                final_qty = initial_qty + in_qty - out_qty
                final_cost = final_qty * product.standard_price
                
                worksheet.write_row(row, 0, [
                    product.name,
                    initial_qty,
                    initial_cost,
                    in_qty,
                    out_qty,
                    final_qty,
                    final_cost,
                    product.uom_id.name,
                ], currency_format)
                row += 1

            workbook.close()
            output.seek(0)
            self.write({
                'data': base64.encodebytes(output.read()),
                'filename': f'lib_inventario_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
            })
            
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/lib.inv.wizard/{self.id}/data/{self.filename}?download=true',
                'target': 'self'
            }
        except Exception as e:
            raise UserError(f"Error al generar el reporte de Excel: {e}")