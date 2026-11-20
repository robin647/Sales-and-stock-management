import { useEffect, useRef, useState } from "react";
import { errorMessage } from "../../utils/apiError";
import { Heading, LoadState, Pager } from "./components";
import { download, useWorkspaceData, workspaceApi } from "./data";
import { deliveryFees, suggestDeliveryZone } from "./deliveryZone";
import { districts, suggestSteadfastDestination } from "./steadfastDistrict";
import styles from "./workspace.module.css";

const ordersPath = "facebook-orders/";
const emptyOrder = {
  tracking_id: "", invoice: "", customer_name: "", phone: "", address: "", area: "",
  quantity: "", cod_amount: "", delivery_zone: "", status: "pending", courier_charge: "",
  weight_kg: "", courier_origin: "1", courier_destination: "", courier_delivery: "home",
};
const imageTypes = ["image/jpeg", "image/png", "image/webp"];
const statusLabels = { pending: "Pending", delivered: "Delivered", cancelled: "Cancelled" };
const fields = [
  ["tracking_id", "Tracking ID (SF-ID)", { maxLength: 64, required: true }],
  ["invoice", "Invoice number", { maxLength: 64 }],
  ["customer_name", "Customer name", { maxLength: 150, required: true }],
  ["phone", "Phone number", { type: "tel", maxLength: 32, required: true }],
  ["area", "Area", { maxLength: 150 }],
  ["quantity", "Products sold (units)", { type: "number", min: 1, step: 1, required: true }],
  ["cod_amount", "Cash on delivery (৳)", { type: "number", min: 0, max: 9999999999.99, step: ".01", required: true }],
];
const taka = new Intl.NumberFormat("en-BD", { style: "currency", currency: "BDT" });
const number = new Intl.NumberFormat("en-BD");
const date = new Intl.DateTimeFormat("en-BD", { dateStyle: "medium", timeZone: "Asia/Dhaka" });

export default function FacebookOrders({ notify }) {
  const [page, setPage] = useState(1);
  const [draft, setDraft] = useState(emptyOrder);
  const [editing, setEditing] = useState(null);
  const [image, setImage] = useState("");
  const [pdfName, setPdfName] = useState("");
  const [reading, setReading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [progress, setProgress] = useState(null);
  const [scanMessage, setScanMessage] = useState("");
  const [failure, setFailure] = useState("");
  const [period, setPeriod] = useState("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [range, setRange] = useState("period=all");
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const editor = useRef(null);
  const result = useWorkspaceData(`${ordersPath}?page=${page}&${range}`);
  const busy = reading || saving;
  const zone = draft.delivery_zone || suggestDeliveryZone(draft.address, draft.area);
  const destination = draft.courier_destination || suggestSteadfastDestination(draft.address, draft.area);
  const weight = Number(draft.weight_kg);
  const quoteParams = destination && weight >= 0.01 && weight <= 600 ? new URLSearchParams({
    origin: draft.courier_origin, destination, weight: String(weight), delivery: draft.courier_delivery,
  }) : null;
  const quote = useWorkspaceData(quoteParams ? `${ordersPath}steadfast-quote/?${quoteParams}` : null);
  const quotedCharge = quote.data?.courier_charge;
  const totals = result.data?.summary;
  const history = result.status === 404
    ? { ...result, error: "Facebook Orders is unavailable on the current backend. Retry after the backend updates." }
    : result;

  useEffect(() => () => { if (image) URL.revokeObjectURL(image); }, [image]);

  function clearDraft() {
    setDraft(emptyOrder);
    setEditing(null);
    setImage("");
    setPdfName("");
    setScanMessage("");
    setFailure("");
  }

  async function readLabel(event) {
    const file = event.currentTarget.files?.[0];
    if (!file) return;
    event.currentTarget.value = "";
    setFailure("");
    setScanMessage("");
    const isPdf = file.type === "application/pdf" || (!file.type && /\.pdf$/i.test(file.name));
    if ((!isPdf && !imageTypes.includes(file.type)) || file.size > 12 * 1024 * 1024) {
      setFailure("Choose a JPG, PNG, WebP or single-page PDF up to 12 MB.");
      return;
    }
    setImage(isPdf ? "" : URL.createObjectURL(file));
    setPdfName(isPdf ? file.name : "");
    setDraft(emptyOrder);
    setReading(true);
    setProgress(null);
    try {
      const { default: read } = isPdf ? await import("./readCourierPdf") : await import("./readCourierImage");
      const { courier_delivery, ...extracted } = await read(file, setProgress);
      setDraft({ ...emptyOrder, ...extracted, courier_delivery: courier_delivery || emptyOrder.courier_delivery });
      const missing = [["invoice", "invoice number"], ["cod_amount", "COD"], ["weight_kg", "weight"]]
        .filter(([key]) => !extracted[key]).map(([, label]) => label);
      setScanMessage(missing.length
        ? `Review the label and enter the missing fields: ${missing.join(", ")}.`
        : "Review the extracted fields and confirm the number of products before saving.");
    } catch {
      setFailure(isPdf
        ? "The PDF could not be read. Upload a single-page, unlocked PDF with one label."
        : "The image could not be read. Try a clearer label or enter the details manually.");
    } finally {
      setReading(false);
    }
  }

  function change(event) {
    const { name, value } = event.target;
    setDraft((current) => ({
      ...current,
      ...(["address", "area"].includes(name) ? { delivery_zone: "" } : {}),
      [name]: value,
    }));
  }

  function edit(order) {
    clearDraft();
    setEditing(order.id);
    setDraft(Object.fromEntries(Object.keys(emptyOrder).map((key) => [key, order[key] ?? emptyOrder[key]])));
    editor.current.focus();
  }

  async function save(event) {
    event.preventDefault();
    setSaving(true);
    setFailure("");
    const payload = {
      ...draft, delivery_zone: zone, courier_destination: destination || null,
      weight_kg: draft.weight_kg || null, courier_charge: draft.courier_charge || quotedCharge || null,
    };
    try {
      if (editing) {
        await workspaceApi.patch(`${ordersPath}${editing}/`, payload);
        notify("Facebook order updated.");
        result.reload();
      } else {
        await workspaceApi.post(ordersPath, payload);
        notify("Facebook order saved.");
        if (page === 1) result.reload();
        else setPage(1);
      }
      clearDraft();
    } catch (error) {
      setFailure(errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  function applyRange(event) {
    event.preventDefault();
    const params = new URLSearchParams({ period });
    if (period === "custom") {
      params.set("start_date", startDate);
      params.set("end_date", endDate);
    }
    setRange(params.toString());
    setPage(1);
    setExportError("");
  }

  async function exportOrders() {
    setExporting(true);
    setExportError("");
    try {
      await download(`${ordersPath}export/?${range}`, "facebook-orders.xlsx");
    } catch (error) {
      setExportError(errorMessage(error));
    } finally {
      setExporting(false);
    }
  }

  return <>
    <Heading title="Facebook Orders" />
    <section className={styles.panel} aria-label="Order history date range">
      <form className={styles.actions} onSubmit={applyRange}>
        <label>Recorded date
          <select value={period} onChange={(event) => setPeriod(event.target.value)}>
            <option value="all">All time</option>
            <option value="week">Last 7 days</option>
            <option value="month">Last 30 days</option>
            <option value="custom">Custom dates</option>
          </select>
        </label>
        {period === "custom" && <>
          <label>From<input type="date" value={startDate} max={endDate || undefined} onChange={(event) => setStartDate(event.target.value)} required /></label>
          <label>Through<input type="date" value={endDate} min={startDate || undefined} onChange={(event) => setEndDate(event.target.value)} required /></label>
        </>}
        <button type="submit">Apply dates</button>
        <button type="button" onClick={exportOrders} disabled={exporting || !result.data}>{exporting ? "Downloading…" : "Download filtered XLSX"}</button>
      </form>
      {exportError && <p className={styles.error} role="alert">{exportError}</p>}
    </section>
    {totals && <>
      <div className={`${styles.stats} ${styles.orderStats}`} aria-label="Totals for selected order dates">
        <div className={`${styles.panel} ${styles.salesTotal}`}><span>Net sales</span><strong>{totals.net_sales == null ? "—" : taka.format(totals.net_sales)}</strong></div>
        <div className={styles.panel}><span>Collected COD</span><strong>{taka.format(totals.cod)}</strong></div>
        <div className={styles.panel}><span>Steadfast delivery cost</span><strong>{taka.format(totals.courier_charge ?? 0)}</strong></div>
        {totals.steadfast_fee != null && <div className={styles.panel}><span>Steadfast COD fee (1%)</span><strong>{taka.format(totals.steadfast_fee)}</strong></div>}
        <div className={styles.panel}><span>Products sold (units)</span><strong>{number.format(totals.units)}</strong></div>
        <div className={styles.panel}><span>Orders recorded</span><strong>{number.format(totals.orders)}</strong><small>{number.format(totals.pending)} pending · {number.format(totals.cancelled)} cancelled</small></div>
      </div>
      {totals.pending > 0 && <p className={styles.scanMessage}>Pending orders enter the sales or cost totals when marked delivered or cancelled.</p>}
    </>}
    <div className={styles.orderIntake}>
      <section className={styles.panel}>
        <h2>Courier label</h2>
        <label className={styles.labelUpload}>
          <span>Upload courier label</span>
          <input type="file" accept="image/jpeg,image/png,image/webp,application/pdf,.pdf" disabled={busy || Boolean(editing)} onChange={readLabel} />
          <small>JPG, PNG, WebP or single-page PDF · Up to 12 MB</small>
        </label>
        {reading && <p role="status">{progress === null ? "Preparing image scan…" : `Reading label… ${progress}%`}</p>}
        {image && <img className={styles.labelPreview} src={image} alt="Courier label selected for this order" />}
        {pdfName && <p>{pdfName}</p>}
      </section>
      <section className={styles.panel}>
        <h2 ref={editor} tabIndex={-1}>{editing ? "Edit order" : "Order details"}</h2>
        {scanMessage && <p role="status" className={styles.scanMessage}>{scanMessage}</p>}
        <form onSubmit={save}>
          <fieldset className={styles.editor} disabled={busy}>
            {fields.map(([name, label, props]) => <label key={name}>{label}
              <input name={name} value={draft[name]} onChange={change} {...props} />
            </label>)}
            <label className={styles.wide}>Delivery address
              <textarea name="address" maxLength={500} rows={2} required value={draft.address} onChange={change} />
            </label>
            <label>Delivery zone
              <select name="delivery_zone" value={zone} onChange={change}>
                <option value="">Select delivery zone</option>
                <option value="inside">Inside Dhaka</option>
                <option value="outside">Outside Dhaka</option>
              </select>
              {!draft.delivery_zone && zone && <small>Suggested from the address. Change if needed.</small>}
            </label>
            <label>Customer delivery rate
              <input readOnly value={zone ? taka.format(deliveryFees[zone]) : ""} />
            </label>
            <label>Order status
              <select name="status" value={draft.status} onChange={change}>
                {Object.entries(statusLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
              </select>
            </label>
            <label>Parcel weight (kg)
              <input name="weight_kg" type="number" min=".01" max="600" step=".01" value={draft.weight_kg} onChange={change} />
            </label>
            <label>Steadfast pickup district
              <select name="courier_origin" value={draft.courier_origin} onChange={change}>
                {districts.map(({ id, name }) => <option value={id} key={id}>{name}</option>)}
              </select>
            </label>
            <label>Steadfast delivery district
              <select name="courier_destination" value={destination} onChange={change}>
                <option value="">Select delivery district</option>
                {districts.map(({ id, name }) => <option value={id} key={id}>{name}</option>)}
              </select>
            </label>
            <label>Steadfast delivery type
              <select name="courier_delivery" value={draft.courier_delivery} onChange={change}>
                <option value="home">Home</option>
                <option value="point">Point</option>
              </select>
            </label>
            <div>
              <label>Steadfast delivery charge override (৳)
                <input name="courier_charge" type="number" min="0" max="9999999999.99" step=".01" value={draft.courier_charge} onChange={change}
                  placeholder={quotedCharge ?? ""} required={draft.status !== "pending" && quotedCharge == null} />
              </label>
              {quoteParams && <small role="status">{quote.error || (quotedCharge == null ? "Getting Steadfast rate…" : `Steadfast standard rate: ${taka.format(quotedCharge)}`)}</small>}
              <small>Leave blank to use the calculated rate. Enter your merchant bill amount if it differs.</small>
            </div>
            {failure && <p className={`${styles.error} ${styles.wide}`} role="alert">{failure}</p>}
            <div className={`${styles.actions} ${styles.wide}`}>
              <button className={styles.primary}>{saving ? "Saving…" : editing ? "Save changes" : "Save order"}</button>
              <button type="button" onClick={clearDraft}>{editing ? "Cancel edit" : "Clear"}</button>
            </div>
          </fieldset>
        </form>
      </section>
    </div>
    <section className={styles.panel}>
      <h2>Order history</h2>
      <LoadState result={history}>{(data) => data.results.length ? <>
        <div className={styles.tableWrap}><table>
          <thead><tr><th>Tracking ID</th><th>Customer</th><th>Delivery address</th><th>Status</th><th>Units</th><th>COD requested</th><th>Customer rate</th><th>Steadfast charge</th><th>Net sales</th><th>Recorded</th><th>Actions</th></tr></thead>
          <tbody>{data.results.map((order) => <tr key={order.id}>
            <td><strong>{order.tracking_id}</strong>{order.invoice && <small>Invoice {order.invoice}</small>}</td>
            <td>{order.customer_name}<small>{order.phone}</small></td>
            <td className={styles.orderAddress}>{order.address}{order.area && <small>{order.area}</small>}</td>
            <td>{statusLabels[order.status]}</td>
            <td>{number.format(order.quantity)}</td>
            <td className={styles.orderAmount}>{taka.format(order.cod_amount)}</td>
            <td className={styles.orderAmount}>{order.delivery_charge == null ? "Set zone" : taka.format(order.delivery_charge)}</td>
            <td className={styles.orderAmount}>{order.courier_charge == null ? "—" : taka.format(order.courier_charge)}</td>
            <td className={styles.orderAmount}>{order.status === "pending" || order.net_sales == null ? "—" : taka.format(order.net_sales)}</td>
            <td>{date.format(new Date(order.created_at))}</td>
            <td><button type="button" disabled={busy} onClick={() => edit(order)}>Edit</button></td>
          </tr>)}</tbody>
        </table></div>
        <Pager data={data} page={page} onPage={setPage} />
      </> : <p className={styles.state}>No Facebook orders recorded yet.</p>}</LoadState>
    </section>
  </>;
}
