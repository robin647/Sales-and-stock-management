import { useState } from "react";
import { errorMessage } from "../../utils/apiError";
import { OfferFilters } from "./Catalog";
import { Heading, LoadState, Modal, Pager } from "./components";
import { download, useWorkspaceData, workspaceApi } from "./data";
import styles from "./workspace.module.css";

export function Downloads({ notify }) {
  const categories = useWorkspaceData("categories/");
  const [scope, setScope] = useState(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");
  const result = useWorkspaceData(scope === null ? null : `downloads/bulk/?${scope}&preview=1`);

  function count(event) {
    event.preventDefault();
    const query = new URLSearchParams(Array.from(new FormData(event.currentTarget)).filter(([, value]) => value));
    setFailure("");
    if (scope === query.toString()) result.reload();
    setScope(query.toString());
  }

  async function exportZip() {
    setBusy(true);
    setFailure("");
    try {
      await download(`downloads/bulk/?${scope}`, "edited-catalog.zip");
      notify("Edited image archive downloaded.");
    } catch (error) {
      setFailure(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  return <>
    <Heading title="Asset downloads" />
    <section className={styles.panel}>
      <h2>Bulk edited images</h2>
      <p>Files are grouped by offer, category and product.</p>
      <LoadState result={categories}>{(rows) => (
        <form className={styles.filters} onSubmit={count} onChange={() => setScope(null)}>
          <fieldset className={styles.filters} disabled={busy}>
            <OfferFilters categories={rows} />
            <div className={styles.actions}><button className={styles.primary}>Count files</button></div>
          </fieldset>
        </form>
      )}</LoadState>
      {scope !== null && <LoadState result={result}>{(data) => (
        <div className={styles.actions}>
          <p>{data.images} edited {data.images === 1 ? "image" : "images"} in {data.products} {data.products === 1 ? "product" : "products"}</p>
          <button className={styles.primary} disabled={busy || !data.images} onClick={exportZip}>{busy ? "Preparing ZIP…" : "Download ZIP"}</button>
        </div>
      )}</LoadState>}
      {failure && <p className={styles.error} role="alert">{failure}</p>}
    </section>
  </>;
}

function ManageEditor({ row, kind, close, saved }) {
  const accounts = kind === "accounts";
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");

  async function save(event) {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget));
    if (accounts) {
      if (!payload.password) delete payload.password;
      payload.is_active = payload.is_active === "on";
      if (row.is_active && !payload.is_active && !window.confirm("Deactivate this moderator account?")) return;
    }
    setBusy(true);
    setFailure("");
    try {
      if (row.id) await workspaceApi.patch(`${kind}/${row.id}/`, payload);
      else await workspaceApi.post(`${kind}/`, payload);
      saved();
    } catch (error) {
      setFailure(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  return <Modal title={`${row.id ? "Edit" : "Add"} ${accounts ? "moderator" : "category"}`} close={() => !busy && close()}>
    <form onSubmit={save}><fieldset disabled={busy} className={styles.editor}>
      {accounts ? <>
        <label>Username<input name="username" maxLength={150} required defaultValue={row.username} autoComplete="off" /></label>
        <label>Email<input name="email" type="email" maxLength={254} defaultValue={row.email} /></label>
        <label>First name<input name="first_name" maxLength={150} defaultValue={row.first_name} /></label>
        <label>Last name<input name="last_name" maxLength={150} defaultValue={row.last_name} /></label>
        <label>{row.id ? "New password (optional)" : "Password"}
          <input name="password" type="password" minLength={8} maxLength={1024} required={!row.id} autoComplete="new-password" />
        </label>
        <label className={styles.check}><input name="is_active" type="checkbox" defaultChecked={row.is_active ?? true} /> Active account</label>
      </> : <label className={styles.wide}>Name<input name="name" maxLength={100} required defaultValue={row.name} /></label>}
      {failure && <p className={`${styles.error} ${styles.wide}`} role="alert">{failure}</p>}
      <div className={`${styles.actions} ${styles.wide}`}><button type="button" onClick={close}>Cancel</button><button className={styles.primary}>{busy ? "Saving…" : "Save"}</button></div>
    </fieldset></form>
  </Modal>;
}

export function Manage({ kind, notify }) {
  const accounts = kind === "accounts";
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [failure, setFailure] = useState("");
  const result = useWorkspaceData(accounts ? `accounts/?page=${page}` : "categories/");

  async function remove(row) {
    if (!window.confirm(`Delete category “${row.name}”?`)) return;
    setDeleting(true);
    setFailure("");
    try {
      await workspaceApi.remove(`categories/${row.id}/`);
      notify("Category deleted.");
      result.reload();
    } catch (error) {
      setFailure(errorMessage(error));
    } finally {
      setDeleting(false);
    }
  }

  return <>
    <Heading title={accounts ? "Moderator accounts" : "Categories"}>
      <button className={styles.primary} onClick={() => setSelected({})}>{accounts ? "Add moderator" : "Add category"}</button>
    </Heading>
    <section className={styles.panel}>
      {failure && <p className={styles.error} role="alert">{failure}</p>}
      <LoadState result={result}>{(data) => {
        const rows = accounts ? data.results : data;
        if (!rows.length) return <p className={styles.state}>{accounts ? "No moderator accounts yet." : "No categories yet."}</p>;
        return <>
          <div className={styles.tableWrap}><table>
            <thead><tr><th>{accounts ? "Username" : "Name"}</th>{accounts && <><th>Profile</th><th>Status</th></>}<th>Actions</th></tr></thead>
            <tbody>{rows.map((row) => <tr key={row.id}>
              <td><strong>{accounts ? row.username : row.name}</strong></td>
              {accounts && <><td>{[row.first_name, row.last_name].filter(Boolean).join(" ") || "—"}{row.email && <small>{row.email}</small>}</td><td>{row.is_active ? "Active" : "Inactive"}</td></>}
              <td><div className={styles.actions}>
                <button onClick={() => setSelected(row)}>Edit</button>
                {!accounts && <button className={styles.danger} disabled={deleting} onClick={() => remove(row)}>Delete</button>}
              </div></td>
            </tr>)}</tbody>
          </table></div>
          {accounts && <Pager data={data} page={page} onPage={setPage} />}
        </>;
      }}</LoadState>
    </section>
    {selected && <ManageEditor row={selected} kind={kind} close={() => setSelected(null)} saved={() => {
      notify(`${accounts ? "Moderator account" : "Category"} saved.`);
      setSelected(null);
      result.reload();
    }} />}
  </>;
}
