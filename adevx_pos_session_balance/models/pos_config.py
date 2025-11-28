from odoo import api, fields, models, _


class PosConfig(models.Model):
    _inherit = 'pos.config'


    current_session_net_sale = fields.Float(
        string="Current Session",  compute="_compute_current_session_net_sale")
    use_journal_ending_balance_as_opening = fields.Boolean(string="Use Journal Ending Balance As Opening")
    opening_journal_id = fields.Many2one(comodel_name="account.journal", string="Opening Journal")
    accept_closing_session_diff = fields.Selection(
        string='Accept closing Session with Difference', selection=[
            ('allow', 'Allow'), ('block', 'Block'), ], required=True, default='allow')

    @api.depends('session_ids')
    def _compute_current_session_net_sale(self):
        for rec in self:
            net_sale = 0
            session = self.env['pos.session'].search_read(
                [('config_id', '=', rec.id), ('state', '!=', 'closed')],
                ['total_payments_amount'], order="start_at asc", limit=1)
            if session:
                net_sale = session[0]['total_payments_amount']
            rec.current_session_net_sale = net_sale

