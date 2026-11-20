import districts from "./steadfastDistricts.json" with { type: "json" };
import { suggestDeliveryZone } from "./deliveryZone.js";

export { districts };

const normalize = (text) => text.normalize("NFC").toLowerCase().trim();
const dhakaSuburbs = /(?<![\p{L}\p{M}])(?:savar|ashulia|dhamrai|keraniganj|dohar|সাভার|আশুলিয়া|ধামরাই|কেরানীগঞ্জ|দোহার)(?![\p{L}\p{M}])/iu;

export function suggestSteadfastDestination(address, area) {
  for (const location of [area, address]) {
    const text = normalize(location);
    if (!text) continue;
    for (const part of text.split(",").reverse()) {
      const district = districts.find(({ name, aliases }) =>
        [name, ...aliases].some((alias) => normalize(alias) === part.trim()));
      if (district) return String(district.id);
    }
    const matches = districts.filter(({ name }) => {
      const district = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return new RegExp(`(?<![\\p{L}\\p{M}])${district}(?![\\p{L}\\p{M}])`, "iu").test(text);
    });
    if (matches.length === 1) return String(matches[0].id);
    if (dhakaSuburbs.test(text)) return "18";
  }
  return suggestDeliveryZone(address, area) === "inside" ? "1" : "";
}
