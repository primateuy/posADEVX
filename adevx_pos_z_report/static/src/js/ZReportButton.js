/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { getZReportReceiptLabels } from "@adevx_pos_z_report/js/z_report_print_labels";

class ZReportButton extends Component {
    static template = 'adevx_pos_z_report.ZReportButton';

    setup() {
        this.orm = useService("orm");
        this.pos = usePos();
        this.printer = useService("printer");
    }

    /** Etiqueta del botón de reporte Z en la pantalla de productos. */
    get zReportControlLabel() {
        return _t("Z Report");
    }

    async printZReport() {
        let results = await this.orm.call("pos.session", "build_sessions_report", [[this.pos.pos_session.id]]);
        const report = renderToElement("adevx_pos_z_report.ReportSalesSummary", {
            pos: this.pos,
            data: results[this.pos.pos_session.id],
            labels: getZReportReceiptLabels(),
        });
        return await this.printer.printHtml(report, {webPrintFallback: true});
    }
}

ProductScreen.addControlButton({
    component: ZReportButton,
    condition: function () {
        return this.pos.config.report_sale_summary;
    },
})
