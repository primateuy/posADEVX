/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { getZReportReceiptLabels } from "@adevx_pos_z_report/js/z_report_print_labels";

patch(ClosePosPopup.prototype, {

    setup() {
        super.setup();
        this.printer = useService("printer");
    },

    /** Texto del botón de impresión del reporte Z en el cierre (traducible vía i18n). */
    get zReportButtonLabel() {
        return _t("Z-Report");
    },

    async printZReport(){
        let results = await this.orm.call("pos.session", "build_sessions_report", [[this.pos.pos_session.id]]);
        const report = renderToElement("adevx_pos_z_report.ReportSalesSummary", {
            pos: this.pos,
            data: results[this.pos.pos_session.id],
            labels: getZReportReceiptLabels(),
        });
        return await this.printer.printHtml(report, {webPrintFallback: true});
    },

})