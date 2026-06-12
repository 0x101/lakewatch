import type { Metadata } from "next";
import PulseClient from "./PulseClient";

export const metadata: Metadata = {
  title: "Pulse — Namma Lakes",
  description:
    "What changed at Bangalore's lakes — recent gainers, shrinkers, and an algae watchlist, tracked from space.",
};

export default function PulsePage() {
  return <PulseClient />;
}
