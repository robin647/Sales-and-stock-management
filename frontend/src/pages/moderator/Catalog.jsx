import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { errorMessage } from "../../utils/apiError";
import { AssetSection } from "./Media";
import { Heading, LoadState, Modal, money, Pager, ProtectedPreview } from "./components";
import { useWorkspaceData, workspaceApi } from "./data";
import styles from "./workspace.module.css";

export function ProductTable({ products }) {
  if (!products.length) return <p className={styles.state}>No matching products.</p>;
  return <div className={styles.tableWrap}><table>
    <thead><tr><th>Product / SKU</th><th>Category</th><th>Color / Size</th><th>Price</th><th>Stock</th></tr></thead>
    <tbody>{products.map((product) => <tr key={product.id}>
      <td><Link className={styles.productLink} to={`/moderator/products/${product.id}`}>
        {product.primary_asset && <ProtectedPreview id={product.primary_asset} thumbnail />}
        <span><strong>{product.name}</strong><small>{product.code}{!product.is_active && " · Inactive"}</small></span>
      </Link></td>
      <td>{product.category_name}</td>
      <td>{[product.color, product.size].filter(Boolean).join(" / ") || "Standard"}</td>
      <td>{money(product.effective_price)}{product.discount_price !== null && <small>{product.discount_percent}% off</small>}</td>
      <td>{product.factory_quantity}</td>
    </tr>)}</tbody>
  </table></div>;
}

export function OfferFilters({ categories, params = new URLSearchParams() }) {
  return <>
    <label>Category<select name="category" defaultValue={params.get("category") || ""}>
      <option value="">All categories</option>
      {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
    </select></label>
    <label>Effective discount %<input name="discount" type="number" min="0" max="100" step="0.01" defaultValue={params.get("discount") || ""} /></label>
    <label>Offer<select name="offer" defaultValue={params.get("offer") || ""}>
      <option value="">All prices</option><option value="yes">On offer</option><option value="no">Regular price</option>
    </select></label>
  </>;
}

function ProductFilters({ params, setParams, categories, isAdmin }) {
  function apply(event) {
    event.preventDefault();
    const values = Array.from(new FormData(event.currentTarget)).filter(([, value]) => value.trim());
    setParams(values);
  }

  return <form className={styles.filters} onSubmit={apply}>
    <label>Search<input name="search" placeholder="Name or SKU" maxLength={150} defaultValue={params.get("search") || ""} /></label>
    <OfferFilters categories={categories} params={params} />
    <label>Color<input name="color" maxLength={60} defaultValue={params.get("color") || ""} /></label>
    <label>Size<input name="size" maxLength={30} defaultValue={params.get("size") || ""} /></label>
    <label>Stock<select name="stock" defaultValue={params.get("stock") || ""}>
      <option value="">All stock</option><option value="available">Available</option>
      <option value="low">Low (1–5)</option><option value="out">Out of stock</option>
    </select></label>
    {isAdmin && <label>Active status<select name="active" defaultValue={params.get("active") || ""}>
      <option value="">All statuses</option><option value="true">Active</option><option value="false">Inactive</option>
    </select></label>}
    <label>Sort by<select name="ordering" defaultValue={params.get("ordering") || "-created_at"}>
      <option value="-created_at">Newest</option><option value="created_at">Oldest</option>
      <option value="name">Name</option><option value="effective_price">Price, low to high</option>
      <option value="-effective_price">Price, high to low</option>
      <option value="selling_price">Regular price, low to high</option><option value="-selling_price">Regular price, high to low</option>
    </select></label>
    <div className={styles.actions}><button className={styles.primary}>Apply filters</button><button type="button" onClick={() => setParams({})}>Reset</button></div>
  </form>;
}

function ProductEditor({ product, copyFrom, categories, close, saved }) {
  const source = product || copyFrom;
  const [discount, setDiscount] = useState(source?.discount_percent ?? 0);
  const [offerOverride, setOfferOverride] = useState(source?.discount_price ?? "");
  const [failure, setFailure] = useState("");
  const [busy, setBusy] = useState(false);

  async function save(event) {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget));
    payload.is_active = payload.is_active === "on";
    payload.online_enabled = payload.online_enabled === "on";
    payload.manual_offer_price = payload.manual_offer_price || null;
    if (product && product.is_active && !payload.is_active && !window.confirm("Mark this product inactive?")) return;
    if (product && product.online_enabled && !payload.online_enabled && !window.confirm("Unpublish this product from the storefront?")) return;
    if (product && Number(payload.stock) === product.factory_quantity) delete payload.stock;
    setBusy(true);
    setFailure("");
    try {
      const { data } = product
        ? await workspaceApi.patch(`products/${product.id}/`, payload)
        : await workspaceApi.post("products/", payload);
      saved(data);
    } catch (error) {
      setFailure(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  return <Modal title={product ? "Edit product" : copyFrom ? "Add color or size variant" : "Add product"} close={close}>
    <form onSubmit={save}><fieldset className={styles.editor} disabled={busy}>
      <label>Name<input name="name" required maxLength={150} defaultValue={source?.name} /></label>
      <label>SKU<input name="code" maxLength={64} placeholder="Auto-generated if blank" defaultValue={product?.code} /></label>
      <label>Category<select name="category" required defaultValue={source?.category || ""}>
        <option value="">Choose a category</option>
        {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
      </select></label>
      <label>Color<input name="color" maxLength={60} defaultValue={product?.color} /></label>
      <label>Size<input name="size" maxLength={30} defaultValue={product?.size} /></label>
      <label>Stock quantity<input name="stock" type="number" min="0" max="2147483647" required defaultValue={product?.factory_quantity ?? 0} /></label>
      <label className={styles.wide}>Description<textarea name="description" rows={3} maxLength={10000} defaultValue={source?.description} /></label>
      <label>Regular price<input name="selling_price" type="number" min="0" max="99999999.99" step="0.01" required defaultValue={source?.selling_price} /></label>
      <label>Discount %<input name="discount" type="number" min="0" max="100" step="0.01" required value={discount} onChange={(event) => {
        setDiscount(event.target.value);
        setOfferOverride("");
      }} /></label>
      <label>Offer price override<input name="manual_offer_price" type="number" min="0" step="0.01" placeholder="Use calculated price"
        disabled={Number(discount) === 0} value={offerOverride} onChange={(event) => setOfferOverride(event.target.value)} /></label>
      <label className={styles.check}><input type="checkbox" name="is_active" defaultChecked={source?.is_active ?? true} /> Active product</label>
      <label className={styles.check}><input type="checkbox" name="online_enabled" defaultChecked={source?.online_enabled ?? false} /> Publish on storefront</label>
      {failure && <p className={`${styles.error} ${styles.wide}`} role="alert">{failure}</p>}
      <div className={`${styles.actions} ${styles.wide}`}><button type="button" onClick={close}>Cancel</button><button className={styles.primary}>{busy ? "Saving…" : "Save product"}</button></div>
    </fieldset></form>
  </Modal>;
}

export function Catalog({ isAdmin, notify }) {
  const [params, setParams] = useSearchParams();
  const [adding, setAdding] = useState(false);
  const navigate = useNavigate();
  const categoryResult = useWorkspaceData("categories/");
  const result = useWorkspaceData(`products/?${params}`);
  const filterKey = new URLSearchParams(params);
  filterKey.delete("page");
  const page = Number(params.get("page") || 1);
  return <>
    <Heading title="Products">{isAdmin && <button className={styles.primary} onClick={() => setAdding(true)}>Add product</button>}</Heading>
    <section className={styles.panel}>
      <LoadState result={categoryResult}>{(categories) => <>
        <ProductFilters key={filterKey.toString()} params={params} setParams={setParams} categories={categories} isAdmin={isAdmin} />
        {adding && <ProductEditor categories={categories} close={() => setAdding(false)} saved={(product) => {
          notify("Product created.");
          navigate(`/moderator/products/${product.id}`);
        }} />}
      </>}</LoadState>
      <LoadState result={result}>{(data) => <>
        <ProductTable products={data.results} />
        <Pager page={page} data={data} onPage={(value) => {
          const next = new URLSearchParams(params);
          next.set("page", value);
          setParams(next);
        }} />
      </>}</LoadState>
    </section>
  </>;
}

function ProductRecord({ id, isAdmin, notify }) {
  const result = useWorkspaceData(`products/${id}/`);
  const categories = useWorkspaceData(isAdmin ? "categories/" : null);
  const navigate = useNavigate();
  const [editor, setEditor] = useState("");
  return <>
    <Link to="/moderator/products">← Products</Link>
    <LoadState result={result}>{(product) => <>
      <Heading title={product.name}>
        {isAdmin && <div className={styles.actions}>
          <button onClick={() => setEditor("variant")}>Add variant</button>
          <button className={styles.primary} onClick={() => setEditor("product")}>Edit product</button>
        </div>}
      </Heading>
      <section className={styles.panel}>
        <dl className={styles.facts}>
          {[
            ["SKU", product.code], ["Category", product.category_name], ["Color", product.color || "—"],
            ["Size", product.size || "Standard"], ["Regular price", money(product.selling_price)],
            ["Current price", money(product.effective_price)], ["Stock", product.factory_quantity],
            ...(isAdmin ? [["Status", product.is_active ? "Active" : "Inactive"], ["Storefront", product.online_enabled ? "Published" : "Draft"]] : []),
          ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
        </dl>
        {product.description && <p className={styles.description}>{product.description}</p>}
        {!!product.variants.length && <div className={styles.variants}><h3>Other variants</h3>
          {product.variants.map((variant) => <Link key={variant.id} to={`/moderator/products/${variant.id}`}>
            {[variant.color, variant.size].filter(Boolean).join(" / ") || "Standard"} · {variant.code} · {variant.factory_quantity} units
            {!variant.is_active && " · Inactive"}
          </Link>)}
        </div>}
      </section>
      <AssetSection product={product} isAdmin={isAdmin} notify={notify} reload={result.reload} />
      {editor && <LoadState result={categories}>{(rows) => (
        <ProductEditor product={editor === "product" ? product : null} copyFrom={editor === "variant" ? product : null}
          categories={rows} close={() => setEditor("")} saved={(saved) => {
            setEditor("");
            notify(editor === "variant" ? "Variant created." : "Product updated.");
            if (saved.id !== product.id) navigate(`/moderator/products/${saved.id}`);
            else result.reload();
          }} />
      )}</LoadState>}
    </>}</LoadState>
  </>;
}

export function ProductDetail(props) {
  const { id } = useParams();
  return <ProductRecord key={id} id={id} {...props} />;
}
