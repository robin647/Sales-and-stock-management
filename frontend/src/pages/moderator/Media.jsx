import { useEffect, useState } from "react";
import { errorMessage } from "../../utils/apiError";
import { Modal, ProtectedPreview } from "./components";
import { download, workspaceApi } from "./data";
import styles from "./workspace.module.css";

const types = { edited: "Edited images", raw: "Raw images", video: "Videos" };
const acceptImages = "image/jpeg,image/png,image/webp,image/gif,image/bmp";
const acceptVideos = ".mp4,.webm,.mov";

function LocalPreview({ file, video }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);
  if (!url) return null;
  return video ? <video className={styles.preview} src={url} controls playsInline />
    : <img className={styles.preview} src={url} alt={file.name} />;
}

function UploadForm({ product, replacement, close, refreshed, notify }) {
  const [kind, setKind] = useState(replacement?.kind ?? "edited");
  const [files, setFiles] = useState([]);
  const [failure, setFailure] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const video = kind === "video";

  function pick(event) {
    const selection = Array.from(event.target.files);
    const limit = video ? 200 : 20;
    if (selection.some((file) => file.size === 0 || file.size > limit * 1024 * 1024)) {
      setFailure(`Choose files up to ${limit} MB each.`);
      setFiles([]);
    } else {
      setFailure("");
      setFiles(selection);
    }
  }

  async function upload(event) {
    event.preventDefault();
    if (!files.length || busy) return;
    setBusy(true);
    setFailure("");
    let complete = 0;
    try {
      for (const file of files) {
        setProgress(`Uploading ${complete + 1} of ${files.length}…`);
        const form = new FormData();
        form.set("file", file);
        if (replacement) {
          await workspaceApi.post(`assets/${replacement.id}/replace/`, form);
        } else {
          form.set("product", product.id);
          form.set("kind", kind);
          await workspaceApi.post("assets/", form);
        }
        complete++;
      }
      notify(replacement ? "Asset replaced." : `${complete} ${complete === 1 ? "file" : "files"} uploaded.`);
      close();
      refreshed();
    } catch (error) {
      const prefix = complete ? `${complete} uploaded. ` : "";
      setFailure(prefix + errorMessage(error));
      setFiles(files.slice(complete));
    } finally {
      setBusy(false);
      setProgress("");
    }
  }

  return <Modal title={replacement ? "Replace asset" : "Upload assets"} close={() => {
    if (!busy) {
      close();
      refreshed();
    }
  }}>
    <form className={styles.stack} onSubmit={upload}>
      {!replacement && <label>Asset type<select disabled={busy} value={kind} onChange={(event) => {
        setKind(event.target.value);
        setFiles([]);
        setFailure("");
      }}>{Object.entries(types).map(([value, text]) => <option value={value} key={value}>{text}</option>)}</select></label>}
      <label>{replacement ? "Replacement file" : "Files to upload"}
        <input key={kind} type="file" multiple={!replacement} disabled={busy} accept={video ? acceptVideos : acceptImages} onChange={pick} />
      </label>
      <small>{video ? "MP4, WEBM or MOV · up to 200 MB per file" : "Up to 20 MB per image"}</small>
      {!!files.length && <div className={styles.mediaGrid}>{files.map((file, index) => (
        <div key={`${file.name}-${index}`}><LocalPreview file={file} video={video} /><small>{file.name}</small></div>
      ))}</div>}
      {failure && <p role="alert" className={styles.error}>{failure}</p>}
      <div className={styles.actions}>
        <button type="button" disabled={busy} onClick={() => { close(); refreshed(); }}>Close</button>
        <button className={styles.primary} disabled={busy || !files.length}>{progress || (replacement ? "Replace" : "Upload")}</button>
      </div>
    </form>
  </Modal>;
}

export function AssetSection({ product, isAdmin, reload, notify }) {
  const [uploading, setUploading] = useState(false);
  const [replacement, setReplacement] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");

  async function run(operation, success, refresh = false) {
    setBusy(true);
    setFailure("");
    try {
      await operation();
      if (success) notify(success);
      if (refresh) reload();
    } catch (error) {
      setFailure(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  return <section className={styles.panel}>
    <div className={styles.heading}><h2>Private assets</h2>{isAdmin && <button className={styles.primary} onClick={() => setUploading(true)}>Upload assets</button>}</div>
    {failure && <p role="alert" className={styles.error}>{failure}</p>}
    <div className={styles.actions}>{["edited", "raw"].map((kind) => (
      <button key={kind} disabled={busy || !product.assets.some((asset) => asset.kind === kind)}
        onClick={() => run(() => download(`products/${product.id}/archive/?kind=${kind}`, `product-${product.id}-${kind}.zip`))}>
        Download {kind} ZIP
      </button>
    ))}</div>
    {!product.assets.length && <p className={styles.state}>No assets uploaded for this product.</p>}
    {Object.entries(types).map(([kind, label]) => {
      const assets = product.assets.filter((asset) => asset.kind === kind);
      if (!assets.length) return null;
      return <div key={kind} className={styles.assetGroup}>
        <h3>{label}</h3>
        <ul>{assets.map((asset) => <li key={asset.id}>
          <div><strong>{asset.original_name}</strong><small>{asset.primary ? "Primary thumbnail" : `${(asset.size_bytes / (1024 * 1024)).toFixed(2)} MB`}</small></div>
          <div className={styles.actions}>
            <button onClick={() => setPreview(asset)}>Preview</button>
            <button disabled={busy} onClick={() => run(() => download(`assets/${asset.id}/download/`, asset.original_name))}>Download</button>
            {isAdmin && <>
              {asset.kind === "edited" && !asset.primary && <button disabled={busy}
                onClick={() => run(() => workspaceApi.post(`assets/${asset.id}/primary/`), "Primary thumbnail updated.", true)}>Make primary</button>}
              <button disabled={busy} onClick={() => setReplacement(asset)}>Replace</button>
              <button className={styles.danger} disabled={busy} onClick={() => {
                if (window.confirm(`Delete ${asset.original_name} permanently?`)) {
                  run(() => workspaceApi.remove(`assets/${asset.id}/`), "Asset deleted.", true);
                }
              }}>Delete</button>
            </>}
          </div>
        </li>)}</ul>
      </div>;
    })}
    {preview && <Modal title={preview.original_name} close={() => setPreview(null)}>
      <ProtectedPreview id={preview.id} version={preview.updated_at} video={preview.kind === "video"} />
    </Modal>}
    {(uploading || replacement) && <UploadForm
      product={product} replacement={replacement} close={() => { setUploading(false); setReplacement(null); }}
      refreshed={reload} notify={notify}
    />}
  </section>;
}
