import type { Metadata } from "next";
import LakesClient from "./LakesClient";
import { BRAND, CITY } from "@/lib/city.config";

export const metadata: Metadata = {
  title: `All Lakes - ${BRAND}`,
  description: `Sortable, filterable table of all tracked lakes in ${CITY} with health scores, surface area, and change metrics.`,
};

export default function LakesPage() {
  return <LakesClient />;
}
