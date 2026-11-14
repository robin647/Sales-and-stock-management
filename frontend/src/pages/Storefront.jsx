import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { productApi, shopApi } from "../api/endpoints";
import { useAuth } from "../context/AuthContext.jsx";
import { useTheme } from "../context/ThemeContext.jsx";
import "./storefront.css";
import "./admin/commerce.css";

const HERO_IMAGE = "https://images.pexels.com/photos/19168798/pexels-photo-19168798/free-photo-of-groom-in-traditional-clothes.jpeg?auto=compress&w=1400";
const PRODUCT_IMAGES = [
  "https://images.pexels.com/photos/39210712/pexels-photo-39210712/free-photo-of-elegant-traditional-indian-sherwani-on-display.jpeg?auto=compress&w=800",
  "https://images.pexels.com/photos/21926986/pexels-photo-21926986/free-photo-of-close-up-of-an-embroidered-sherwani-hanging-on-a-branch.jpeg?auto=compress&w=800",
  "https://images.pexels.com/photos/18016521/pexels-photo-18016521/free-photo-of-traditional-clothing-on-hanger.jpeg?auto=compress&w=800",
  "https://images.pexels.com/photos/2060241/pexels-photo-2060241.jpeg?auto=compress&w=800",
];

const money = (value) => `৳${Number(value || 0).toLocaleString("en-BD", { maximumFractionDigits: 2 })}`;

function productPrice(product) {
  const regular = Number(product.selling_price || 0);
  const offer = Number(product.discount_price || 0);
  return { regular, current: offer > 0 && offer < regular ? offer : regular };
}

function readSavedCart() {
  try {
    const saved = JSON.parse(localStorage.getItem("mahir-shopping-bag") || "{}");
    return Object.fromEntries(Object.entries(saved || {}).filter(([id, quantity]) => /^\d+$/.test(id) && Number.isInteger(quantity) && quantity > 0));
  } catch {
    return {};
  }
}

export default function Storefront() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [catalogAttempt, setCatalogAttempt] = useState(0);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All styles");
  const [cart, setCart] = useState(readSavedCart);
  const [cartOpen, setCartOpen] = useState(false);
  const [orderRequiresCustomer, setOrderRequiresCustomer] = useState(false);
  const [sort, setSort] = useState("featured");
  const [detail, setDetail] = useState(null);
  const [shopSettings, setShopSettings] = useState(null);
  const [favorites, setFavorites] = useState(() => { try { const saved = JSON.parse(localStorage.getItem("mahir-favorites") || "[]"); return Array.isArray(saved) ? saved : []; } catch { return []; } });
  const [favoritesOnly, setFavoritesOnly] = useState(false);

  useEffect(() => { shopApi.settings().then(res => setShopSettings(res.data)).catch(() => {}); }, []);
  useEffect(() => { localStorage.setItem("mahir-favorites", JSON.stringify(favorites)); }, [favorites]);
  useEffect(() => {
    const close = event => { if (event.key === "Escape") { setDetail(null); setCartOpen(false); } };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, []);
  function toggleFavorite(id) { setFavorites(current => current.includes(id) ? current.filter(value => value !== id) : [...current, id]); }

  useEffect(() => {
    localStorage.setItem("mahir-shopping-bag", JSON.stringify(cart));
  }, [cart]);

  useEffect(() => {
    if (sessionStorage.getItem("mahir-resume-order") === "1") {
      sessionStorage.removeItem("mahir-resume-order");
      setCartOpen(true);
    }
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError("");
    productApi.listAll({ is_active: true, storefront: true })
      .then((rows) => { if (active) setProducts(rows); })
      .catch((error) => {
        if (!active) return;
        setLoadError(error.response?.status >= 500
          ? "The product service is temporarily unavailable. Please try again shortly."
          : "We could not load the collection. Check your connection and try again.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [catalogAttempt]);

  const categories = useMemo(() => ["All styles", ...new Set(products.map((item) => item.category_name).filter(Boolean))], [products]);
  const filtered = useMemo(() => products.filter((item) => {
    const matchesCategory = category === "All styles" || item.category_name === category;
    const matchesSearch = `${item.name} ${item.code} ${item.category_name} ${item.size}`.toLowerCase().includes(query.toLowerCase());
    return matchesCategory && matchesSearch && (!favoritesOnly || favorites.includes(item.id));
  }).sort((a, b) => sort === "price-low" ? productPrice(a).current - productPrice(b).current : sort === "price-high" ? productPrice(b).current - productPrice(a).current : sort === "newest" ? new Date(b.created_at) - new Date(a.created_at) : Number(b.is_featured) - Number(a.is_featured)), [category, products, query, sort, favoritesOnly, favorites]);
  const cartItems = products.filter((product) => cart[product.id]);
  const cartCount = Object.values(cart).reduce((sum, quantity) => sum + quantity, 0);
  const cartTotal = cartItems.reduce((sum, product) => sum + productPrice(product).current * cart[product.id], 0);
  const cartSavings = cartItems.reduce((sum, product) => sum + (productPrice(product).regular - productPrice(product).current) * cart[product.id], 0);

  function addToCart(product) {
    if (product.factory_quantity <= 0) return;
    setCart((current) => ({ ...current, [product.id]: Math.min((current[product.id] || 0) + 1, product.factory_quantity ?? 1000) }));
  }

  function changeQuantity(productId, delta) {
    setCart((current) => {
      const product = products.find(item => item.id === productId);
      const nextQuantity = Math.min((current[productId] || 0) + delta, product?.factory_quantity ?? 1000);
      const next = { ...current };
      if (nextQuantity <= 0) delete next[productId];
      else next[productId] = nextQuantity;
      return next;
    });
  }

  function orderOnWhatsApp() {
    if (user?.role !== "customer") {
      setOrderRequiresCustomer(true);
      return;
    }
    const lines = cartItems.map((product) => `${product.name}${product.size ? ` (${product.size})` : ""} x${cart[product.id]} - ${money(productPrice(product).current * cart[product.id])}`);
    const message = `Assalamu alaikum, I would like to order:\n${lines.join("\n")}\nTotal: ${money(cartTotal)}`;
    window.open(`https://wa.me/${shopSettings?.whatsapp_number || "8801781879276"}?text=${encodeURIComponent(message)}`, "_blank", "noopener,noreferrer");
  }

  function continueToCustomerAuth(path) {
    sessionStorage.setItem("mahir-resume-order", "1");
    navigate(path, { state: { returnToOrder: true } });
  }

  return (
    <div className="storefront">
      <div className="store-promo"><span>Cash on Delivery · Delivery charge paid in advance</span><a href="#collection">Shop the collection <span aria-hidden="true">↗</span></a></div>
      <header className="store-header">
        <Link className="store-brand" to="/" aria-label="Mahir Sherwani home"><span className="brand-mark">M</span><span>MAHIR <i>SHERWANI</i></span></Link>
        <nav className="store-nav" aria-label="Main navigation"><a href="#collection" onClick={() => { setCategory("All styles"); setQuery(""); }}>Collection</a><a href="#edits">Occasion edits</a><a href="#story">Our story</a><a href="#offers">Discover</a></nav>
        <div className="store-actions">
          <label className="store-search"><span aria-hidden="true">⌕</span><input aria-label="Search products" placeholder="Search styles" value={query} onChange={(event) => { setQuery(event.target.value); document.getElementById("collection")?.scrollIntoView({ behavior: "smooth" }); }} /></label>
          <button className="store-icon-button theme-toggle" type="button" title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`} onClick={toggleTheme}>{theme === "dark" ? "☼" : "◐"}</button>
          {user ? <button className="store-account" type="button" onClick={() => { logout(); window.location.reload(); }}>Sign out</button> : <Link className="store-account" to="/login">Login</Link>}
          {user?.role === "customer" ? <Link className="store-signup" to="/my-orders">My orders</Link> : user?.role === "admin" ? <Link className="store-signup" to="/">Admin panel</Link> : <Link className="store-signup" to="/signup">Sign up</Link>}
          <button className="store-icon-button cart-trigger" type="button" aria-label={`Open bag, ${cartCount} items`} onClick={() => setCartOpen(true)}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 8h14l1 13H4L5 8Z" /><path d="M9 8V6a3 3 0 0 1 6 0v2" /></svg><b>{cartCount}</b></button>
        </div>
      </header>

      <main>
        <section className="store-hero">
          <div className="hero-copy"><span className="eyebrow">THE ART OF CELEBRATION</span><h1>A little tradition.<br />A lasting<br /><em>impression.</em></h1><p>From your everyday favourites to your once-in-a-lifetime moments. Discover a wardrobe with a story to tell.</p><div className="hero-links"><a className="primary-link" href="#collection">Explore the collection <span aria-hidden="true">→</span></a><a className="hero-secondary" href="#edits">Find your occasion ↗</a></div><div className="hero-note"><span>ROOTED IN TRADITION</span><span>Made for your next chapter</span></div></div>
          <div className="hero-photo" style={{ backgroundImage: `url("${HERO_IMAGE}")` }}><div className="hero-photo-caption"><span>THE FESTIVE EDIT</span><strong>Wear the occasion.</strong></div><div className="hero-vertical">MAHIR SHERWANI · EST. 2018</div></div>
        </section>

        <section className="store-benefits" aria-label="Shopping benefits"><div><span>✳</span><p><strong>Made with care</strong><small>Finishing you can feel</small></p></div><div><span>↗</span><p><strong>Easy ordering</strong><small>Talk to us on WhatsApp</small></p></div><div><span>◇</span><p><strong>Secure delivery</strong><small>Across Bangladesh</small></p></div></section>
        <section id="edits" className="occasion-section">
          <div className="collection-heading"><div><span className="eyebrow">EVERY OCCASION, YOUR EXPRESSION</span><h2>Dress for the moment.</h2></div><a className="text-link" href="#collection">View collection ↗</a></div>
          <div className="occasion-grid">
            {[{ title: "The wedding edit", subtitle: "For the beginning of forever", image: HERO_IMAGE, search: "sherwani" }, { title: "Everyday elegance", subtitle: "Tradition in your own rhythm", image: PRODUCT_IMAGES[2], search: "panjabi" }, { title: "A reason to celebrate", subtitle: "Find your next favourite", image: PRODUCT_IMAGES[1], search: "" }].map((edit, index) => <a key={edit.title} href="#collection" className="occasion-card" onClick={() => { setCategory("All styles"); setQuery(edit.search); }}><img src={edit.image} alt={edit.title} loading="lazy" /><div className="occasion-copy"><span>0{index + 1} / THE MAHIR EDIT</span><h3>{edit.title}</h3><p>{edit.subtitle}</p></div><span className="occasion-arrow" aria-hidden="true">↗</span></a>)}
          </div>
        </section>
        <section id="offers" className="offer-band"><div><span className="eyebrow">THE OCCASION EDIT</span><h2>Make every entrance count.</h2><p>Discover handpicked looks for celebrations, gatherings and everything in between.</p></div><a href="#collection">Find your look <span aria-hidden="true">↗</span></a><div className="offer-stamp">NEW<br />SEASON</div></section>

        <section id="collection" className="collection-section">
          <div className="collection-heading"><div><span className="eyebrow">THE MAHIR COLLECTION</span><h2>Pieces to keep close</h2></div><span className="product-count" role="status">{loading ? "Loading collection…" : loadError ? "Collection unavailable" : `${filtered.length} styles`}</span></div>
          <div className="collection-tools"><div className="category-filters" aria-label="Filter by category">{categories.map((item) => <button key={item} type="button" className={category === item ? "active" : ""} onClick={() => setCategory(item)}>{item}</button>)}</div><div className="store-sort-tools"><button type="button" className={favoritesOnly ? "favorite-filter active" : "favorite-filter"} onClick={() => setFavoritesOnly(!favoritesOnly)} aria-pressed={favoritesOnly}>♡ Saved ({favorites.length})</button><select aria-label="Sort products" value={sort} onChange={e => setSort(e.target.value)}><option value="featured">Featured first</option><option value="newest">Newest arrivals</option><option value="price-low">Price: low to high</option><option value="price-high">Price: high to low</option></select></div></div>
          {loading ? <div className="catalog-message" role="status">Curating the collection…</div> : loadError ? <div className="catalog-message" role="alert">{loadError}</div> : filtered.length ? <div className="product-grid">{filtered.map((product, index) => {
            const price = productPrice(product);
            const discount = price.regular > price.current ? Math.round((1 - price.current / price.regular) * 100) : 0;
            return <article className="product-card" key={product.id}><div className="product-image-wrap"><button className="product-view" type="button" aria-label={`View ${product.name}`} onClick={() => setDetail(product)}><img src={product.image || PRODUCT_IMAGES[index % PRODUCT_IMAGES.length]} alt={`${product.name} collection style`} loading="lazy" /></button><button className="product-favorite" type="button" aria-label={`Save ${product.name}`} aria-pressed={favorites.includes(product.id)} onClick={() => toggleFavorite(product.id)}>{favorites.includes(product.id) ? "♥" : "♡"}</button><span className="product-tag">{discount ? `${discount}% OFF` : index < 2 ? "NEW ARRIVAL" : "MAHIR EDIT"}</span><button type="button" aria-label={`Add ${product.name} to bag`} className="quick-add" disabled={product.factory_quantity <= 0} onClick={() => { addToCart(product); setCartOpen(true); }}>+</button></div><div className="product-details"><div className="product-category">{product.category_name || "MAHIR COLLECTION"}{product.size ? <span> · {product.size}</span> : null}</div><h3><button className="product-name-button" onClick={() => setDetail(product)}>{product.name}</button></h3><span className="product-availability">{product.factory_quantity > 0 ? "In stock" : "Out of stock"}</span><div className="product-prices"><strong>{money(price.current)}</strong>{price.regular > price.current ? <><del>{money(price.regular)}</del><span>Save {money(price.regular - price.current)}</span></> : null}</div></div></article>;
          })}</div> : <div className="catalog-message">{products.length ? "No styles match your search." : "New styles are being added to the collection. Check back soon."}</div>}
          {!loading && loadError && <button className="retry-button" type="button" onClick={() => setCatalogAttempt((attempt) => attempt + 1)}>Try again</button>}
        </section>
        <section id="story" className="brand-story"><span className="eyebrow">THE MAHIR PHILOSOPHY</span><h2>Some things never<br />go out of <em>tradition.</em></h2><p>The quiet confidence of a beautiful fit. The character in every detail. We bring together timeless style and a personal touch, so you can feel like yourself on the days that matter.</p><a className="text-link" href="https://wa.me/8801781879276" target="_blank" rel="noopener noreferrer">Let us help you find your look ↗</a><span className="story-monogram" aria-hidden="true">M</span></section>
      </main>

      <footer className="store-footer"><Link className="store-brand" to="/shop"><span className="brand-mark">M</span><span>MAHIR <i>SHERWANI</i></span></Link><p>Made for the moments that become memories.</p><div><a href="#collection">Collection</a><Link to="/my-orders">Track my orders</Link><Link to="/login">Admin &amp; showroom login</Link><span>© {new Date().getFullYear()} Mahir Sherwani</span></div></footer>
      {detail && <div className="c-modal-backdrop commerce" onClick={e => { if (e.target === e.currentTarget) setDetail(null); }}><section className="c-modal" role="dialog" aria-modal="true" aria-labelledby="product-detail-title"><div className="c-modal-heading"><h2 id="product-detail-title">{detail.name}</h2><button autoFocus aria-label="Close product details" onClick={() => setDetail(null)}>×</button></div><div className="c-form c-editor-grid"><div className="product-detail-photo"><img src={detail.image || PRODUCT_IMAGES[0]} alt={detail.name} /></div><div><span className="c-badge">{detail.category_name}</span><h2>{detail.name}</h2><p>{detail.size ? `Size: ${detail.size}` : "Standard size"}{detail.code ? ` · ${detail.code}` : ""}</p><h2>{money(productPrice(detail).current)}</h2>{detail.discount_price && <p><del>{money(detail.selling_price)}</del> · Save {money(Number(detail.selling_price) - Number(detail.discount_price))}</p>}<p className="product-description">{detail.description || "Contact us for fabric, fit and sizing details."}</p><p>{detail.factory_quantity > 0 ? `${detail.factory_quantity} available` : "Currently out of stock"}</p><div className="commerce-actions"><button disabled={detail.factory_quantity <= 0} className="c-button" onClick={() => { addToCart(detail); setDetail(null); setCartOpen(true); }}>Add to bag</button><button className="c-button secondary" onClick={() => toggleFavorite(detail.id)}>{favorites.includes(detail.id) ? "♥ Saved" : "♡ Save"}</button></div><p className="c-help">Cash on Delivery for products. Delivery charge is paid in advance.</p></div></div></section></div>}
      {cartOpen && <div className="cart-overlay" role="presentation" onClick={(event) => { if (event.target === event.currentTarget) setCartOpen(false); }}><aside className="cart-panel" aria-label="Shopping bag"><div className="cart-heading"><div><span className="eyebrow">YOUR SELECTION</span><h2>Shopping bag <small>({cartCount})</small></h2></div><button type="button" className="cart-close" aria-label="Close bag" onClick={() => setCartOpen(false)}>×</button></div>{cartItems.length ? <><div className="cart-lines">{cartItems.map((product) => <div className="cart-line" key={product.id}><img src={product.image || PRODUCT_IMAGES[products.indexOf(product) % PRODUCT_IMAGES.length]} alt="" /><div className="cart-line-info"><strong>{product.name}</strong><small>{product.size || product.category_name}</small><div className="quantity-control"><button type="button" aria-label="Decrease quantity" onClick={() => changeQuantity(product.id, -1)}>−</button><span>{cart[product.id]}</span><button type="button" aria-label="Increase quantity" onClick={() => changeQuantity(product.id, 1)}>+</button></div></div><b>{money(productPrice(product).current * cart[product.id])}</b></div>)}</div><div className="cart-summary">{cartSavings > 0 && <p><span>You save</span><strong>{money(cartSavings)}</strong></p>}<p className="cart-total"><span>Estimated total</span><strong>{money(cartTotal)}</strong></p>{orderRequiresCustomer ? <div className="order-auth-prompt"><strong>Sign in to place your order</strong><p>Your bag is saved. Sign in to your customer account or create one to continue.</p><button className="checkout-button" type="button" onClick={() => continueToCustomerAuth("/login")}>Customer login <span aria-hidden="true">→</span></button><button className="signup-order-button" type="button" onClick={() => continueToCustomerAuth("/signup")}>Create customer account</button></div> : <><Link className="checkout-button" to="/checkout">Checkout · Cash on Delivery <span aria-hidden="true">→</span></Link><button className="whatsapp-order-button" type="button" onClick={orderOnWhatsApp}>Ask on WhatsApp <span aria-hidden="true">↗</span></button><small>Pay delivery charge first. Pay product price on delivery.</small></>}</div></> : <div className="empty-cart"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 8h14l1 13H4L5 8Z" /><path d="M9 8V6a3 3 0 0 1 6 0v2" /></svg><p>Your bag is waiting for something special.</p><button type="button" onClick={() => { setCartOpen(false); document.getElementById("collection")?.scrollIntoView({ behavior: "smooth" }); }}>Explore the collection</button></div>}</aside></div>}
    </div>
  );
}
