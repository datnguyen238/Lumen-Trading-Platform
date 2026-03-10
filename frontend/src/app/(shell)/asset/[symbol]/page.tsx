import { AssetView } from "@/components/market/asset-view";

export default async function AssetPage(props: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol: rawSymbol } = await props.params;
  const symbol = safeDecode(rawSymbol);

  return <AssetView symbol={symbol} />;
}

function safeDecode(value: string) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
