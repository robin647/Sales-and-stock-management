import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { productApi } from "../api/endpoints";
import { useAuth } from "../context/AuthContext.jsx";
import { useTheme } from "../context/ThemeContext.jsx";
import "./storefront.css";

const HERO_IMAGE = "https://images.pexels.com/photos/19168798/pexels-photo-19168798/free-photo-of-groom-in-traditional-clothes.jpeg?auto=compress&w=1400";
const PRODUCT_IMAGES = [
  "https://images.pexels.com/photos/39210712/pexels-photo-39210712/free-photo-of-elegant-traditional-indian-sherwani-on-display.jpeg?auto=compress&w=800",
  "https://images.pexels.com/photos/21926986/pexels-photo-21926986/free-photo-of-close-up-of-an-embroidered-sherwani-hanging-on-a-branch.jpeg?auto=compress&w=800",
  "https://images.pexels.com/photos/18016521/pexels-photo-18016521/free-photo-of-traditional-clothing-on-hanger.jpeg?auto=compress&w=800",
  "https://images.pexels.com/photos/2060241/pexels-photo-2060241.jpeg?auto=compress&w=800",
];

const money = (value) => `৳${Number(value || 0).toLocaleString("en-BD", { maximumFractionDigits: 0 })}`;

function productPrice(product) {
  const regular = Number(product.selling_price || 0);
  const offer = Number(product.discount_price || 0);
  return { regular, current: offer > 0 && offer < regular ? offer : regular };
}

export default function Storefront() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All styles");
  const [cart, setCart] = useState({});
  const [cartOpen, setCartOpen] = useState(false);

  useEffect(() => {
    let active = true;
    productApi.listAll({ is_active: true })
      .then((rows) => { if (active) setProducts(rows); })
      .catch(() => { if (active) setLoadError(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const categories = useMemo(() => ["All styles", ...new Set(products.map((item) => item.category_name).filter(Boolean))], [products]);
  const filtered = useMemo(() => products.filter((item) => {
    const matchesCategory = category === "All styles" || item.category_name === category;
    const matchesSearch = `${item.name} ${item.code} ${item.category_name} ${item.size}`.toLowerCase().includes(query.toLowerCase());
    return matchesCategory && matchesSearch;
  }), [category, products, query]);
  const cartItems = products.filter((product) => cart[product.id]);
  const cartCount = Object.values(cart).reduce((sum, quantity) => sum + quantity, 0);
  const cartTotal = cartItems.reduce((sum, product) => sum + productPrice(product).current * cart[product.id], 0);
  const cartSavings = cartItems.reduce((sum, product) => sum + (productPrice(product).regular - productPrice(product).current) * cart[product.id], 0);

  function addToCart(product) {
    setCart((current) => ({ ...current, [product.id]: (current[product.id] || 0) + 1 }));
  }

  function changeQuantity(productId, delta) {
    setCart((current) => {
      const nextQuantity = (current[productId] || 0) + delta;
      const next = { ...current };
      if (nextQuantity <= 0) delete next[productId];
      else next[productId] = nextQuantity;
      return next;
    });
  }

  function orderOnWhatsApp() {
    const lines = cartItems.map((product) => `${product.name}${product.size ? ` (${product.size})` : ""} x${cart[product.id]} - ${money(productPrice(product).current * cart[product.id])}`);
    const message = `Assalamu alaikum, I would like to order:\n${lines.join("\n")}\nTotal: ${money(cartTotal)}`;
    window.open(`https://wa.me/8801781879276?text=${encodeURIComponent(message)}`, "_blank", "noopener,noreferrer");
  }

  return (
    <div className="storefront">
      <div className="store-promo"><span>Complimentary delivery on orders over ৳5,000</span><a href="#collection">Shop the collection <span aria-hidden="true">↗</span></a></div>
      <header className="store-header">
        <Link className="store-brand" to="/" aria-label="Mahir Sherwani home"><span className="brand-mark">M</span><span>MAHIR <i>SHERWANI</i></span></Link>
        <nav className="store-nav" aria-label="Main navigation"><a href="#collection">New arrivals</a><a href="#collection">Panjabi</a><a href="#collection">Sherwani</a><a href="#offers">Offers</a></nav>
        <div className="store-actions">
          <label className="store-search"><span aria-hidden="true">⌕</span><input aria-label="Search products" placeholder="Search styles" value={query} onChange={(event) => { setQuery(event.target.value); document.getElementById("collection")?.scrollIntoView({ behavior: "smooth" }); }} /></label>
          <button className="store-icon-button theme-toggle" type="button" title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`} onClick={toggleTheme}>{theme === "dark" ? "☼" : "◐"}</button>
          {user ? <button className="store-account" type="button" onClick={() => { logout(); window.location.reload(); }}>Sign out</button> : <Link className="store-account" to="/login">Login</Link>}
          <Link className="store-signup" to="/signup">Sign up</Link>
          <button className="store-icon-button cart-trigger" type="button" aria-label={`Open bag, ${cartCount} items`} onClick={() => setCartOpen(true)}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 8h14l1 13H4L5 8Z" /><path d="M9 8V6a3 3 0 0 1 6 0v2" /></svg><b>{cartCount}</b></button>
        </div>
      </header>

      <main>
        <section className="store-hero">
          <div className="hero-copy"><span className="eyebrow">CRAFTED FOR YOUR MOMENTS</span><h1>Tradition,<br /><em>tailored to you.</em></h1><p>Thoughtful details. Exceptional fabrics. Occasionwear made to be remembered.</p><a className="primary-link" href="#collection">Explore the collection <span aria-hidden="true">→</span></a><div className="hero-note"><span>01 / 03</span><span>Made for celebration, made for you</span></div></div>
          <div className="hero-photo" style={{ backgroundImage: `url("${HERO_IMAGE}")` }}><div className="hero-photo-caption"><span>THE FESTIVE EDIT</span><strong>Wear the occasion.</strong></div><div className="hero-vertical">MAHIR SHERWANI · EST. 2018</div></div>
        </section>

        <section className="store-benefits" aria-label="Shopping benefits"><div><span>✳</span><p><strong>Made with care</strong><small>Finishing you can feel</small></p></div><div><span>↗</span><p><strong>Easy ordering</strong><small>Talk to us on WhatsApp</small></p></div><div><span>◇</span><p><strong>Secure delivery</strong><small>Across Bangladesh</small></p></div></section>
        <section id="offers" className="offer-band"><div><span className="eyebrow">THE OCCASION EDIT</span><h2>Make every entrance count.</h2><p>Discover handpicked looks for celebrations, gatherings and everything in between.</p></div><a href="#collection">Find your look <span aria-hidden="true">↗</span></a><div className="offer-stamp">NEW<br />SEASON</div></section>

        <section id="collection" className="collection-section">
          <div className="collection-heading"><div><span className="eyebrow">THE MAHIR COLLECTION</span><h2>Pieces to keep close</h2></div><span className="product-count">{filtered.length} styles</span></div>
          <div className="collection-tools"><div className="category-filters" aria-label="Filter by category">{categories.map((item) => <button key={item} type="button" className={category === item ? "active" : ""} onClick={() => setCategory(item)}>{item}</button>)}</div><span className="collection-hint">Designed for the days that matter</span></div>
          {loading ? <div className="catalog-message">Curating the collection…</div> : loadError ? <div className="catalog-message">We could not load the collection right now. Please refresh to try again.</div> : filtered.length ? <div className="product-grid">{filtered.map((product, index) => {
            const price = productPrice(product);
            const discount = price.regular > price.current ? Math.round((1 - price.current / price.regular) * 100) : 0;
            return <article className="product-card" key={product.id}><div className="product-image-wrap"><img src={product.image || PRODUCT_IMAGES[index % PRODUCT_IMAGES.length]} alt={`${product.name} collection style`} loading="lazy" /><span className="product-tag">{discount ? `${discount}% OFF` : index < 2 ? "NEW ARRIVAL" : "MAHIR EDIT"}</span><button type="button" aria-label={`Add ${product.name} to bag`} className="quick-add" onClick={() => { addToCart(product); setCartOpen(true); }}>+</button></div><div className="product-details"><div className="product-category">{product.category_name || "MAHIR COLLECTION"}{product.size ? <span> · {product.size}</span> : null}</div><h3>{product.name}</h3><div className="product-prices"><strong>{money(price.current)}</strong>{price.regular > price.current ? <><del>{money(price.regular)}</del><span>Save {money(price.regular - price.current)}</span></> : null}</div></div></article>;
          })}</div> : <div className="catalog-message">{products.length ? "No styles match your search." : "New styles are being added to the collection. Check back soon."}</div>}
          {loadError && <button className="retry-button" type="button" onClick={() => window.location.reload()}>Try again</button>}
        </section>
      </main>

      <footer className="store-footer"><Link className="store-brand" to="/"><span className="brand-mark">M</span><span>MAHIR <i>SHERWANI</i></span></Link><p>Made for the moments that become memories.</p><div><a href="#collection">Collection</a><Link to="/login">Admin &amp; showroom login</Link><span>© {new Date().getFullYear()} Mahir Sherwani</span></div></footer>
      {cartOpen && <div className="cart-overlay" role="presentation" onClick={(event) => { if (event.target === event.currentTarget) setCartOpen(false); }}><aside className="cart-panel" aria-label="Shopping bag"><div className="cart-heading"><div><span className="eyebrow">YOUR SELECTION</span><h2>Shopping bag <small>({cartCount})</small></h2></div><button type="button" className="cart-close" aria-label="Close bag" onClick={() => setCartOpen(false)}>×</button></div>{cartItems.length ? <><div className="cart-lines">{cartItems.map((product) => <div className="cart-line" key={product.id}><img src={product.image || PRODUCT_IMAGES[products.indexOf(product) % PRODUCT_IMAGES.length]} alt="" /><div className="cart-line-info"><strong>{product.name}</strong><small>{product.size || product.category_name}</small><div className="quantity-control"><button type="button" aria-label="Decrease quantity" onClick={() => changeQuantity(product.id, -1)}>−</button><span>{cart[product.id]}</span><button type="button" aria-label="Increase quantity" onClick={() => changeQuantity(product.id, 1)}>+</button></div></div><b>{money(productPrice(product).current * cart[product.id])}</b></div>)}</div><div className="cart-summary">{cartSavings > 0 && <p><span>You save</span><strong>{money(cartSavings)}</strong></p>}<p className="cart-total"><span>Estimated total</span><strong>{money(cartTotal)}</strong></p><button className="checkout-button" type="button" onClick={orderOnWhatsApp}>Order on WhatsApp <span aria-hidden="true">↗</span></button><small>We’ll confirm availability and delivery with you.</small></div></> : <div className="empty-cart"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 8h14l1 13H4L5 8Z" /><path d="M9 8V6a3 3 0 0 1 6 0v2" /></svg><p>Your bag is waiting for something special.</p><button type="button" onClick={() => { setCartOpen(false); document.getElementById("collection")?.scrollIntoView({ behavior: "smooth" }); }}>Explore the collection</button></div>}</aside></div>}
    </div>
  );
}