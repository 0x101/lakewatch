"use client";

import { ThemeToggle } from "@/components/ui/ThemeToggle";

export function AboutHeader() {
  return (
    <div className="flex items-center justify-between mb-6">
      <h1 className="text-3xl font-bold text-white">What is this?</h1>
      <ThemeToggle />
    </div>
  );
}
