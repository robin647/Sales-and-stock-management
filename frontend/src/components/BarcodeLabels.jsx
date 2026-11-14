import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { barcodeFitsLabel, encodeProductBarcode, productLabelPrice } from "../utils/barcode";
import "./barcode-labels.css";

const sizes = { small: { width: 50, height: 30, barHeight: 10 }, medium: { width: 70, height: 40, barHeight: 15 }, large: { width: 100, height: 50, barHeight: 20 } };
const money = value => "৳ " + value.toLocaleString("en-BD", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function BarcodeLabels({ products, onClose }) {
  const [size, setSize] = useState("small");
  const [paper, setPaper] = useState("a4");
  const [copies, setCopies] = useState(1);
  const dimensions = sizes[size];
  const prepared = useMemo(() => products.map(product => {
    try { return { product, barcode: encodeProductBarcode(product.code) }; }
    catch (error) { return { product, error: error.message }; }
  }), [products]);
  const count = Number(copies);
  const total = products.length * count;
  const validCount = Number.isInteger(count) && count >= 1 && count <= 100 && total <= 500;
  const errors = prepared.flatMap(item => item.error ? [item.product.name + ": " + item.error]
    : !barcodeFitsLabel(item.barcode, dimensions.width) ? [item.product.name + ": code is too long for this label size. Choose a larger label or a shorter unique product code."] : []);
  const labels = validCount && !errors.length ? prepared.flatMap(item => Array.from({ length: count }, (_, index) => ({ ...item, key: item.product.id + "-" + index }))) : [];

  useEffect(() => {
    const close = event => { if (event.key === "Escape") onClose(); };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [onClose]);

  const printStyles = `@page { size: ${paper === "a4" ? "A4 portrait" : dimensions.width + "mm " + dimensions.height + "mm"}; margin: ${paper === "a4" ? "10mm" : "0"}; }
    @media print {
      .barcode-sheet { ${paper === "thermal" ? "display:block !important;" : "display:grid !important; grid-template-columns:repeat(auto-fill," + dimensions.width + "mm) !important; gap:3mm !important;"} }
      .barcode-label { ${paper === "thermal" ? "break-after:page; page-break-after:always;" : ""} }
      .barcode-label:last-child { break-after:auto; page-break-after:auto; }
    }`;

  return createPortal(<div className="barcode-print-root commerce" onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <style>{printStyles}</style>
    <section className="barcode-dialog" role="dialog" aria-modal="true" aria-labelledby="barcode-title">
      <header className="barcode-dialog-heading"><div><span className="commerce-kicker">PRODUCT LABELS</span><h2 id="barcode-title">Barcode studio</h2><p>{products.length} product(s) · {validCount ? total : 0} labels</p></div><button className="barcode-close" autoFocus onClick={onClose} aria-label="Close barcode preview">×</button></header>
      <div className="barcode-controls"><label>Label size<select value={size} onChange={event => setSize(event.target.value)}><option value="small">50 × 30 mm</option><option value="medium">70 × 40 mm</option><option value="large">100 × 50 mm</option></select></label><label>Paper<select value={paper} onChange={event => setPaper(event.target.value)}><option value="a4">A4 sheet</option><option value="thermal">Thermal / single-label roll</option></select></label><label>Copies per product<input type="number" min="1" max="100" step="1" value={copies} onChange={event => setCopies(event.target.value)} /></label><button className="c-button" disabled={!validCount || !!errors.length || !labels.length} onClick={() => window.print()}>Print / Save PDF</button></div>
      <div className="barcode-guidance">Use 100% / Actual size in the print dialog and turn off browser headers and footers. Labels use the current discount price when available. Choose matching paper dimensions for a thermal printer.</div>
      {!validCount && <div className="c-alert error barcode-warning" role="alert">Choose 1–100 copies per product, with a maximum of 500 labels per print.</div>}
      {!!errors.length && <div className="c-alert error barcode-warning" role="alert">{errors.map(message => <p key={message}>{message}</p>)}</div>}
      <div className="barcode-preview"><div className="barcode-sheet" style={{ "--label-width": dimensions.width + "mm", "--label-height": dimensions.height + "mm", "--barcode-height": dimensions.barHeight + "mm" }}>{labels.map(({ product, barcode, key }) => <article className="barcode-label" key={key}>
        <div className="barcode-product-name" title={product.name + (product.size ? " · " + product.size : "")}>{product.name}{product.size ? " · " + product.size : ""}</div>
        <svg className="product-barcode" viewBox={`0 0 ${barcode.modules} 40`} preserveAspectRatio="none" role="img" aria-label={"Code 128 barcode for " + barcode.code}><rect x="0" y="0" width={barcode.modules} height="40" fill="#fff" />{barcode.bars.map(bar => <rect key={bar.x} x={bar.x} y="0" width={bar.width} height="40" fill="#000" />)}</svg>
        <div className="barcode-product-code">{barcode.code}</div><div className="barcode-product-price">{money(productLabelPrice(product))}</div>
      </article>)}</div></div>
    </section>
  </div>, document.body);
}
