import json as json_module
from pytz import timezone, UTC
from datetime import datetime, date
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = "pos.session"

    def get_current_date(self):
        if self.env.user and self.env.user.tz:
            tz = timezone(self.env.user.tz)
        else:
            tz = UTC
        c_time = datetime.now(tz)
        return c_time.strftime('%d/%m/%Y')

    def get_current_time(self):
        if self.env.user and self.env.user.tz:
            tz = timezone(self.env.user.tz)
        else:
            tz = UTC
        c_time = datetime.now(tz)
        return c_time.strftime('%H:%M')

    def get_cash_in_out(self):
        """Retorna todos los movimientos de caja (IN y OUT) con razón/concepto."""
        movements = []
        for line in self.statement_line_ids.sorted('create_date'):
            # payment_ref tiene formato: "SessionName-Tipo-Razón" o solo la razón
            reason = line.payment_ref or ''
            movements.append({
                'amount': line.amount,
                'reason': reason,
                'date': str(line.date) if line.date else '',
            })
        return movements

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
                journal_dict['amount'] += payment.amount
            payments_amount.append(journal_dict)
        return payments_amount

    def get_manual_payments(self):
        """Retorna pagos manuales con Sello, Cuotas e Importe."""
        manual_payments = []
        # Verificar que el módulo pos_forum_manual_payment está instalado
        if 'manual_payment_values_json' not in self.env['pos.payment']._fields:
            return manual_payments
        for order in self.order_ids:
            for payment in order.payment_ids:
                if not payment.manual_payment_values_json:
                    continue
                try:
                    manual_vals = json_module.loads(payment.manual_payment_values_json)
                except (ValueError, TypeError):
                    manual_vals = {}
                tx = payment.payment_transaction_id if payment.payment_transaction_id else None
                is_manual = tx and getattr(tx, 'is_pos_manual', False)
                if not is_manual and not manual_vals:
                    continue
                sello = ''
                cuotas = ''
                ticket = ''
                if tx:
                    sello = getattr(tx, 'manual_stamp', '') or getattr(tx, 'acquirer', '') or ''
                    ticket = getattr(tx, 'manual_ticket_number', '') or getattr(tx, 'ticket_number', '') or ''
                # Cuotas puede estar en el JSON con distintos nombres
                cuotas = (
                    manual_vals.get('cuotas') or
                    manual_vals.get('installments') or
                    manual_vals.get('nro_cuotas') or
                    manual_vals.get('quota') or
                    ''
                )
                manual_payments.append({
                    'payment_method': payment.payment_method_id.name,
                    'amount': payment.amount,
                    'sello': sello,
                    'cuotas': str(cuotas) if cuotas else '',
                    'ticket': ticket,
                })
        return manual_payments

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
            'new_session': _('Nueva Sesión'),
            'opening_control': _('Control de Apertura'),
            'opened': _('En Progreso'),
            'closing_control': _('Control de Cierre'),
            'closed': _('Cerrada y Publicada'),
        }
        for session in self:
            session_report = {}
            session_report['name'] = session.name
            session_report['current_date'] = session.get_current_date()
            session_report['current_time'] = session.get_current_time()
            session_report['state'] = session_state.get(session.state, session.state)
            session_report['start_at'] = session.start_at
            session_report['stop_at'] = session.stop_at
            # Cajero: usar nombre del usuario de Odoo (el frontend sobreescribirá con el empleado real)
            session_report['seller'] = session.user_id.name
            session_report['cash_register_balance_start'] = session.cash_register_balance_start
            session_report['cash_register_balance_end_real'] = session.cash_register_balance_end_real
            session_report['cash_register_difference'] = session.cash_register_difference
            session_report['closing_notes'] = session.closing_notes or ''
            session_report['orders_count'] = len(session.order_ids)
            session_report['sales_total'] = session.get_total_sales()
            session_report['reversal_total'] = session.get_total_reversal()
            session_report['reversal_orders_detail'] = session.get_reversal_orders_detail()
            session_report['taxes'] = session.get_vat_tax()
            session_report['taxes_total'] = session.get_total_tax()
            session_report['discounts_total'] = session.get_total_discount()
            session_report['refund_total'] = session.get_total_refund()
            session_report['gross_total'] = session.get_total_first()
            session_report['gross_profit_total'] = session.get_gross_total()
            session_report['net_gross_total'] = session.get_gross_total() - session.get_total_tax()
            # closing_total: saldo teórico esperado (apertura + cobros - salidas)
            session_report['closing_total'] = session.cash_register_balance_end
            session_report['payments_amount'] = session.get_payments_amount()
            # Movimientos de caja (IN y OUT combinados)
            cash_movements = session.get_cash_in_out()
            session_report['cash_movements'] = cash_movements
            session_report['cash_in'] = [m for m in cash_movements if m['amount'] > 0]
            session_report['cash_out'] = [m for m in cash_movements if m['amount'] < 0]
            # Pagos manuales (Sello, Cuotas, Importe)
            session_report['manual_payments'] = session.get_manual_payments()
            vals[session.id] = session_report
        return vals
