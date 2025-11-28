/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";

patch(ClosePosPopup.prototype, {

    setup() {
        super.setup();
        this.printer = useService("printer");
    },

    async printZReport(){
        let results = await this.orm.call("pos.session", "build_sessions_report", [[this.pos.pos_session.id]]);
        const report = renderToElement("adevx_pos_z_report.ReportSalesSummary", Object.assign({}, {
            pos: this.pos, data: results[this.pos.pos_session.id]
        }));
        return await this.printer.printHtml(report, {webPrintFallback: true});
    },

})