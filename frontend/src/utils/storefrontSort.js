export function compareFeaturedProducts(a, b) {
  return (Number(b.popularity_orders) || 0) - (Number(a.popularity_orders) || 0)
    || (Date.parse(b.created_at) || 0) - (Date.parse(a.created_at) || 0)
    || Number(b.id) - Number(a.id);
}
