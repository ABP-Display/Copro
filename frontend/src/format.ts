export const kinds: Record<string, string> = {
  apartment: "Appartement",
  parking: "Parking",
  cellar: "Cave",
  commercial: "Local commercial",
  other: "Autre",
};
export const number = (value: string | number) =>
  new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 }).format(
    Number(value),
  );
