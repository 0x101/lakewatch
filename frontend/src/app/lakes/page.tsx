import type { Metadata } from "next";
import LakesClient from "./LakesClient";

export const metadata: Metadata = {
  title: "All Lakes - Namma Lakes",
  description:
    "Sortable, filterable table of all 176 tracked lakes in Bangalore with health scores, surface area, and change metrics.",
};

export default function LakesPage() {
  return <LakesClient />;
}
