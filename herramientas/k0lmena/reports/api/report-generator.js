"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
// multiple-cucumber-html-reporter v4 es solo ESM: se carga con import() dinámico.
import("multiple-cucumber-html-reporter").then((report) => report.generate({
    jsonDir: "reports/api", // Directorio donde está el archivo cucumber-report.json
    reportPath: "reports/api", // Carpeta donde se generará el reporte HTML
    metadata: {
        browser: {
            name: "chrome",
            version: "latest"
        },
        device: "Local test machine",
        platform: {
            name: "Windows",
            version: "10"
        }
    },
    customData: {
        title: "Test Execution Report",
        data: [
            { label: "Project", value: "K0lmena" },
            { label: "Execution Date", value: new Date().toLocaleString() }
        ]
    }
}));
