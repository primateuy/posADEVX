/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { ConnectionLostError } from "@web/core/network/rpc_service";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";
import { parseFloat } from "@web/views/fields/parsers";

patch(ClosePosPopup.prototype, {

    setup() {
        super.setup();
        this.printer = useService("printer");
    },

    async printZReport() {
        // Obtener nombre del cajero actual desde el frontend (empleado seleccionado)
        const cashierName = this.pos.get_cashier()?.name || '';
        let results = await this.orm.call("pos.session", "build_sessions_report", [[this.pos.pos_session.id]]);
        const data = results[this.pos.pos_session.id];
        // Sobreescribir con el cajero real del frontend
        if (cashierName) {
            data.seller = cashierName;
        }
        const report = renderToElement("adevx_pos_z_report.ReportSalesSummary", Object.assign({}, {
            pos: this.pos, data: data
        }));
        return await this.printer.printHtml(report, { webPrintFallback: true });
    },

    /**
     * Override de closeSession para auto-imprimir el Reporte Z antes de
     * redirigir al backend, cuando la opción está habilitada.
     * Duplica la lógica original para poder insertar el print en el lugar correcto.
     */
    async closeSession() {
        this.customerDisplay?.update({ closeUI: true });
        const syncSuccess = await this.pos.push_orders_with_closing_popup();
        if (!syncSuccess) {
            return;
        }
        if (this.pos.config.cash_control) {
            const response = await this.orm.call(
                "pos.session",
                "post_closing_cash_details",
                [this.pos.pos_session.id],
                {
                    counted_cash: parseFloat(
                        this.state.payments[this.props.default_cash_details.id].counted
                    ),
                }
            );
            if (!response.successful) {
                return this.handleClosingError(response);
            }
        }

        try {
            await this.orm.call("pos.session", "update_closing_control_state_session", [
                this.pos.pos_session.id,
                this.state.notes,
            ]);
        } catch (error) {
            // Manejar el error manualmente para el caso de "rescue session".
            if (!error.data && error.data.message !== "This session is already closed.") {
                throw error;
            }
        }

        try {
            const bankPaymentMethodDiffPairs = this.props.other_payment_methods
                .filter((pm) => pm.type == "bank")
                .map((pm) => [pm.id, this.getDifference(pm.id)]);
            const response = await this.orm.call("pos.session", "close_session_from_ui", [
                this.pos.pos_session.id,
                bankPaymentMethodDiffPairs,
            ]);
            if (!response.successful) {
                return this.handleClosingError(response);
            }
            // Guardar PDF del Reporte Z en el backend
            try {
                const cashierName = this.pos.get_cashier()?.name || '';
                await this.orm.call(
                    "pos.session",
                    "generate_z_report_pdf",
                    [[this.pos.pos_session.id]],
                    { cashier_name: cashierName }
                );
            } catch (pdfError) {
                console.error("Error al guardar el PDF del Reporte Z:", pdfError);
            }
            // Auto-imprimir Reporte Z si está habilitado
            if (this.pos.config.report_sale_summary) {
                try {
                    await this.printZReport();
                } catch (printError) {
                    console.error("Error al imprimir el Reporte Z:", printError);
                }
            }
            this.pos.redirectToBackend();
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                throw error;
            } else {
                await this.popup.add(ErrorPopup, {
                    title: _t("Closing session error"),
                    body: _t(
                        "An error has occurred when trying to close the session.\n" +
                            "You will be redirected to the back-end to manually close the session."
                    ),
                });
                this.pos.redirectToBackend();
            }
        }
    },

});
