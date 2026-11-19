import { useEffect, useRef, useState } from "react";
import { workspaceApi } from "./data";
import styles from "./workspace.module.css";

export const money = (value) => new Intl.NumberFormat("en-BD", {
  style: "currency", currency: "BDT", maximumFractionDigits: 2,
}).format(Number(value));

export function Heading({ title, children }) {
  return <div className={styles.heading}><h1>{title}</h1>{children}</div>;
}

export function LoadState({ result, children }) {
  if (result.error) return <div className={styles.state} role="alert">{result.error} <button onClick={result.reload}>Retry</button></div>;
  if (result.data === undefined) return <p className={styles.state} role="status">Loading…</p>;
  return children(result.data);
}

export function Pager({ page, data, onPage }) {
  if (!data.count) return null;
  return <div className={styles.pager}>
    <span>{data.count} results · Page {page}</span>
    <button disabled={!data.previous} onClick={() => onPage(page - 1)}>Previous</button>
    <button disabled={!data.next} onClick={() => onPage(page + 1)}>Next</button>
  </div>;
}

export function Modal({ title, close, children }) {
  const ref = useRef(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog.showModal();
    return () => dialog.close();
  }, []);
  return <dialog ref={ref} className={styles.dialog} aria-label={title} onCancel={(event) => { event.preventDefault(); close(); }}>
    <div className={styles.heading}><h2>{title}</h2><button type="button" onClick={close} aria-label="Close">×</button></div>
    {children}
  </dialog>;
}

export function ProtectedPreview({ id, version, video = false, thumbnail = false }) {
  const [result, setResult] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl;
    const mode = thumbnail ? "thumbnail=1" : "inline=1";
    workspaceApi.get(`assets/${id}/download/?${mode}`, { responseType: "blob", signal: controller.signal })
      .then(({ data }) => {
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(data);
        setResult({ id, version, url: objectUrl });
      }).catch(() => {
        if (!controller.signal.aborted) setResult({ id, version, error: true });
      });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [id, version, thumbnail]);
  const current = result?.id === id && result.version === version ? result : null;
  if (current?.error) return <span role="alert">Preview unavailable</span>;
  if (!current?.url) return <span role="status">{thumbnail ? "…" : "Loading preview…"}</span>;
  const unavailable = () => setResult({ id, version, error: true });
  return video ? <video className={styles.preview} src={current.url} controls playsInline onError={unavailable} />
    : <img className={thumbnail ? styles.thumbnail : styles.preview} alt="Product asset" src={current.url} onError={unavailable} />;
}
