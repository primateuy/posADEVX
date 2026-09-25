/** @odoo-module **/

/**
 * Envío del Reporte Z a la impresora.
 *
 * Por qué no alcanza con ``printer.printHtml``: en estas cajas el PDV no tiene
 * impresora declarada (``other_devices``, ``epson_printer_ip`` e
 * ``iface_print_via_proxy`` están vacíos), así que el servicio ``printer`` del
 * core cae en ``webPrintFallback`` y termina en ``window.print()`` del
 * navegador. Por ese camino no hay comando de corte ESC/POS y el driver
 * alimenta papel hasta el fin de página: el reporte sale sin cortar y gastando
 * de más. El recibo no tiene el problema porque va por QZ Tray, donde el corte
 * lo hace el driver al terminar el trabajo.
 *
 * Se usa QZ cuando está configurado en el PDV, y si no se mantiene el camino
 * anterior. La dependencia es blanda a propósito: ``qz_print`` lo aporta
 * ``pos_forum_qz_print``, que no todos los clientes instalan.
 *
 * @param {Object} env - env del componente (para llegar a los servicios).
 * @param {Object} pos - servicio pos (para la configuración de la caja).
 * @param {Object} printer - servicio printer del core, como respaldo.
 * @param {HTMLElement} el - el reporte ya renderizado.
 * @returns {Promise<boolean>}
 */
export async function printZReportElement(env, pos, printer, el) {
    const qzPrint = env.services.qz_print;
    const cfg = pos.config;
    if (qzPrint && cfg.use_qz_tray && cfg.qz_tray_printer_name && cfg.qz_tray_printer_name.trim()) {
        try {
            await qzPrint.printHtml(cfg.qz_tray_printer_name.trim(), el.outerHTML, {
                jobName: "Reporte Z",
            });
            return true;
        } catch (error) {
            // Bloque: si QZ no responde no se pierde el reporte; se cae al
            // camino de siempre y queda el motivo en consola.
            console.error(
                "[adevx_pos_z_report] QZ no pudo imprimir el Reporte Z; se usa el camino estándar.",
                error
            );
        }
    }
    return await printer.printHtml(el, { webPrintFallback: true });
}
