from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import UserError
import xlsxwriter
import base64
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from collections import defaultdict
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

class LibInvWizard(models.TransientModel):
    _name = 'lib.inv.wizard'
    _description = 'Wizard para generar el Libro Auxiliar de Inventario'

    date_from = fields.Date(string='Fecha Inicio', required=True, default=fields.Date.today().replace(day=1))
    date_to = fields.Date(string='Fecha Fin', required=True, default=fields.Date.today())
    location_ids = fields.Many2many('stock.location', string='Ubicaciones')
    warehouse_ids = fields.Many2many('stock.warehouse', string='Almacenes')
    category_ids = fields.Many2many('product.category', string='Categorías de Productos')
    data = fields.Binary('Archivo Excel')
    filename = fields.Char('Nombre del Archivo')

    def _get_initial_inventory(self, product_id, date_from, location_ids):
        domain = [('product_id', '=', product_id.id), ('date', '<', date_from), ('state', '=', 'done')]
        if location_ids:
            domain.append(('location_id', 'in', location_ids.ids))
        moves = self.env['stock.move'].search(domain)
        initial_qty = sum(moves.mapped('quantity_done'))
        initial_cost = product_id.with_context(to_date=date_from).standard_price * initial_qty
        return initial_qty, initial_cost

    def _get_in_moves(self, product_id, date_from, date_to, location_ids):
        domain = [
            ('product_id', '=', product_id.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '=', 'done'),
        ]
        if location_ids:
            domain.append(('location_dest_id', 'in', location_ids.ids))
        else:
            domain.append(('location_dest_id', '!=', False))

        moves = self.env['stock.move'].search(domain)
        in_qty = sum(moves.mapped('quantity_done'))
        in_cost = sum(moves.mapped('cost_at_date'))
        avg_cost = in_cost / in_qty if in_qty else 0.0
        return in_qty, avg_cost

    def _get_out_moves(self, product_id, date_from, date_to, location_ids, auto_consumo=False):
        domain = [
            ('product_id', '=', product_id.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '=', 'done'),
            ('picking_id.auto_consumo', '=', auto_consumo),
        ]
        if location_ids:
            domain.append(('location_id', 'in', location_ids.ids))
        else:
            domain.append(('location_id', '!=', False))

        moves = self.env['stock.move'].search(domain)
        out_qty = sum(moves.mapped('quantity_done'))
        out_cost = sum(moves.mapped('cost_at_date'))
        return out_qty, out_cost

    def _get_final_inventory(self, product_id, date_to, location_ids):
        domain = [('product_id', '=', product_id.id), ('date', '<=', date_to), ('state', '=', 'done')]
        if location_ids:
            domain.append(('location_id', 'in', location_ids.ids))
        moves = self.env['stock.move'].search(domain)
        final_qty = sum(moves.mapped('quantity_done'))
        final_cost = product_id.with_context(to_date=date_to).standard_price * final_qty
        return final_qty, final_cost

    def generate_excel_report(self):
        products = self.env['product.product'].search([('type', '=', 'product')])
        if self.category_ids:
            products = products.filtered(lambda p: p.categ_id in self.category_ids)

        locations = self.location_ids or self.env['stock.location'].search([('usage', '=', 'internal')])

        if not products:
            raise UserError("No existen productos para generar el reporte.")
        if not locations:
            raise UserError("No existen ubicaciones para generar el reporte.")

        output = BytesIO()
        try:
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Libro de Inventario')

            header = [
                'Referencia Interna', 'Nombre del Producto', 'Unidad de Medida',
                'Inventario Inicial (Cant.)', 'Inventario Inicial (Bs)',
                'Entradas (Cant.)', 'Costo Unitario Promedio',
                'Salidas (Cant.)', 'Salidas (Bs)',
                'Auto Consumo (Cant.)', 'Auto Consumo (Bs)',
                'Inventario Final (Cant.)', 'Inventario Final (Bs)'
            ]
            worksheet.write_row(0, 0, header)

            row = 1
            for product in products:
                initial_qty, initial_cost = self._get_initial_inventory(product, self.date_from, locations)
                in_qty, avg_cost = self._get_in_moves(product, self.date_from, self.date_to, locations)
                out_qty, out_cost = self._get_out_moves(product, self.date_from, self.date_to, locations)
                auto_consumo_qty, auto_consumo_cost = self._get_out_moves(product, self.date_from, self.date_to, locations, auto_consumo=True)
                final_qty, final_cost = self._get_final_inventory(product, self.date_to, locations)

                data = [
                    product.default_code or '', product.name, product.uom_id.name,
                    initial_qty, initial_cost,
                    in_qty, avg_cost,
                    out_qty, out_cost,
                    auto_consumo_qty, auto_consumo_cost,
                    final_qty, final_cost
                ]
                worksheet.write_row(row, 0, data)
                row += 1

            workbook.close()
            output.seek(0)
            file_data = base64.encodebytes(output.read())

            self.write({
                'data': file_data,
                'filename': 'Libro_Inventario.xlsx',
            })

            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content?model=lib.inv.wizard&id=%s&field=data&download=true&filename=%s' % (self.id, self.filename),
                'target': 'new',
            }
        except Exception as e:
            raise UserError(f"Error al generar el reporte de Excel: {e}")

    def generate_pdf_report(self):
        products = self.env['product.product'].search([('type', '=', 'product')])
        if self.category_ids:
            products = products.filtered(lambda p: p.categ_id in self.category_ids)

        locations = self.location_ids or self.env['stock.location'].search([('usage', '=', 'internal')])

        if not products:
            raise UserError("No existen productos para generar el reporte.")
        if not locations:
            raise UserError("No existen ubicaciones para generar el reporte.")
        styles = getSampleStyleSheet()
        # ...existing code...