import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { categoryApi, fetchAllPages, productApi } from "../../api/endpoints";
import { errorMessage } from "../../utils/apiError";
import "./commerce.css";

const blank = { name: "", code: "", category: "", size: "", selling_price: "", discount_price: "", description: "", image_url: "", initial_stock: "0", is_active: true, is_featured: false, online_enabled: true };
const money = (value) => "৳" + Number(value || 0).toLocaleString("en-BD", { maximumFractionDigits: 2 });

export default function Products() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [tab, setTab] = useState("products");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [form, setForm] = useState(blank);
  const [editing, setEditing] = useState(null);
  const [editor, setEditor] = useState(false);
  const [saving, setSaving] = useState(false);
  const [discountMode, setDiscountMode] = useState("price");
  const [percent, setPercent] = useState("");
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState("");
  const [removeImage, setRemoveImage] = useState(false);
  const [categoryName, setCategoryName] = useState("");
  const [categoryId, setCategoryId] = useState(null);
  const [stocks, setStocks] = useState([]);
  const [showStocks, setShowStocks] = useState(false);
  const nameInput = useRef(null);

  async function load() {
    setLoading(true); setError("");
    try {
      const [rows, cats] = await Promise.all([productApi.listAll(), categoryApi.listAll()]);
      setProducts(rows); setCategories(cats);
    } catch (err) { setError(errorMessage(err)); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!image) return;
    const url = URL.createObjectURL(image); setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [image]);
  useEffect(() => { if (editor) nameInput.current?.focus(); }, [editor]);
  const rows = useMemo(() => products.filter((p) => (!filter || String(p.category) === filter) && (!status || (status === "active" ? p.is_active : !p.is_active)) && (p.name + " " + p.code + " " + p.size).toLowerCase().includes(query.toLowerCase())), [products, filter, status, query]);
  const regular = Number(form.selling_price || 0);
  const offer = discountMode === "percent" && Number(percent) > 0 ? Math.round(regular * (1 - Number(percent) / 100) * 100) / 100 : discountMode === "price" && form.discount_price !== "" ? Number(form.discount_price) : regular;
  function openEditor(product = null) {
    setEditing(product?.id || null); setForm(product ? { ...blank, ...product, discount_price: product.discount_price ?? "" } : { ...blank, category: categories[0]?.id || "" });
    setImage(null); setPreview(product?.image || ""); setRemoveImage(false); setDiscountMode("price"); setPercent(""); setError(""); setEditor(true);
  }
  async function saveProduct(event) {
    event.preventDefault(); setError("");
    if (offer <= 0 && (form.discount_price !== "" || Number(percent) > 0)) { setError("Offer price must be greater than zero."); return; }
    setSaving(true);
    try {
      const data = new FormData();
      Object.entries(form).forEach(([key, value]) => {
        if (![...Object.keys(blank)].includes(key) || key === "discount_price" || (editing && key === "initial_stock")) return;
        data.append(key, value);
      });
      if (discountMode === "percent") data.append("discount_percentage", percent || "0");
      else data.append("discount_price", form.discount_price);
      if (image) data.append("image", image);
      if (removeImage) data.append("remove_image", "true");
      if (editing) await productApi.update(editing, data); else await productApi.create(data);
      setEditor(false); setNotice(editing ? "Product updated." : "Product added to your catalog."); await load();
    } catch (err) { setError(errorMessage(err)); }
    finally { setSaving(false); }
  }
  async function toggle(product) {
    setError("");
    try { await productApi.update(product.id, { is_active: !product.is_active }); await load(); }
    catch (err) { setError(errorMessage(err)); }
  }
  async function saveCategory(event) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      if (categoryId) await categoryApi.update(categoryId, { name: categoryName.trim() }); else await categoryApi.create({ name: categoryName.trim() });
      setCategoryName(""); setCategoryId(null); setNotice("Category saved."); await load();
    } catch (err) { setError(errorMessage(err)); }
    finally { setSaving(false); }
  }
  async function deleteCategory(category) {
    if (!window.confirm('Delete empty category "' + category.name + '"?')) return;
    setSaving(true); setError("");
    try { await categoryApi.delete(category.id); setNotice("Category deleted."); await load(); }
    catch (err) { setError(errorMessage(err)); }
    finally { setSaving(false); }
  }
  async function stockOverview() {
    setError("");
    try { setStocks(await fetchAllPages("/inventory/showroom-stocks/")); setShowStocks(!showStocks); }
    catch (err) { setError(errorMessage(err)); }
  }
  return <div className="commerce">
    <div className="commerce-heading"><div><span className="commerce-kicker">YOUR ONLINE STORE</span><h1>Products & categories</h1><p>Manage your collection, prices and the pieces customers discover.</p></div><div className="commerce-actions"><button className="c-button secondary" onClick={() => setTab("categories")}>+ Category</button><Link className="c-button secondary" to="/shop">View store ↗</Link><button className="c-button" onClick={() => openEditor()}>+ Add product</button></div></div>
    <div className="commerce-stats">{[["Total products", products.length], ["Active products", products.filter(p => p.is_active).length], ["On offer", products.filter(p => p.discount_price !== null).length], ["Categories", categories.length]].map(([title, value]) => <div className="c-stat" key={title}><span>{title}</span><strong>{value}</strong></div>)}</div>
    {error && <div className="c-alert error" role="alert">{error}</div>}{notice && <div className="c-alert" role="status">{notice}<button onClick={() => setNotice("")} aria-label="Dismiss notification">×</button></div>}
    <div className="commerce-tabs"><button className={tab === "products" ? "selected" : ""} onClick={() => setTab("products")}>All products</button><button className={tab === "categories" ? "selected" : ""} onClick={() => setTab("categories")}>Categories</button><Link to="/online-orders">Online orders →</Link></div>
    {tab === "products" ? <section className="c-panel"><div className="c-toolbar"><input aria-label="Search products" placeholder="Search name, code or size…" value={query} onChange={e => setQuery(e.target.value)} /><select aria-label="Filter category" value={filter} onChange={e => setFilter(e.target.value)}><option value="">All categories</option>{categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select><select aria-label="Filter status" value={status} onChange={e => setStatus(e.target.value)}><option value="">All statuses</option><option value="active">Active</option><option value="inactive">Inactive</option></select><button className="c-button secondary" onClick={stockOverview}>Showroom stock</button></div>
      <div className="c-table-wrap"><table className="c-table"><thead><tr><th>Product</th><th>Category / size</th><th>Price</th><th>Factory stock</th><th>Visibility</th><th>Actions</th></tr></thead><tbody>{rows.map(p => <tr key={p.id}><td><div className="c-product-cell">{p.image ? <img src={p.image} alt="" /> : <span className="c-image-placeholder">M</span>}<div><strong>{p.name}</strong><small>{p.code || "No product code"}{p.is_featured ? " · Featured" : ""}</small></div></div></td><td>{p.category_name}<small>{p.size || "Standard"}</small></td><td><strong>{money(p.discount_price ?? p.selling_price)}</strong>{p.discount_price !== null && <small><del>{money(p.selling_price)}</del> <span className="c-discount">−{p.discount_percent}%</span></small>}</td><td><span className={p.factory_quantity > 0 ? "c-badge" : "c-badge muted"}>{p.factory_quantity || 0} pcs</span></td><td><span className={p.is_active ? "c-badge" : "c-badge muted"}>{p.is_active ? "Active" : "Archived"}</span><small>{p.online_enabled ? "Online store enabled" : "Showroom only"}</small></td><td><div className="commerce-actions"><button className="c-text-button" onClick={() => openEditor(p)}>Edit</button><button className="c-text-button" onClick={() => toggle(p)}>{p.is_active ? "Archive" : "Activate"}</button></div></td></tr>)}</tbody></table></div>
      {loading && <p className="c-empty">Loading your catalog…</p>}{!loading && !rows.length && <div className="c-empty"><h3>{products.length ? "No matching products" : "Your collection starts here"}</h3><p>{products.length ? "Try a different search or filter." : "Create a category, then add your first product."}</p><button className="c-button" onClick={() => openEditor()}>+ Add product</button></div>}
      {showStocks && <div className="c-stock-overview"><h3>Existing showroom inventory</h3>{stocks.length ? stocks.map(s => <p key={s.id}>{s.product_name || products.find(p => p.id === s.product)?.name} · {s.showroom_name || s.showroom}: <strong>{s.quantity} pcs</strong></p>) : <p>No showroom stock found.</p>}<Link to="/stock-adjustments">Adjust inventory →</Link></div>}
    </section> : <div className="c-category-layout"><form className="c-panel c-form" onSubmit={saveCategory}><h2>{categoryId ? "Edit category" : "Create a category"}</h2><p>Organise your products so customers can find their favourites.</p><label>Category name<input maxLength={100} required placeholder="e.g. Sherwani" value={categoryName} onChange={e => setCategoryName(e.target.value)} /></label><button className="c-button" disabled={saving}>{saving ? "Saving…" : "Save category"}</button>{categoryId && <button type="button" className="c-text-button" onClick={() => { setCategoryId(null); setCategoryName(""); }}>Cancel edit</button>}</form><div className="c-category-grid">{categories.map(c => <div className="c-panel c-category" key={c.id}><span className="c-category-icon">{c.name[0]}</span><h3>{c.name}</h3><p>{products.filter(p => p.category === c.id).length} products</p><button className="c-text-button" onClick={() => { setCategoryId(c.id); setCategoryName(c.name); }}>Rename category →</button>{!products.some(p => p.category === c.id) && <button className="c-text-button" disabled={saving} onClick={() => deleteCategory(c)}>Delete empty category</button>}</div>)}</div></div>}
    {editor && <div className="c-modal-backdrop"><section className="c-modal" role="dialog" aria-modal="true" aria-labelledby="product-editor-title" onKeyDown={e => { if (e.key === "Escape" && !saving) setEditor(false); }}><div className="c-modal-heading"><div><span className="commerce-kicker">CATALOG STUDIO</span><h2 id="product-editor-title">{editing ? "Edit product" : "Add a new product"}</h2></div><button disabled={saving} aria-label="Close product editor" onClick={() => setEditor(false)}>×</button></div><form className="c-form" onSubmit={saveProduct}>
      {error && <div className="c-alert error" role="alert">{error}</div>}<div className="c-editor-grid"><div><h3>Product details</h3><label>Product name<input ref={nameInput} required maxLength={150} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></label><div className="c-form-grid"><label>Product code<input maxLength={64} value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} /></label><label>Size<input maxLength={30} placeholder="M, L, XL…" value={form.size} onChange={e => setForm({ ...form, size: e.target.value })} /></label></div><label>Category<select required value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}><option value="">Select category</option>{categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>{!categories.length && <p>Create a category in the Categories tab first.</p>}<label>Description<textarea rows={4} maxLength={10000} placeholder="Fabric, fit, details and care instructions…" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></label><h3>Pricing</h3><div className="c-form-grid"><label>Regular sale price (৳)<input required type="number" min="0" step="0.01" value={form.selling_price} onChange={e => setForm({ ...form, selling_price: e.target.value })} /></label><label>Discount type<select value={discountMode} onChange={e => setDiscountMode(e.target.value)}><option value="price">Set offer price</option><option value="percent">Percentage off</option></select></label></div>{discountMode === "price" ? <label>Discount price (৳) · optional<input type="number" min="0.01" step="0.01" value={form.discount_price} onChange={e => setForm({ ...form, discount_price: e.target.value })} placeholder="Leave empty for regular price" /></label> : <label>Discount (%)<input type="number" min="0" max="99.99" step="0.01" value={percent} onChange={e => setPercent(e.target.value)} /></label>}<div className="c-price-preview"><span>Customer pays</span><strong>{money(offer)}</strong><small>Saving {money(Math.max(0, regular - offer))}</small></div></div><div><h3>Product image</h3><div className="c-image-preview">{preview ? <img src={preview} alt="Product preview" /> : <span>Your product photo</span>}</div><label>Upload photo<input type="file" accept="image/jpeg,image/png,image/webp" onChange={e => { setImage(e.target.files?.[0] || null); setRemoveImage(false); }} /></label><p className="c-help">JPG, PNG or WebP, up to 3 MB. Optimised images are saved with your catalog.</p><label>Or use an image URL<input type="url" placeholder="https://…" value={form.image_url} onChange={e => { setRemoveImage(false); setForm({ ...form, image_url: e.target.value }); if (!image) setPreview(e.target.value); }} /></label>{preview && <button type="button" className="c-text-button" onClick={() => { setPreview(""); setImage(null); setRemoveImage(true); setForm({ ...form, image_url: "" }); }}>Remove current image</button>}<h3>Stock & visibility</h3>{!editing ? <label>Initial factory stock<input type="number" min="0" step="1" required value={form.initial_stock} onChange={e => setForm({ ...form, initial_stock: e.target.value })} /></label> : <p className="c-help">Use Product Stock Adjustment for audited inventory changes.</p>}{[["is_active", "Active product"], ["online_enabled", "Show in online collection"], ["is_featured", "Feature this product"]].map(([key, label]) => <label className="c-checkbox" key={key}><input type="checkbox" checked={form[key]} onChange={e => setForm({ ...form, [key]: e.target.checked })} />{label}</label>)}</div></div><div className="c-modal-footer"><button type="button" className="c-button secondary" disabled={saving} onClick={() => setEditor(false)}>Cancel</button><button className="c-button" disabled={saving}>{saving ? "Saving product…" : editing ? "Save changes" : "Create product"}</button></div></form></section></div>}
  </div>;
}
