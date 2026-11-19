import { useEffect, useRef, useState } from "react";
import { errorMessage } from "../../utils/apiError";
import { Heading, LoadState, Pager } from "./components";
import { useWorkspaceData, workspaceApi } from "./data";
import styles from "./workspace.module.css";

const ordersPath = "facebook-orders/";
const emptyOrder = {
  tracking_id: "", invoice: "", customer_name: "", phone: "", address: "", area: "",
  quantity: "", cod_amount: "",
};
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
  const [reading, setReading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [progress, setProgress] = useState(null);
  const [scanMessage, setScanMessage] = useState("");
  const [failure, setFailure] = useState("");
  const editor = useRef(null);
  const result = useWorkspaceData(`${ordersPath}?page=${page}`);
  const busy = reading || saving;

  useEffect(() => () => { if (image) URL.revokeObjectURL(image); }, [image]);

  function clearDraft() {
    setDraft(emptyOrder);
    setEditing(null);
    setImage("");
    setScanMessage("");
    setFailure("");
  }

  async function readImage(event) {
    const file = event.currentTarget.files?.[0];
    if (!file) return;
    event.currentTarget.value = "";
    setFailure("");
    setScanMessage("");
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 12 * 1024 * 1024) {
      setFailure("Choose a JPG, PNG, or WebP image up to 12 MB.");
      return;
    }
    setImage(URL.createObjectURL(file));
    setDraft(emptyOrder);
    setReading(true);
    setProgress(null);
    try {
      const { default: readCourierImage } = await import("./readCourierImage");
      const extracted = await readCourierImage(file, setProgress);
      setDraft(extracted);
      setScanMessage(Object.values(extracted).some(Boolean)
        ? "Review the extracted fields and confirm the number of products before saving."
        : "No matching label fields were found. Enter the details from the image.");
    } catch {
      setFailure("The image could not be read. Try a clearer label or enter the details manually.");
    } finally {
      setReading(false);
    }
  }

  function change(event) {
    const { name, value } = event.target;
    setDraft((current) => ({ ...current, [name]: value }));
  }

  function edit(order) {
    clearDraft();
    setEditing(order.id);
    setDraft(Object.fromEntries(Object.keys(emptyOrder).map((key) => [key, order[key]])));
    editor.current.focus();
  }

  async function save(event) {
    event.preventDefault();
    setSaving(true);
    setFailure("");
    try {
      if (editing) {
        await workspaceApi.patch(`${ordersPath}${editing}/`, draft);
        notify("Facebook order updated.");
        result.reload();
      } else {
        await workspaceApi.post(ordersPath, draft);
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

  return <>
    <Heading title="Facebook Orders" />
    {result.data && <div className={styles.stats} aria-label="All Facebook order totals">
      <div className={`${styles.panel} ${styles.salesTotal}`}><span>Total order value (COD)</span><strong>{taka.format(result.data.summary.cod)}</strong></div>
      <div className={styles.panel}><span>Products sold (units)</span><strong>{number.format(result.data.summary.units)}</strong></div>
      <div className={styles.panel}><span>Orders recorded</span><strong>{number.format(result.data.summary.orders)}</strong></div>
    </div>}
    <div className={styles.orderIntake}>
      <section className={styles.panel}>
        <h2>Courier label</h2>
        <label className={styles.labelUpload}>
          <span>Upload label image</span>
          <input type="file" accept="image/jpeg,image/png,image/webp" disabled={busy || Boolean(editing)} onChange={readImage} />
          <small>JPG, PNG or WebP · Up to 12 MB</small>
        </label>
        {reading && <p role="status">{progress === null ? "Preparing image scan…" : `Reading label… ${progress}%`}</p>}
        {image && <img className={styles.labelPreview} src={image} alt="Courier label selected for this order" />}
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
      <LoadState result={result}>{(data) => data.results.length ? <>
        <div className={styles.tableWrap}><table>
          <thead><tr><th>Tracking ID</th><th>Customer</th><th>Delivery address</th><th>Units</th><th>COD</th><th>Recorded</th><th>Actions</th></tr></thead>
          <tbody>{data.results.map((order) => <tr key={order.id}>
            <td><strong>{order.tracking_id}</strong>{order.invoice && <small>Invoice {order.invoice}</small>}</td>
            <td>{order.customer_name}<small>{order.phone}</small></td>
            <td className={styles.orderAddress}>{order.address}{order.area && <small>{order.area}</small>}</td>
            <td>{number.format(order.quantity)}</td>
            <td className={styles.orderAmount}>{taka.format(order.cod_amount)}</td>
            <td>{date.format(new Date(order.created_at))}</td>
            <td><button type="button" disabled={busy} onClick={() => edit(order)}>Edit</button></td>
          </tr>)}</tbody>
        </table></div>
        <Pager data={data} page={page} onPage={setPage} />
      </> : <p className={styles.state}>No Facebook orders recorded yet.</p>}</LoadState>
    </section>
  </>;
}
