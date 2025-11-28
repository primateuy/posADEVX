/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";

patch(ClosePosPopup.prototype, {

    // recode
    async confirm() {
        if (!this.pos.config.cash_control || this.env.utils.floatIsZero(this.getMaxDifference())) {
            await this.closeSession();
            return;
        }
        if (this.hasUserAuthority()) {
            // add standard code inside if condition
            if (this.pos.config.accept_closing_session_diff == 'allow'){
                const { confirmed } = await this.popup.add(ConfirmPopup, {
                    title: _t("Payments Difference"),
                    body: _t(
                        "Do you want to accept payments difference and post a profit/loss journal entry?"
                    ),
                });
                if (confirmed) {
                    await this.closeSession();
                }
            }
            return;
        }
        await this.popup.add(ConfirmPopup, {
            title: _t("Payments Difference"),
            body: _t(
                "The maximum difference allowed is %s.\nPlease contact your manager to accept the closing difference.",
                this.env.utils.formatCurrency(this.props.amount_authorized_diff)
            ),
            confirmText: _t("OK"),
        });
    }

})