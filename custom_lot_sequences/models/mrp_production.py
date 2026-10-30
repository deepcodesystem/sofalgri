# -*- coding: utf-8 -*-
from datetime import datetime, time

import pytz

from odoo import models, fields


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _get_day_lot_name(self):
        """ Numéro de lot de la session de calibrage du jour : le dernier lot produit
        créé aujourd'hui (fuseau de l'utilisateur) sur un autre OF du même type d'opération. """
        self.ensure_one()
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        day_start = tz.localize(datetime.combine(fields.Date.context_today(self), time.min))
        day_start_utc = fields.Datetime.to_string(day_start.astimezone(pytz.UTC))
        productions = self.search([
            ('id', '!=', self.id),
            ('company_id', '=', self.company_id.id),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('state', '!=', 'cancel'),
            ('lot_producing_id.create_date', '>=', day_start_utc),
        ])
        return productions.lot_producing_id.sorted('create_date', reverse=True)[:1].name

    def _prepare_stock_lot_values(self):
        # Bouton « Générer » : même numéro de lot pour tous les calibres de la journée
        # (un lot par article, de même nom). Contexte new_day_lot : nouveau numéro de séquence.
        if self.product_tracking == 'lot' and not self.env.context.get('new_day_lot'):
            day_lot_name = self._get_day_lot_name()
            if day_lot_name:
                return {
                    'product_id': self.product_id.id,
                    'company_id': self.company_id.id,
                    'name': day_lot_name,
                }
        return super()._prepare_stock_lot_values()

    def action_generate_serial(self):
        self.ensure_one()
        if self.product_tracking == 'lot' and not self.env.context.get('new_day_lot'):
            # Calibre déjà produit aujourd'hui : son lot du jour existe, on le reprend
            day_lot_name = self._get_day_lot_name()
            existing_lot = day_lot_name and self.env['stock.lot'].search([
                ('name', '=', day_lot_name),
                ('product_id', '=', self.product_id.id),
                ('company_id', 'in', [self.company_id.id, False]),
            ], limit=1)
            if existing_lot:
                self.lot_producing_id = existing_lot
                return True
        return super().action_generate_serial()
