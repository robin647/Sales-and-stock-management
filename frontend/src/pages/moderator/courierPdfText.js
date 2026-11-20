export function courierPdfText(items) {
  const rows = [];
  const words = items.filter(({ str }) => str?.trim()).sort((a, b) => b.transform[5] - a.transform[5]);
  for (const word of words) {
    const y = word.transform[5];
    const row = rows.at(-1);
    // The large COD amount sits slightly below the label's text baseline.
    if (row && Math.abs(row.y - y) <= 3) row.words.push(word);
    else rows.push({ y, words: [word] });
  }
  return rows.map(({ words }) => words.sort((a, b) => a.transform[4] - b.transform[4])
    .map(({ str }) => str.trim()).join(" ")).join("\n");
}
