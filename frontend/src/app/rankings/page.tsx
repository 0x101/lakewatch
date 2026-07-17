import type { Metadata } from "next";
import RankingsClient from "./RankingsClient";
import { BRAND } from "@/lib/city.config";

export const metadata: Metadata = {
  title: `Rankings - ${BRAND}`,
  description:
    "Lakes ranked by health, improvement, decline, pollution, and cleanliness. Satellite-derived metrics.",
};

export default function RankingsPage() {
  return <RankingsClient />;
}
