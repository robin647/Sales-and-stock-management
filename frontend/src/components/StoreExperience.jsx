import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { ecommerceApi } from "../api/endpoints";
import { useStoreLocale } from "../context/StoreLocaleContext";

export function StorePreferencesBar() {
  const { config, locale, locales, select, labels } = useStoreLocale();
  return <div className="store-preferences-bar"><span>{config.campaigns[0]?.headline || config.store.announcement || `${config.store.store_name || "MAHIR"} · Thoughtfully made for your celebrations`}</span><div><Link to="/support">{labels.support}</Link><select aria-label="Language and display currency" value={`${locale.language_code}-${locale.currency_code}`} onChange={event => select(event.target.value)}>{locales.map(row => <option key={`${row.language_code}-${row.currency_code}`} value={`${row.language_code}-${row.currency_code}`}>{row.language_name} · {row.currency_code}</option>)}</select></div></div>;
}

export function StorePublishedContent() {
  const { config, labels } = useStoreLocale();
  const banners = config.content.filter(row => row.kind === "banner");
  return <div className="store-managed-content">{banners.length > 0 && <section className="store-managed-banners">{banners.map(row => <article key={row.id}>{row.image_url && <img src={row.image_url} alt={row.title} loading="lazy" />}<div><h2>{row.title}</h2><p>{row.body}</p>{row.link && <a href={row.link}>Discover more →</a>}</div></article>)}</section>}{config.reviews.length > 0 && <section><h2>{labels.reviews}</h2><div className="store-review-grid">{config.reviews.slice(0, 6).map(row => <article key={row.id}><span aria-label={`${row.rating} out of 5 stars`}>{"★".repeat(row.rating)}{"☆".repeat(5 - row.rating)}</span><p>{row.comment}</p><strong>{row.customer_name}</strong>{row.reply && <small>MAHIR: {row.reply}</small>}</article>)}</div></section>}<section className="store-policy-links"><h2>{labels.policies}</h2>{config.content.filter(row => row.kind !== "banner").map(row => <Link key={row.id} to={`/pages/${row.slug}`}>{row.title} ↗</Link>)}<Link to="/support">{labels.support} ↗</Link>{config.store.support_phone && <a href={`tel:${config.store.support_phone}`}>{config.store.support_phone}</a>}{config.store.support_email && <a href={`mailto:${config.store.support_email}`}>{config.store.support_email}</a>}</section></div>;
}

export function StoreSeo() {
  const location = useLocation();
  useEffect(() => {
    let active = true;
    const previous = document.title;
    const changes = [];
    ecommerceApi.public(location.pathname).then(({ data }) => {
      if (!active || !data.seo) return;
      const seo = data.seo; document.title = seo.title;
      const set = (selector, tag, attr, name, value) => {
        let node = document.head.querySelector(selector), created = !node;
        if (!node) { node = document.createElement(tag); node.setAttribute(attr, name); document.head.appendChild(node); }
        const key = tag === "link" ? "href" : "content", old = node.getAttribute(key);
        node.setAttribute(key, value); changes.push(() => { if (created) node.remove(); else if (old === null) node.removeAttribute(key); else node.setAttribute(key, old); });
      };
      set('meta[name="description"]', "meta", "name", "description", seo.description);
      set('meta[name="robots"]', "meta", "name", "robots", seo.noindex ? "noindex,nofollow" : "index,follow");
      if (seo.canonical_url) set('link[rel="canonical"]', "link", "rel", "canonical", seo.canonical_url);
      set('meta[property="og:title"]', "meta", "property", "og:title", seo.title);
      if (seo.image_url) set('meta[property="og:image"]', "meta", "property", "og:image", seo.image_url);
    }).catch(() => {});
    return () => { active = false; document.title = previous; changes.forEach(undo => undo()); };
  }, [location.pathname]);
  return null;
}
