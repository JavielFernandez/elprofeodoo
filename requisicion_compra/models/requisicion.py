from odoo import models, fields, api, _
from odoo.exceptions import UserError

class RequisicionCompra(models.Model):
    _name = 'requisicion.compra'
    _description = 'Requisición de Compra'

    name = fields.Char(string='Número de Requisición', required=True, default=lambda self: self.env['ir.sequence'].next_by_code('requisicion.compra'))
    solicitante_id = fields.Many2one('res.users', string='Solicitante', default=lambda self: self.env.user)
    fecha_solicitud = fields.Date(string='Fecha de Solicitud', default=fields.Date.today())
    fecha_entrega_requerida = fields.Date(string='Fecha de Entrega Requerida')
    lineas_ids = fields.One2many('requisicion.compra.linea', 'requisicion_id', string='Líneas de Requisición')
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('en_revision', 'En Revisión'),
        ('aprobado', 'Aprobado'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ], string='Estado', default='borrador')
    nota_entrega_id = fields.Many2one('stock.picking', string='Nota de Entrega')
    solicitud_cotizacion_ids = fields.Many2many('purchase.order', string='Solicitudes de Cotización')

    def action_enviar_revision(self):
        self.write({'estado': 'en_revision'})
        # Notificación a Almacén (implementar lógica de notificación)

    def action_aprobar(self):
        self.write({'estado': 'aprobado'})

    def action_completar(self):
        self.write({'estado': 'completado'})

    def action_cancelar(self):
        self.write({'estado': 'cancelado'})

    def action_crear_nota_entrega(self):
        lineas_entrega = []
        for linea in self.lineas_ids:
            if linea.disponible_almacen:
                lineas_entrega.append((0, 0, {
                    'product_id': linea.producto_id.id,
                    'product_uom_qty': linea.cantidad_requerida,
                }))

        nota_entrega = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'origin': self.name,
            'move_ids_without_package': lineas_entrega,
        })
        self.write({'nota_entrega_id': nota_entrega.id})

    def action_crear_solicitudes_cotizacion(self):
        for linea in self.lineas_ids:
            if linea.para_compra:
                # Lógica para seleccionar el proveedor (ejemplo)
                proveedor = self.env['res.partner'].search([('supplier_rank', '>', 0)], limit=1)
                if proveedor:
                    # Lógica para obtener el precio unitario (ejemplo)
                    precio_unitario = 10.0  # Reemplazar con la lógica real
                    solicitud_cotizacion = self.env['purchase.order'].create({
                        'partner_id': proveedor.id,
                        'order_line': [(0, 0, {
                            'product_id': linea.producto_id.id,
                            'product_qty': linea.cantidad_requerida,
                            'product_uom': linea.producto_id.uom_id.id,
                            'price_unit': precio_unitario,
                        })],
                    })
                    self.solicitud_cotizacion_ids = [(4, solicitud_cotizacion.id)]
                else:
                    raise UserError(_("No se encontró ningún proveedor."))

class RequisicionCompraLinea(models.Model):
    _name = 'requisicion.compra.linea'
    _description = 'Línea de Requisición de Compra'

    requisicion_id = fields.Many2one('requisicion.compra', string='Requisición')
    producto_id = fields.Many2one('product.product', string='Producto', required=True)
    nombre_producto = fields.Char(related='producto_id.name', string='Nombre del Producto')
    cantidad_requerida = fields.Float(string='Cantidad Requerida', required=True)
    linea_presupuestaria_id = fields.Many2one('account.analytic.account', string='Línea Presupuestaria')
    cuenta_analitica_id = fields.Many2one('account.analytic.account', string='Cuenta Analítica')
    disponible_almacen = fields.Boolean(string='Disponible en Almacén', compute='_compute_disponible_almacen', store=True)
    para_compra = fields.Boolean(string='Para Compra')
    proveedor_id = fields.Many2one('res.partner', string='Proveedor') # Agregado campo proveedor

    @api.depends('producto_id', 'cantidad_requerida')
    def _compute_disponible_almacen(self):
        for linea in self:
            cantidad_disponible = self.env['stock.quant'].search([
                ('product_id', '=', linea.producto_id.id),
                ('location_id', '=', self.env.ref('stock.stock_location_stock').id),
            ], limit=1).quantity
            linea.disponible_almacen = cantidad_disponible >= linea.cantidad_requerida