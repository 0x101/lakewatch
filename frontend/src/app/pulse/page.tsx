import type { Metadata } from "next";
import PulseClient from "./PulseClient";
import { BRAND, CITY } from "@/lib/city.config";

export const metadata: Metadata = {
  title: `Pulse — ${BRAND}`,
  description: `What changed at ${CITY}'s lakes — recent gainers, shrinkers, and an algae watchlist, tracked from space.`,
};

export default function PulsePage() {
  return <PulseClient />;
}
