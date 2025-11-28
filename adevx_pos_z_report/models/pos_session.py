from pytz import timezone, UTC
from datetime import datetime, date
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = "pos.session"

    def get_current_date(self):
        if self.env.user and self.env.user.tz:
            tz = self.env.user.tz
            tz = timezone(tz)
        else:
            tz = UTC
        if tz:
            c_time = datetime.now(tz)
            return c_time.strftime('%d/%m/%Y')
        else:
            return date.today().strftime('%d/%m/%Y')

    def get_current_time(self):
        if self.env.user and self.env.user.tz:
            tz = self.env.user.tz
            tz = timezone(tz)
        else:
            tz = UTC
        if tz:
            c_time = datetime.now(tz)
            return c_time.strftime('%I:%M %p')
        else:
            return datetime.now().strftime('%I:%M:%S %p')

    def get_cash_in_out(self):
        account_bank_statement_lines = self.env['account.bank.statement.line'].search([
            ('pos_session_id', '=', self.id)])
        cash_in_out = {}
        for absl in account_bank_statement_lines:
            if absl.amount > 0:
                cash_in_out.setdefault('cash_in', []).append({
                    'amount': absl.amount,
                    'date': absl.create_date
                })
            else:
                cash_in_out.setdefault('cash_out', []).append({
                    'amount': absl.amount,
                    'date': absl.create_date
                })
        return cash_in_out

    def get_payments_amount(self):
        payments_amount = []
        for payment_method in self.config_id.payment_method_ids:
            payments = self.env['pos.payment'].search([
                ('session_id', '=', self.id),
                ('payment_method_id', '=', payment_method.id)
            ])
            journal_dict = {
                'name': payment_method.name,
                'amount': 0
            }
            for payment in payments:
                amount = payment.amount
                journal_dict['amount'] += amount
            payments_amount.append(journal_dict)
        return payments_amount

    def get_total_sales(self):
        total_price = 0.0
        for order in self.order_ids:
            if order.amount_paid >= 0:
                total_price += sum([(line.qty * line.price_unit) for line in order.lines])
        return total_price

    def get_total_reversal(self):
        total_price = 0.0
        for order in self.order_ids:
            if order.amount_paid <= 0:
                total_price += order.amount_paid
        return total_price

    def get_reversal_orders_detail(self):
        reversal_orders_detail = {}
        for order in self.order_ids:
            if order.amount_paid <= 0:
                reversal_orders_detail[order.name] = []
                for line in order.lines:
                    reversal_orders_detail[order.name].append({
                        'product_id': line.product_id.display_name,
                        'qty': line.qty,
                        'price_subtotal_incl': line.price_subtotal_incl,
                    })
        return reversal_orders_detail

    def get_vat_tax(self):
        taxes_info = []
        tax_list = [tax.id for order in self.order_ids for line in
                    order.lines.filtered(lambda line: line.tax_ids_after_fiscal_position) for tax in
                    line.tax_ids_after_fiscal_position]
        tax_list = list(set(tax_list))
        for tax in self.env['account.tax'].browse(tax_list):
            total_tax = 0.00
            net_total = 0.00
            for line in self.env['pos.order.line'].search(
                    [('order_id', 'in', [order.id for order in self.order_ids])]).filtered(
                lambda line: tax in line.tax_ids_after_fiscal_position):
                total_tax += line.price_subtotal * tax.amount / 100
                net_total += line.price_subtotal
            taxes_info.append({
                'tax_name': tax.name,
                'tax_total': total_tax,
                'tax_per': tax.amount,
                'net_total': net_total,
                'gross_tax': total_tax + net_total
            })
        return taxes_info

    def get_total_tax(self):
        total_tax = 0.0
        for order in self.order_ids:
            total_tax += order.amount_tax
        return total_tax

    def get_total_discount(self):
        total_discount = 0.0
        if self.order_ids:
            for order in self.order_ids:
                total_discount += sum([((line.qty * line.price_unit) * line.discount) / 100 for line in order.lines])
                total_discount += sum([line.price_extra for line in order.lines])
        return total_discount

    # def get_sale_summary_by_user(self):
    #     user_summary = {}
    #     for order in self.order_ids:
    #         for line in order.lines:
    #             if line.user_id:
    #                 if not user_summary.get(line.user_id.name, None):
    #                     user_summary[line.user_id.name] = line.price_subtotal_incl
    #                 else:
    #                     user_summary[line.user_id.name] += line.price_subtotal_incl
    #             else:
    #                 if not user_summary.get(order.user_id.name, None):
    #                     user_summary[order.user_id.name] = line.price_subtotal_incl
    #                 else:
    #                     user_summary[order.user_id.name] += line.price_subtotal_incl
    #     return user_summary

    def get_total_refund(self):
        refund_total = 0.0
        if self.order_ids:
            for order in self.order_ids:
                if order.amount_total < 0:
                    refund_total += order.amount_total
        return refund_total

    def get_total_first(self):
        return sum(order.amount_total for order in self.order_ids)

    def get_gross_total(self):
        gross_total = 0.0
        if self.order_ids:
            for order in self.order_ids:
                for line in order.lines:
                    gross_total += line.qty * (line.price_unit - line.product_id.standard_price)
        return gross_total

    def build_sessions_report(self):
        vals = {}
        session_state = {
            'new_session': _('New Session'),
            'opening_control': _('Opening Control'),
            'opened': _('In Progress'),
            'closing_control': _('Closing Control'),
            'closed': _('Closed & Posted'),
        }
        for session in self:
            session_report = {}
            session_report['name'] = session.name
            session_report['current_date'] = session.get_current_date()
            session_report['current_time'] = session.get_current_time()
            session_report['state'] = session_state[session.state]
            session_report['start_at'] = session.start_at
            session_report['stop_at'] = session.stop_at
            session_report['seller'] = session.user_id.name
            session_report['cash_register_balance_start'] = session.cash_register_balance_start
            session_report['orders_count'] = len(session.order_ids)
            session_report['sales_total'] = session.get_total_sales()
            session_report['reversal_total'] = session.get_total_reversal()
            session_report['reversal_orders_detail'] = session.get_reversal_orders_detail()
            session_report['taxes'] = session.get_vat_tax()
            session_report['taxes_total'] = session.get_total_tax()
            session_report['discounts_total'] = session.get_total_discount()
            # session_report['users_summary'] = session.get_sale_summary_by_user()
            session_report['refund_total'] = session.get_total_refund()
            session_report['gross_total'] = session.get_total_first()
            session_report['gross_profit_total'] = session.get_gross_total()
            session_report['net_gross_total'] = session.get_gross_total() - session.get_total_tax()
            session_report['closing_total'] = session.cash_register_balance_end_real
            session_report['payments_amount'] = session.get_payments_amount()
            session_report['cash_in'] = session.get_cash_in_out().get('cash_in', {})
            session_report['cash_out'] = session.get_cash_in_out().get('cash_out', {})
            vals[session.id] = session_report
        return vals
