from pytz import timezone, UTC
from datetime import datetime, date
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = "pos.session"

    def action_pos_session_open(self):
        # we only open sessions that haven't already been opened
        for session in self.filtered(lambda session: session.state == 'opening_control'):
            if (session.config_id.use_journal_ending_balance_as_opening and
                    session.config_id.cash_control and not session.rescue):
                last_session = self.search([
                    ('config_id', '=', session.config_id.id), ('id', '!=', session.id)], limit=1)
                opening_journal = last_session.config_id.opening_journal_id
                dashboard_data = opening_journal._get_journal_dashboard_data_batched()[opening_journal.id]
                account_balance = dashboard_data['account_balance'].split('\xa0')[0].replace(',', '')
                last_session.cash_register_balance_end_real = account_balance

        return super().action_pos_session_open()