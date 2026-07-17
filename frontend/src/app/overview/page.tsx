import type { Metadata } from "next";
import OverviewClient from "./OverviewClient";
import { BRAND, CITY } from "@/lib/city.config";

export const metadata: Metadata = {
  title: `City Overview - ${BRAND}`,
  description: `Aggregate health metrics, trends, seasonal patterns, and custodian breakdown across all tracked lakes in ${CITY}.`,
};

export default function OverviewPage() {
  return <OverviewClient />;
}
