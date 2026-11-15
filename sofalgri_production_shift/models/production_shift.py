# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_datetime

DEFAULT_TZ = 'Africa/Casablanca'


class ProductionShift(models.Model):
    _name = 'sofalgri.production.shift'
    _description = "Shift de production"
    _inherit = ['mail.thread']
    _order = 'date_start desc, id desc'

    name = fields.Char(string="Shift", required=True, readonly=True, copy=False, default=lambda self: _("Nouveau"))
    company_id = fields.Many2one(
        'res.company', string="Société", required=True, readonly=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        [('open', "En cours"), ('done', "Terminé")],
        string="État", required=True, default='open', readonly=True, tracking=True,
    )
    date_start = fields.Datetime(string="Début", required=True, readonly=True, default=fields.Datetime.now)
    date_end = fields.Datetime(string="Fin", readonly=True, tracking=True)
    user_start_id = fields.Many2one(
        'res.users', string="Démarré par", required=True, readonly=True, default=lambda self: self.env.user)
    user_end_id = fields.Many2one('res.users', string="Terminé par", readonly=True)
    duration = fields.Float(string="Durée (h)", compute='_compute_duration')
    note = fields.Text(string="Remarques")
    report_sent = fields.Boolean(string="Rapport envoyé", readonly=True, copy=False)

    production_ids = fields.Many2many(
        'mrp.production', string="Ordres de fabrication", compute='_compute_report')
    production_count = fields.Integer(string="Nb d'OF", compute='_compute_report')
    pallet_count = fields.Integer(string="Palettes", compute='_compute_report')
    box_count = fields.Float(string="Colis", compute='_compute_report', digits=(16, 0))
    qty_produced = fields.Float(string="Poids produit (kg)", compute='_compute_report', digits=(16, 2))
    component_qty = fields.Float(string="Vrac consommé (kg)", compute='_compute_report', digits=(16, 2))
    report_html = fields.Html(string="Rapport", compute='_compute_report', sanitize=False)

    @api.constrains('state', 'company_id')
    def _check_single_open_shift(self):
        for shift in self.filtered(lambda s: s.state == 'open'):
            if self.search_count([('state', '=', 'open'), ('company_id', '=', shift.company_id.id),
                                  ('id', '!=', shift.id)]):
                raise ValidationError(_("Un shift est déjà en cours : terminez-le avant d'en démarrer un autre."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("Nouveau")) == _("Nouveau"):
                vals['name'] = self.env['ir.sequence'].next_by_code('sofalgri.production.shift') or _("Nouveau")
        return super().create(vals_list)

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        now = fields.Datetime.now()
        for shift in self:
            end = shift.date_end or now
            shift.duration = (end - shift.date_start).total_seconds() / 3600.0 if shift.date_start else 0.0

    # ------------------------------------------------------------------
    # Ouverture / clôture
    # ------------------------------------------------------------------
    @api.model
    def _get_open_shift(self, company=None):
        company = company or self.env.company
        return self.search([('state', '=', 'open'), ('company_id', '=', company.id)], limit=1)

    @api.model
    def action_start_shift(self):
        if self._get_open_shift():
            open_shift = self._get_open_shift()
            raise UserError(_("Le shift %(shift)s est déjà en cours depuis %(date)s (démarré par %(user)s).",
                              shift=open_shift.name, date=open_shift._format_dt(open_shift.date_start),
                              user=open_shift.user_start_id.name))
        shift = self.create({})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Shift démarré"),
                'message': _("%(shift)s démarré le %(date)s.", shift=shift.name,
                             date=shift._format_dt(shift.date_start)),
                'type': 'success',
                'sticky': False,
                # Rechargement complet : le navigateur garde sinon la liste avec l'ancien bouton
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    @api.model
    def action_end_open_shift(self):
        shift = self._get_open_shift()
        if not shift:
            raise UserError(_("Aucun shift en cours : démarrez d'abord le shift."))
        return shift.action_end_shift()

    def action_end_shift(self):
        self.ensure_one()
        if self.state != 'open':
            raise UserError(_("Ce shift est déjà terminé."))
        self.write({
            'state': 'done',
            'date_end': fields.Datetime.now(),
            'user_end_id': self.env.user.id,
        })
        self._send_report()
        # Page rechargée sur le shift terminé : en revenant à la liste des OF, seul « Démarrer le shift » reste
        return {
            'type': 'ir.actions.act_url',
            'url': '/odoo/action-sofalgri_production_shift.action_production_shift/%s' % self.id,
            'target': 'self',
        }

    def action_send_report(self):
        for shift in self:
            if shift.state != 'done':
                raise UserError(_("Le rapport est envoyé à la fin du shift."))
            shift._send_report()
        return True

    def action_print_report(self):
        return self.env.ref('sofalgri_production_shift.action_report_production_shift').report_action(self)

    # ------------------------------------------------------------------
    # Rapport
    # ------------------------------------------------------------------
    def _format_dt(self, value):
        if not value:
            return ''
        tz = self.env.user.tz or DEFAULT_TZ
        return format_datetime(self.env, value, tz=tz, dt_format='dd/MM/yyyy HH:mm')

    def _get_productions(self):
        """ Tous les OF de la station terminés pendant le shift (quel que soit l'utilisateur). """
        self.ensure_one()
        return self.env['mrp.production'].search([
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'done'),
            ('date_finished', '>=', self.date_start),
            ('date_finished', '<=', self.date_end or fields.Datetime.now()),
        ], order='date_finished, id')

    @staticmethod
    def _calibre_sort_key(calibre):
        calibre = str(calibre or '')
        return (int(calibre) if calibre.isdigit() else 999, calibre)

    def _get_report_data(self):
        """ Palettes produites pendant le shift : une palette par n° de palette des OF
        (palette mixte : plusieurs lignes), les OF sans palette (vrac, déchets) à part.
        Les quantités déconstruites sont retirées. """
        self.ensure_one()
        productions = self._get_productions()
        pallets = {}
        bulk_lines = []
        summary = {}
        component_qty = 0.0
        production_count = 0  # OF entièrement déconstruits exclus
        has_component_qty = 'component_lot_qty' in productions._fields
        for production in productions:
            qty = production.qty_produced
            if not qty:
                continue
            unbuilt = sum(
                unbuild.product_uom_id._compute_quantity(unbuild.product_qty, production.product_uom_id)
                for unbuild in production.unbuild_ids.filtered(lambda u: u.state == 'done')
            )
            remaining = qty - unbuilt
            if remaining <= 0:
                continue
            # La déconstruction rend le vrac au prorata de la quantité déconstruite
            if has_component_qty:
                component_qty += production.component_lot_qty * remaining / qty
            production_count += 1
            product = production.product_id
            packaging = production.product_packaging_id
            # Champ de sofalgri_package_reports, affiché s'il existe
            calibre = 'calibre' in product._fields and product.calibre or ''
            line = {
                'production': production.name,
                'date': self._format_dt(production.date_finished),
                'product': product.product_tmpl_id.name.strip(),
                'calibre': calibre,
                'packaging': packaging.name or '',
                'lot': production.lot_producing_id.name or '',
                'location': (production.storage_location_id or production.location_dest_id).name or '',
                'boxes': production.product_packaging_qty * remaining / qty,
                'qty': remaining,
                'uom': production.product_uom_id.name,
            }
            pallet = production.result_package_id
            if pallet:
                group = pallets.setdefault(pallet.id, {'name': pallet.name, 'lines': []})
                group['lines'].append(line)
            else:
                bulk_lines.append(line)
            key = (str(calibre), line['product'], line['packaging'])
            item = summary.setdefault(key, {
                'calibre': calibre, 'product': line['product'], 'packaging': line['packaging'],
                'pallets': set(), 'boxes': 0.0, 'qty': 0.0,
            })
            if pallet:
                item['pallets'].add(pallet.id)
            item['boxes'] += line['boxes']
            item['qty'] += line['qty']

        pallet_groups = sorted(pallets.values(), key=lambda g: g['name'])
        for group in pallet_groups:
            group['lines'].sort(key=lambda l: self._calibre_sort_key(l['calibre']))
            group['mixed'] = len(group['lines']) > 1
        summary_lines = sorted(summary.values(),
                               key=lambda i: (self._calibre_sort_key(i['calibre']), i['product'], i['packaging']))
        for item in summary_lines:
            item['pallet_count'] = len(item['pallets'])
        all_lines = [line for group in pallet_groups for line in group['lines']] + bulk_lines
        return {
            'productions': productions,
            'production_count': production_count,
            'pallets': pallet_groups,
            'bulk_lines': bulk_lines,
            'summary': summary_lines,
            'pallet_count': len(pallet_groups),
            'box_count': sum(line['boxes'] for line in all_lines),
            'qty': sum(line['qty'] for line in all_lines),
            'component_qty': component_qty,
            'date_start': self._format_dt(self.date_start),
            'date_end': self._format_dt(self.date_end) if self.date_end else _("en cours"),
        }

    def _render_report_html(self, data):
        self.ensure_one()
        return self.env['ir.qweb']._render(
            'sofalgri_production_shift.production_shift_report_content', {'shift': self, 'data': data})

    @api.depends('date_start', 'date_end', 'state')
    def _compute_report(self):
        for shift in self:
            if not shift.date_start or not shift.id:
                shift.production_ids = False
                shift.production_count = shift.pallet_count = 0
                shift.box_count = shift.qty_produced = shift.component_qty = 0.0
                shift.report_html = False
                continue
            data = shift._get_report_data()
            shift.production_ids = data['productions']
            shift.production_count = data['production_count']
            shift.pallet_count = data['pallet_count']
            shift.box_count = data['box_count']
            shift.qty_produced = data['qty']
            shift.component_qty = data['component_qty']
            shift.report_html = shift._render_report_html(data)

    def _send_report(self):
        """ Email aux destinataires de la configuration, rapport PDF en pièce jointe, trace dans le fil. """
        self.ensure_one()
        partners = self.company_id.production_shift_partner_ids.filtered('email')
        if not partners:
            self.message_post(body=_("Rapport non envoyé : aucun destinataire avec une adresse email "
                                     "dans Fabrication > Configuration > Paramètres > Shifts de production."))
            return False
        data = self._get_report_data()
        pdf_content, _report_type = self.env['ir.actions.report']._render_qweb_pdf(
            'sofalgri_production_shift.action_report_production_shift', self.ids)
        attachment = self.env['ir.attachment'].create({
            'name': "%s.pdf" % self.name.replace('/', '-'),
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        subject = _("Rapport du shift %(shift)s : %(pallets)s palettes, %(qty)s kg",
                    shift=self.name, pallets=data['pallet_count'], qty="{:,.0f}".format(data['qty']).replace(',', ' '))
        body = self._render_report_html(data)
        email_from = (self.company_id.email_formatted
                      or self.env['ir.mail_server'].sudo()._get_default_from_address()
                      or self.env.user.email_formatted)
        mail = self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body,
            'email_from': email_from,
            'recipient_ids': [(6, 0, partners.ids)],
            'attachment_ids': [(6, 0, attachment.ids)],
            'model': self._name,
            'res_id': self.id,
            'auto_delete': False,
        })
        mail.send(raise_exception=False)
        self.message_post(
            body=_("Rapport envoyé à %(partners)s.", partners=", ".join(partners.mapped('name'))),
            attachment_ids=attachment.ids,
        )
        self.report_sent = True
        return True
