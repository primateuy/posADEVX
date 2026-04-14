/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

class ZReportButton extends Component {
    static template = 'adevx_pos_z_report.ZReportButton';

    setup() {
        this.orm = useService("orm");
        this.pos = usePos();
        this.printer = useService("printer");
    }

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
    }
}

ProductScreen.addControlButton({
    component: ZReportButton,
    condition: function () {
        return this.pos.config.report_sale_summary;
    },
})
