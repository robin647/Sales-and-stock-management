import { Link, useParams } from "react-router-dom";
import { useStoreLocale } from "../context/StoreLocaleContext";
import { StoreSeo, StorePreferencesBar } from "../components/StoreExperience";
import "./storefront.css";

export default function StorePage() {
  const { slug } = useParams(); const { config } = useStoreLocale();
  const page = config.content.find(row => row.slug === slug && row.kind !== "banner")
    || (slug === "returns" && config.store.return_policy ? { title: "Returns & refunds", body: config.store.return_policy } : null)
    || (slug === "privacy" && config.store.privacy_policy ? { title: "Privacy policy", body: config.store.privacy_policy } : null);
  return <main className="storefront"><StoreSeo /><StorePreferencesBar /><article className="store-public-page"><Link to="/shop">← Back to the collection</Link><h1>{page?.title || "Page unavailable"}</h1>{page?.image_url && <img src={page.image_url} alt={page.title} />}<p style={{ whiteSpace: "pre-wrap" }}>{page?.body || "This page has not been published."}</p></article></main>;
}
