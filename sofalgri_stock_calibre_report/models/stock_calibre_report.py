from odoo import fields, models, tools


class StockCalibreReport(models.Model):
    _name = 'sofalgri.stock.calibre.report'
    _description = "Palettes en frigo par calibre et conditionnement"
    _auto = False
    _rec_name = 'calibre'
    _order = 'calibre'
    _depends = {
        'stock.quant': ['location_id', 'package_id', 'product_id', 'product_packaging_id', 'quantity'],
        'stock.location': ['usage', 'complete_name'],
        'product.product': ['calibre'],
        'product.packaging': ['name', 'qty'],
    }

    calibre = fields.Integer(string="Calibre", readonly=True, aggregator=None)
    qty_carton_gold_frutas = fields.Integer(string="Carton 4 kg Gold Frutas", readonly=True)
    qty_carton_sofina = fields.Integer(string="Carton 4 kg Sofina", readonly=True)
    qty_carton_lidl = fields.Integer(string="Carton 4 kg Lidl", readonly=True)
    qty_carton_generic = fields.Integer(string="Carton 4 kg Générique", readonly=True)
    qty_plastic = fields.Integer(string="Caisse plastique 10 kg", readonly=True)
    qty_other = fields.Integer(string="Autres", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH calibres AS (
                    SELECT DISTINCT calibre::integer AS calibre
                    FROM product_product
                    WHERE calibre ~ '^[0-9]+$'
                ),
                palettes AS (
                    SELECT product.calibre::integer AS calibre,
                           quant.package_id,
                           CASE
                               WHEN packaging.name = 'CARTON 4KG GOLD FRUTAS' THEN 'gold_frutas'
                               WHEN packaging.name = 'CARTON 4KG GOLD SOFINA' THEN 'sofina'
                               WHEN packaging.name = 'CARTON 4KG LIDL' THEN 'lidl'
                               WHEN packaging.name = 'CARTON 4KG' THEN 'generic'
                               WHEN packaging.name ILIKE 'PLASTIQUE%' AND packaging.qty = 10 THEN 'plastic'
                               ELSE 'other'
                           END AS packaging_type
                    FROM stock_quant quant
                    JOIN stock_location location ON location.id = quant.location_id
                    JOIN product_product product ON product.id = quant.product_id
                    LEFT JOIN product_packaging packaging ON packaging.id = quant.product_packaging_id
                    WHERE location.usage = 'internal'
                      AND location.complete_name ILIKE '%/Frigo %'
                      AND quant.quantity > 0
                      AND quant.package_id IS NOT NULL
                      AND product.calibre ~ '^[0-9]+$'
                )
                SELECT calibres.calibre AS id,
                       calibres.calibre,
                       COUNT(DISTINCT palettes.package_id) FILTER (WHERE palettes.packaging_type = 'gold_frutas') AS qty_carton_gold_frutas,
                       COUNT(DISTINCT palettes.package_id) FILTER (WHERE palettes.packaging_type = 'sofina') AS qty_carton_sofina,
                       COUNT(DISTINCT palettes.package_id) FILTER (WHERE palettes.packaging_type = 'lidl') AS qty_carton_lidl,
                       COUNT(DISTINCT palettes.package_id) FILTER (WHERE palettes.packaging_type = 'generic') AS qty_carton_generic,
                       COUNT(DISTINCT palettes.package_id) FILTER (WHERE palettes.packaging_type = 'plastic') AS qty_plastic,
                       COUNT(DISTINCT palettes.package_id) FILTER (WHERE palettes.packaging_type = 'other') AS qty_other
                FROM calibres
                LEFT JOIN palettes ON palettes.calibre = calibres.calibre
                GROUP BY calibres.calibre
            )
        """)
