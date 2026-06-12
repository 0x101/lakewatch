import type { Metadata } from "next";
import RankingsClient from "./RankingsClient";

export const metadata: Metadata = {
  title: "Rankings - Namma Lakes",
  description:
    "Lakes ranked by health, improvement, decline, pollution, and cleanliness. Satellite-derived metrics.",
};

export default function RankingsPage() {
  return <RankingsClient />;
}
