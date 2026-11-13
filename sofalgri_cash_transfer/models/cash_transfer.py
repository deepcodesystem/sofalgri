from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CashTransfer(models.Model):
    """Versement d'espèces d'une caisse sur un compte bancaire.

    Validation : écriture dans le journal de banque, débit du compte de la banque,
    crédit du compte de la caisse, au montant versé.
    """
    _name = 'sofalgri.cash.transfer'
    _description = "Versement d'espèces en banque"
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(string="Référence", default="/", readonly=True, copy=False)
    date = fields.Date(
        string="Date", required=True, default=fields.Date.context_today, tracking=True)
    company_id = fields.Many2one(
        'res.company', string="Société", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    cash_journal_id = fields.Many2one(
        'account.journal', string="Caisse", required=True, tracking=True,
        domain="[('type', '=', 'cash'), ('company_id', '=', company_id)]",
        default=lambda self: self._default_cash_journal())
    allowed_bank_journal_ids = fields.Many2many(
        'account.journal', compute='_compute_allowed_bank_journal_ids')
    bank_journal_id = fields.Many2one(
        'account.journal', string="Compte bancaire", required=True, tracking=True,
        domain="[('id', 'in', allowed_bank_journal_ids)]",
        default=lambda self: self._default_bank_journal())
    amount = fields.Monetary(string="Montant versé", required=True, tracking=True)
    ref = fields.Char(string="Référence du bordereau", tracking=True)
    notes = fields.Text(string="Notes")
    state = fields.Selection([
        ('draft', "Brouillon"),
        ('posted', "Validé"),
        ('cancel', "Annulé"),
    ], string="État", default='draft', required=True, readonly=True, copy=False, tracking=True)
    move_id = fields.Many2one('account.move', string="Écriture", readonly=True, copy=False)

    @api.model
    def _get_bank_journal_domain(self, company=None):
        company = company or self.env.company
        domain = [('type', '=', 'bank'), ('company_id', '=', company.id)]
        Journal = self.env['account.journal']
        if Journal.search_count(domain + [('cash_transfer_target', '=', True)], limit=1):
            domain.append(('cash_transfer_target', '=', True))
        return domain

    @api.model
    def _default_cash_journal(self):
        return self.env['account.journal'].search(
            [('type', '=', 'cash'), ('company_id', '=', self.env.company.id)], limit=1)

    @api.model
    def _default_bank_journal(self):
        return self.env['account.journal'].search(self._get_bank_journal_domain(), limit=1)

    @api.depends('company_id')
    def _compute_allowed_bank_journal_ids(self):
        Journal = self.env['account.journal']
        for transfer in self:
            transfer.allowed_bank_journal_ids = Journal.search(
                transfer._get_bank_journal_domain(transfer.company_id))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code('sofalgri.cash.transfer') or '/'
        return super().create(vals_list)

    def unlink(self):
        if any(transfer.state != 'draft' for transfer in self):
            raise UserError(_("Seul un versement en brouillon peut être supprimé : annulez-le d'abord."))
        return super().unlink()

    def _prepare_move_vals(self):
        self.ensure_one()
        cash_account = self.cash_journal_id.default_account_id
        bank_account = self.bank_journal_id.default_account_id
        if not cash_account or not bank_account:
            raise UserError(_("La caisse et le compte bancaire doivent avoir un compte par défaut."))
        label = _("Versement d'espèces %(name)s : %(cash)s → %(bank)s",
                  name=self.name, cash=self.cash_journal_id.name, bank=self.bank_journal_id.name)
        if self.ref:
            label = f"{label} ({self.ref})"
        return {
            'move_type': 'entry',
            'journal_id': self.bank_journal_id.id,
            'date': self.date,
            'ref': self.ref or self.name,
            'company_id': self.company_id.id,
            'line_ids': [
                (0, 0, {'name': label, 'account_id': bank_account.id, 'debit': self.amount, 'credit': 0.0}),
                (0, 0, {'name': label, 'account_id': cash_account.id, 'debit': 0.0, 'credit': self.amount}),
            ],
        }

    def action_post(self):
        for transfer in self:
            if transfer.state != 'draft':
                continue
            if transfer.amount <= 0:
                raise UserError(_("Le montant versé doit être positif."))
            if transfer.cash_journal_id == transfer.bank_journal_id:
                raise UserError(_("La caisse et le compte bancaire doivent être différents."))
            move = self.env['account.move'].create(transfer._prepare_move_vals())
            move.action_post()
            transfer.write({'move_id': move.id, 'state': 'posted'})
        return True

    def action_cancel(self):
        for transfer in self:
            if transfer.move_id and transfer.move_id.state == 'posted':
                transfer.move_id.button_draft()
            if transfer.move_id and transfer.move_id.state == 'draft':
                transfer.move_id.button_cancel()
            transfer.state = 'cancel'
        return True

    def action_draft(self):
        self.filtered(lambda transfer: transfer.state == 'cancel').write({'state': 'draft', 'move_id': False})
        return True

    def action_open_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
        }
