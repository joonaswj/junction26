const eur = new Intl.NumberFormat("fi-FI", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
});

const eurCents = new Intl.NumberFormat("fi-FI", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
});

export const formatEur = (value: number) => eur.format(value);
export const formatEurCents = (value: number) => eurCents.format(value);

// "age 45-54, upper-middle income" -> "aged 45–54 with a similar income"
export function describePeers(peerGroup: string): string {
    const age = peerGroup.match(/^age ([^,]+),/);
    return age
        ? `people aged ${age[1].replace("-", "–")} with a similar income`
        : "people with a similar income";
}

// "cust02868", "02868" or "2868" -> "CUST02868"
export function normalizeCustomerId(input: string): string {
    const value = input.trim().toUpperCase();
    const digits = value.replace(/^CUST/, "");
    return /^\d{1,5}$/.test(digits) ? `CUST${digits.padStart(5, "0")}` : value;
}
