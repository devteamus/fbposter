import type { Metadata } from "next";
import "./globals.css";

// NOTE: change this once the domain is pointed & live, so OG/Twitter
// image + canonical URLs resolve to absolute, correct links.
const SITE_URL = "https://fb.postgo.fun";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "FB Auto-Poster — Multi-Account Facebook Scheduler",
    template: "%s | FB Auto-Poster",
  },
  description:
    "Schedule and automate posts across multiple Facebook Pages from one dashboard. Upload a CSV, set an interval, and let FB Auto-Poster handle the rest.",
  keywords: [
    "facebook auto poster",
    "facebook scheduler",
    "multi account facebook posting",
    "facebook automation",
    "social media scheduler",
  ],
  applicationName: "FB Auto-Poster",
  authors: [{ name: "Md Faisal Hossain", url: "https://www.linkedin.com/in/ifaisalh/" }],
  creator: "Md Faisal Hossain",
  robots: { index: true, follow: true },
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: "FB Auto-Poster",
    title: "FB Auto-Poster — Multi-Account Facebook Scheduler",
    description:
      "Schedule and automate posts across multiple Facebook Pages from one dashboard.",
  },
  twitter: {
    card: "summary_large_image",
    title: "FB Auto-Poster — Multi-Account Facebook Scheduler",
    description:
      "Schedule and automate posts across multiple Facebook Pages from one dashboard.",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background font-sans antialiased">{children}</body>
    </html>
  );
}
