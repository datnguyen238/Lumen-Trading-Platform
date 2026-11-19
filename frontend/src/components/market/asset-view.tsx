"use client";
import { Research } from "@/components/lumen/research";
export function AssetView({ symbol }: { symbol: string }) { return <Research key={symbol.toUpperCase()} symbol={symbol.toUpperCase()}/>; }
