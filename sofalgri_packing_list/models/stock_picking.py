# -*- coding: utf-8 -*-
import io

import xlsxwriter

from odoo import models, fields, api, _
from odoo.exceptions import UserError

# Colonnes de la liste de colisage (modèle client), dans l'ordre : (en-tête, clé de la ligne)
PACKING_LIST_COLUMNS = [
    ('Supplier name', 'supplier'),
    ('Vessel name', 'vessel'),
    ('Container number', 'container'),
    ('Customer name', 'customer'),
    ('ETD', 'etd'),
    ('ETA', 'eta'),
    ('Destination port', 'port'),
    ('Supplier reference', 'supplier_ref'),
    ('Variety', 'variety'),
    ('Packaging', 'packaging'),
    ('Weight (kg)', 'weight'),
    ('Size', 'size'),
    ('Class', 'class'),
    ('Country of Origin', 'origin'),
    ('Number of boxes', 'boxes'),
    ('Pallet quantity', 'pallets'),
    ('Organic / Conventional', 'cultivation'),
    ('Pallet ID', 'pallet_id'),
    ('Global Gap Number', 'ggn'),
    ('Grower Code', 'grower'),
    ('Temp Tale Location', 'temp_tale'),
    ('Ethylene Absorber Location', 'ethylene'),
    ('Supplier Packhouse', 'packhouse'),
    ('Pack Date DD/MM/YYYY', 'pack_date'),
]
DATE_KEYS = ('etd', 'eta', 'pack_date')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # --- Informations d'expédition de la liste de colisage ---
    truck_reference = fields.Char(string="Référence camion", help="Ex. « TRUCK 13 » (titre de la liste de colisage).")
    vessel_name = fields.Char(string="Navire")
    container_number = fields.Char(
        string="N° conteneur",
        compute='_compute_container_number', store=True, readonly=False,
        help="Pré-rempli avec le matricule du véhicule.",
    )
    etd = fields.Date(string="ETD (départ prévu)")
    eta = fields.Date(string="ETA (arrivée prévue)")
    destination_port = fields.Char(string="Port de destination")
    temp_tale_location = fields.Char(string="Emplacement Temp Tale")
    ethylene_absorber_location = fields.Char(string="Emplacement absorbeur d'éthylène")

    @api.depends('matricule')
    def _compute_container_number(self):
        for picking in self:
            picking.container_number = picking.container_number or picking.matricule

    # --- Lignes de la liste de colisage ---

    def _get_packing_list_supplier_reference(self):
        """ N° des factures client de la commande, à défaut la commande. """
        self.ensure_one()
        invoices = self.sale_id.invoice_ids.filtered(lambda m: m.move_type == 'out_invoice' and m.state == 'posted')
        return ', '.join(invoices.mapped('name')) or self.sale_id.name or self.origin or ''

    def _get_packing_list_title(self):
        self.ensure_one()
        parts = [self.company_id.name, '-', self.truck_reference or self.name, self.partner_id.commercial_partner_id.name or '']
        return 'PACKING LIST ' + ' '.join(p for p in parts if p)

    def _get_packing_list_rows(self):
        """ Une ligne par palette × article (calibre) × conditionnement, triées par calibre puis palette ;
        « Pallet quantity » = 1 sur la première ligne de chaque palette. """
        self.ensure_one()
        lines = self.move_line_ids.filtered(lambda l: l.quantity and l.product_id)
        if not lines:
            raise UserError(_("La livraison %s n'a aucune ligne à mettre dans la liste de colisage.", self.name))
        company = self.company_id
        warehouse = self.picking_type_id.warehouse_id
        common = {
            'supplier': company.name,
            'vessel': self.vessel_name or '',
            'container': self.container_number or '',
            'customer': self.partner_id.commercial_partner_id.name or '',
            'etd': self.etd,
            'eta': self.eta,
            'port': self.destination_port or '',
            'supplier_ref': self._get_packing_list_supplier_reference(),
            'grower': warehouse.grower_code or '',
            'temp_tale': self.temp_tale_location or '',
            'ethylene': self.ethylene_absorber_location or '',
            'packhouse': warehouse.packhouse_name or '',
        }

        groups = {}
        for line in lines:
            package = line.result_package_id or line.package_id
            packaging = line.product_packaging_id or line.move_id.product_packaging_id
            key = (package.id, line.product_id.id, packaging.id)
            group = groups.setdefault(key, {
                'package': package, 'product': line.product_id, 'packaging': packaging,
                'boxes': 0.0, 'pack_dates': [],
            })
            if line.product_packaging_qty:
                group['boxes'] += line.product_packaging_qty
            elif packaging.qty:
                group['boxes'] += line.quantity / packaging.qty
            lot = line.lot_id
            pack_date = 'production_date' in lot._fields and lot.production_date
            if pack_date:
                group['pack_dates'].append(fields.Date.to_date(pack_date))

        rows = []
        for group in groups.values():
            product, packaging = group['product'], group['packaging']
            rows.append(dict(common, **{
                'variety': (product.product_variety or '').upper(),
                'packaging': packaging.description_sale or packaging.name or '',
                'weight': packaging.qty or '',
                'size': product.calibre or '',
                'class': product.product_classify or '',
                'origin': ('country_of_origin' in product._fields and (product.country_of_origin.name or '').upper()) or '',
                'boxes': round(group['boxes']),
                'pallets': '',
                'cultivation': dict(product._fields['cultivation_mode'].selection).get(product.cultivation_mode, ''),
                'pallet_id': group['package'].name or '',
                'ggn': product.global_gap or company.number_ggn or '',
                'pack_date': min(group['pack_dates']) if group['pack_dates'] else False,
            }))

        def sort_key(row):
            size = str(row['size'])
            return (int(size) if size.isdigit() else 999, size, row['pallet_id'])
        rows.sort(key=sort_key)
        seen_pallets = set()
        for row in rows:
            if row['pallet_id'] and row['pallet_id'] not in seen_pallets:
                row['pallets'] = 1
                seen_pallets.add(row['pallet_id'])
        return rows

    def _get_packing_list_columns(self):
        return PACKING_LIST_COLUMNS

    # --- Export Excel ---

    def action_export_packing_list_xlsx(self):
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Sheet1')
        title_format = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'})
        header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'align': 'center', 'valign': 'vcenter',
                                             'border': 1, 'bg_color': '#D9E1F2'})
        cell_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})

        columns = self._get_packing_list_columns()
        sheet.merge_range(1, 2, 3, len(columns) - 1, self._get_packing_list_title(), title_format)
        sheet.set_row(5, 45)
        for col, (header, key) in enumerate(columns):
            sheet.write(5, col, header, header_format)
            sheet.set_column(col, col, 14 if key not in ('supplier', 'customer', 'packaging') else 26)
        for row_index, row in enumerate(self._get_packing_list_rows(), start=6):
            for col, (header, key) in enumerate(columns):
                value = row[key]
                if key in DATE_KEYS and value:
                    sheet.write_datetime(row_index, col, fields.Datetime.to_datetime(value), date_format)
                else:
                    sheet.write(row_index, col, value if value is not False else '', cell_format)
        sheet.freeze_panes(6, 0)
        workbook.close()

        filename = '%s.xlsx' % self._get_packing_list_title().replace('/', '-')
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'raw': output.getvalue(),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }
