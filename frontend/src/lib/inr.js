// Indian Rupee formatter — 1,00,000 style grouping
export function formatINR(value, symbol = "₹") {
  const n = Number(value);
  if (Number.isNaN(n)) return `${symbol}0`;
  const negative = n < 0;
  const abs = Math.abs(n);
  const [whole, decimal] = abs.toFixed(2).split(".");
  // Indian grouping: last 3 digits then groups of 2
  const lastThree = whole.slice(-3);
  const otherNumbers = whole.slice(0, -3);
  const formattedOther = otherNumbers ? otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ",") + "," : "";
  const decimalPart = decimal && decimal !== "00" ? "." + decimal : "";
  return `${negative ? "-" : ""}${symbol}${formattedOther}${lastThree}${decimalPart}`;
}
