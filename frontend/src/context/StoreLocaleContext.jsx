import { createContext, useContext, useEffect, useState } from "react";
import { ecommerceApi } from "../api/endpoints";

const StoreLocaleContext = createContext(null);
const fallback = { language_code: "en", language_name: "English", currency_code: "BDT", currency_symbol: "৳", exchange_rate: 1 };
export function StoreLocaleProvider({ children }) {
  const [config, setConfig] = useState({ store: {}, content: [], campaigns: [], locales: [], reviews: [] });
  const [selected, setSelected] = useState(() => { try { return localStorage.getItem("mahir-store-locale") || ""; } catch { return ""; } });
  useEffect(() => { ecommerceApi.public("/").then(res => setConfig(res.data)).catch(() => {}); }, []);
  const locales = config.locales.length ? config.locales : [fallback];
  const locale = locales.find(row => `${row.language_code}-${row.currency_code}` === selected) || locales.find(row => row.is_default) || locales[0];
  function select(value) { setSelected(value); try { localStorage.setItem("mahir-store-locale", value); } catch {} }
  const formatMoney = value => `${locale.currency_symbol}${(Number(value || 0) * Number(locale.exchange_rate)).toLocaleString(locale.language_code === "bn" ? "bn-BD" : "en-BD", { maximumFractionDigits: 2 })}`;
  const labels = locale.language_code === "bn" ? { collection: "কালেকশন দেখুন", support: "সাহায্য ও রিটার্ন", reviews: "ক্রেতাদের মতামত", policies: "তথ্য ও নীতিমালা" } : { collection: "Explore the collection", support: "Support & returns", reviews: "Customer reviews", policies: "Information & policies" };
  return <StoreLocaleContext.Provider value={{ config, locale, locales, select, formatMoney, labels }}>{children}</StoreLocaleContext.Provider>;
}
export const useStoreLocale = () => useContext(StoreLocaleContext);
