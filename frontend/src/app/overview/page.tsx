import type { Metadata } from "next";
import OverviewClient from "./OverviewClient";

export const metadata: Metadata = {
  title: "City Overview - Namma Lakes",
  description:
    "Aggregate health metrics, trends, seasonal patterns, and custodian breakdown across all 176 tracked lakes in Bangalore.",
};

export default function OverviewPage() {
  return <OverviewClient />;
}
