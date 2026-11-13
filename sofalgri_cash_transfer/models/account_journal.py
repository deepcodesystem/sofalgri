from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    cash_transfer_target = fields.Boolean(
        string="Reçoit les versements d'espèces",
        help="Compte bancaire proposé dans les versements d'espèces. "
             "Aucun journal coché : tous les journaux de banque sont proposés.")
