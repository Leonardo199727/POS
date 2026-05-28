import api from "../api/axios";
import { getBusinessName } from "../pages/Settings";

export const printTicket = async (ventaId: number | string, token: string) => {
    try {
        const res = await api.get(`ventas/${ventaId}/`, {
            headers: { Authorization: `Token ${token}` }
        });
        const venta = res.data.data;
        
        let detalleHtml = '';
        venta.detalles.forEach((item: any) => {
            detalleHtml += `
                <tr>
                    <td colspan="3" class="item-name">${item.cantidad}x ${item.producto} ${item.variante !== 'Default' ? `- ${item.variante}` : ''}</td>
                </tr>
                <tr>
                    <td></td>
                    <td class="text-right">$${item.precio_unitario.toFixed(2)}</td>
                    <td class="text-right">$${item.subtotal.toFixed(2)}</td>
                </tr>
            `;
        });

        const html = `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Ticket ${venta.folio}</title>
                <style>
                    @media print {
                        @page { margin: 0; size: 58mm auto; }
                        body { margin: 0; }
                    }
                    body {
                        font-family: 'Courier New', Courier, monospace;
                        width: 48mm;
                        padding: 2mm 5mm 2mm 1mm;
                        font-size: 10px;
                        color: #000;
                        background: #fff;
                        margin: 0;
                        /* Prevent wrapping if possible on prices */
                        word-break: break-word;
                    }
                    .text-center { text-align: center; }
                    .text-right { text-align: right; }
                    .bold { font-weight: bold; }
                    .mb-1 { margin-bottom: 4px; }
                    .mt-2 { margin-top: 8px; }
                    .divider { border-top: 1px dashed #000; margin: 4px 0; }
                    table { width: 100%; border-collapse: collapse; table-layout: fixed; }
                    td { vertical-align: top; padding: 1px 0; font-size: 10px; }
                    .item-name { font-size: 9px; font-weight: bold; padding-bottom: 2px; }
                    .price-col { width: 45%; }
                    .total-row { font-size: 12px; font-weight: bold; }
                    .header h1 { font-size: 14px; margin: 0 0 2px 0; font-weight: 900; }
                    .header p { margin: 0; font-size: 9px; }
                    .info-grid { display: grid; grid-template-columns: auto 1fr; gap: 2px 8px; font-size: 9px; }
                </style>
            </head>
            <body>
                <div class="header text-center mb-1">
                    <h1 class="bold">${getBusinessName()}</h1>
                    <p>Punto de Venta</p>
                </div>
                <div class="divider"></div>
                <div class="info-grid">
                    <span class="bold">Folio:</span> <span>${venta.folio}</span>
                    <span class="bold">Fecha:</span> <span>${new Date(venta.created_at).toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'short' })}</span>
                    <span class="bold">Cajero:</span> <span>${venta.usuario}</span>
                    <span class="bold">Tipo:</span> <span>${venta.tipo_venta.toUpperCase()}</span>
                    ${venta.cliente ? `<span class="bold">Cliente:</span> <span>${venta.cliente.nombre}</span>` : ''}
                </div>
                <div class="divider"></div>
                <table>
                    ${detalleHtml}
                </table>
                <div class="divider"></div>
                <table>
                    <tr>
                        <td class="text-right" style="padding-right: 8px;">Subtotal:</td>
                        <td class="text-right price-col">$${venta.subtotal.toFixed(2)}</td>
                    </tr>
                    ${venta.total_comision > 0 ? `
                    <tr>
                        <td class="text-right" style="padding-right: 8px;">Comisión T.C. (4.5%):</td>
                        <td class="text-right price-col">$${venta.total_comision.toFixed(2)}</td>
                    </tr>
                    ` : ''}
                    <tr class="total-row">
                        <td class="text-right" style="padding-right: 8px;">TOTAL:</td>
                        <td class="text-right">$${(venta.total + (venta.total_comision || 0)).toFixed(2)}</td>
                    </tr>
                </table>
                ${venta.tipo_venta === 'credito' ? `
                <div class="divider"></div>
                <table>
                    <tr>
                        <td class="text-right" style="padding-right: 8px;">Pago Inicial:</td>
                        <td class="text-right price-col">$${(venta.total_pagado + (venta.total_comision || 0)).toFixed(2)}</td>
                    </tr>
                    <tr>
                        <td class="text-right" style="padding-right: 8px;">A Crédito:</td>
                        <td class="text-right price-col">$${(venta.total - venta.total_pagado).toFixed(2)}</td>
                    </tr>
                </table>
                <div class="divider"></div>
                <div class="text-center bold" style="font-size: 10px; margin: 4px 0;">
                    Saldo Actual: $${venta.cliente?.saldo_actual?.toFixed(2) || '0.00'}
                </div>
                ` : ''}
                <div class="divider"></div>
                <div class="text-center mt-2" style="font-size: 10px;">
                    <p class="bold mb-1">¡Gracias por su compra!</p>
                    <p style="font-size: 9px;">*** Este documento no es un comprobante fiscal ***</p>
                </div>
                <!-- Feed paper mechanism -->
                <div style="height: 12mm;"></div>
            </body>
            </html>
        `;

        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        document.body.appendChild(iframe);

        iframe.contentWindow?.document.open();
        iframe.contentWindow?.document.write(html);
        iframe.contentWindow?.document.close();

        // Esperar un instante para que el navegador procese el DOM del iframe
        setTimeout(() => {
            if (iframe.contentWindow) {
                iframe.contentWindow.focus();
                iframe.contentWindow.print();
            }
            // Limpiar el iframe de la memoria después de un buen rato
            setTimeout(() => {
                if (document.body.contains(iframe)) {
                    document.body.removeChild(iframe);
                }
            }, 120000); // 2 minutos
        }, 500);
        
    } catch (err) {
        console.error("Error generating ticket:", err);
    }
}


// ─── Ticket para Abonos y Cargos ────────────────────────────

interface AbonoTicketData {
    tipo: 'ABONO' | 'CARGO';
    clienteNombre: string;
    cajero: string;
    // Abono fields
    folio?: string;
    metodoPago?: string;
    montoCliente?: number;
    cargoTarjeta?: number;
    totalCobrado?: number;
    // Cargo fields
    concepto?: string;
    montoCargo?: number;
    // Shared
    saldoAnterior: number;
    saldoNuevo: number;
}

export const printAbonoTicket = (data: AbonoTicketData) => {
    const fecha = new Date().toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'short' });

    const isAbono = data.tipo === 'ABONO';
    const titulo = isAbono ? 'RECIBO DE ABONO' : 'RECIBO DE CARGO';

    // Build the body section based on operation type
    let operationHtml = '';

    if (isAbono) {
        operationHtml = `
            <div class="info-grid">
                <span class="bold">Método:</span> <span>${data.metodoPago || 'N/A'}</span>
            </div>
            <div class="divider"></div>
            <table>
                <tr>
                    <td class="text-right" style="padding-right: 8px;">Abono:</td>
                    <td class="text-right price-col">$${(data.montoCliente || 0).toFixed(2)}</td>
                </tr>
                ${(data.cargoTarjeta || 0) > 0 ? `
                <tr>
                    <td class="text-right" style="padding-right: 8px;">Comisión T.C. (4.5%):</td>
                    <td class="text-right price-col">$${(data.cargoTarjeta || 0).toFixed(2)}</td>
                </tr>
                ` : ''}
                <tr class="total-row">
                    <td class="text-right" style="padding-right: 8px;">TOTAL COBRADO:</td>
                    <td class="text-right">$${(data.totalCobrado || data.montoCliente || 0).toFixed(2)}</td>
                </tr>
            </table>
        `;
    } else {
        operationHtml = `
            <div class="info-grid">
                <span class="bold">Concepto:</span> <span>${data.concepto || 'N/A'}</span>
            </div>
            <div class="divider"></div>
            <table>
                <tr class="total-row">
                    <td class="text-right" style="padding-right: 8px;">CARGO:</td>
                    <td class="text-right">$${(data.montoCargo || 0).toFixed(2)}</td>
                </tr>
            </table>
        `;
    }

    const html = `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>${titulo}</title>
            <style>
                @media print {
                    @page { margin: 0; size: 58mm auto; }
                    body { margin: 0; }
                }
                body {
                    font-family: 'Courier New', Courier, monospace;
                    width: 48mm;
                    padding: 2mm 5mm 2mm 1mm;
                    font-size: 10px;
                    color: #000;
                    background: #fff;
                    margin: 0;
                    word-break: break-word;
                }
                .text-center { text-align: center; }
                .text-right { text-align: right; }
                .bold { font-weight: bold; }
                .mb-1 { margin-bottom: 4px; }
                .mt-2 { margin-top: 8px; }
                .divider { border-top: 1px dashed #000; margin: 4px 0; }
                table { width: 100%; border-collapse: collapse; table-layout: fixed; }
                td { vertical-align: top; padding: 1px 0; font-size: 10px; }
                .price-col { width: 45%; }
                .total-row { font-size: 12px; font-weight: bold; }
                .header h1 { font-size: 14px; margin: 0 0 2px 0; font-weight: 900; }
                .header p { margin: 0; font-size: 9px; }
                .info-grid { display: grid; grid-template-columns: auto 1fr; gap: 2px 8px; font-size: 9px; }
                .saldo-box { text-align: center; font-size: 10px; margin: 4px 0; }
                .saldo-box .label { font-size: 9px; font-weight: bold; margin-bottom: 2px; }
                .saldo-box .amount { font-size: 13px; font-weight: 900; }
            </style>
        </head>
        <body>
            <div class="header text-center mb-1">
                <h1 class="bold">${getBusinessName()}</h1>
                <p>${titulo}</p>
            </div>
            <div class="divider"></div>
            <div class="info-grid">
                ${isAbono && data.folio ? `<span class="bold">Folio:</span> <span>${data.folio}</span>` : ''}
                <span class="bold">Fecha:</span> <span>${fecha}</span>
                <span class="bold">Cajero:</span> <span>${data.cajero}</span>
                <span class="bold">Cliente:</span> <span>${data.clienteNombre}</span>
            </div>
            <div class="divider"></div>
            ${operationHtml}
            <div class="divider"></div>
            <table>
                <tr>
                    <td class="text-right" style="padding-right: 8px;">Saldo Anterior:</td>
                    <td class="text-right price-col">$${data.saldoAnterior.toFixed(2)}</td>
                </tr>
                <tr class="total-row">
                    <td class="text-right" style="padding-right: 8px;">Saldo Nuevo:</td>
                    <td class="text-right">$${data.saldoNuevo.toFixed(2)}</td>
                </tr>
            </table>
            <div class="divider"></div>
            <div class="text-center mt-2" style="font-size: 10px;">
                <p class="bold mb-1">${isAbono ? '¡Gracias por su pago!' : 'Cargo registrado'}</p>
                <p style="font-size: 9px;">*** Este documento no es un comprobante fiscal ***</p>
            </div>
            <!-- Feed paper -->
            <div style="height: 12mm;"></div>
        </body>
        </html>
    `;

    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    document.body.appendChild(iframe);

    iframe.contentWindow?.document.open();
    iframe.contentWindow?.document.write(html);
    iframe.contentWindow?.document.close();

    setTimeout(() => {
        if (iframe.contentWindow) {
            iframe.contentWindow.focus();
            iframe.contentWindow.print();
        }
        setTimeout(() => {
            if (document.body.contains(iframe)) {
                document.body.removeChild(iframe);
            }
        }, 120000);
    }, 500);
}
