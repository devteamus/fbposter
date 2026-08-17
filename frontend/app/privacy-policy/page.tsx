import type { Metadata } from "next";
import Link from "next/link";
import { Facebook } from "lucide-react";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "Privacy Policy for FB Auto-Poster.",
};

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-muted/30 px-4 py-12">
      <div className="mx-auto w-full max-w-2xl space-y-8">
        <div className="flex flex-col items-center space-y-2 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Facebook className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Privacy Policy</h1>
          <p className="text-sm text-muted-foreground">FB Auto-Poster</p>
          <p className="text-xs text-muted-foreground">Last updated: August 2026</p>
        </div>

        <div className="space-y-6 rounded-xl border bg-card p-6 text-sm leading-relaxed shadow-sm md:p-8">
          <section className="space-y-2">
            <h2 className="text-base font-semibold">1. Overview</h2>
            <p className="text-muted-foreground">
              FB Auto-Poster ("the Service", "we", "us") is a tool that lets a Facebook Page
              owner schedule and automatically publish their own content (text, images,
              videos, and Reels) to Facebook Pages they own or manage, from a CSV file they
              upload. This policy explains what information we collect, why, and how it is
              handled.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">2. Information We Collect</h2>
            <ul className="list-disc space-y-1.5 pl-5 text-muted-foreground">
              <li>
                <span className="font-medium text-foreground">Account information</span> — the
                username, email address, and password (stored as a salted hash, never in
                plain text) you provide when you register.
              </li>
              <li>
                <span className="font-medium text-foreground">Facebook Page credentials</span> —
                the Page access token, Page ID, and Page name you provide so the Service can
                publish posts to that Page on your behalf via the Facebook Graph API.
              </li>
              <li>
                <span className="font-medium text-foreground">Content you upload</span> — the
                captions, media URLs, optional comments, and post scheduling details
                contained in the CSV files you upload.
              </li>
              <li>
                <span className="font-medium text-foreground">Usage data</span> — basic
                operational logs (e.g. job status, post success/failure) needed to run and
                troubleshoot the scheduling feature.
              </li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">3. How We Use Your Information</h2>
            <p className="text-muted-foreground">
              Your information is used solely to operate the Service: authenticating you,
              publishing your scheduled content to the Facebook Page(s) you connect, and
              showing you the status of your posting jobs. We do not sell, rent, or share
              your personal information or Facebook credentials with third parties, and we
              do not use your data for advertising.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">4. Data Retention</h2>
            <p className="text-muted-foreground">
              Uploaded CSV files are automatically deleted from our storage a set number of
              hours after a posting job completes. Job and post history (captions, media
              links, and status) is retained for a limited number of days after completion
              to let you review past activity, after which it is automatically and
              permanently deleted. You can also delete a job manually at any time, which
              removes its file and history immediately.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">5. Facebook Platform Data</h2>
            <p className="text-muted-foreground">
              The Service uses the Facebook Graph API only to publish content to Pages you
              explicitly connect, using the access token and permissions you grant. We
              request only the permissions necessary for this purpose (managing Page posts,
              managing engagement on those posts, and publishing video/Reels content). We do
              not access your personal Facebook profile, friends list, or any data unrelated
              to the Pages you connect.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">6. Data Security</h2>
            <p className="text-muted-foreground">
              Passwords are hashed with bcrypt. Access to the Service is protected by
              authenticated, time-limited session tokens. Reasonable technical measures
              (rate limiting, input validation, and restricted error output) are in place to
              protect your data from unauthorized access.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">7. Your Rights</h2>
            <p className="text-muted-foreground">
              You may request deletion of your account and associated data, or ask what
              data we hold about you, at any time by contacting us using the details below.
              You can also disconnect a Facebook Page from the Service at any time, which
              stops the Service from posting to it.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">8. Children's Privacy</h2>
            <p className="text-muted-foreground">
              The Service is not directed at children and is not knowingly used by anyone
              under the age required to hold a Facebook Page (per Facebook's own terms).
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">9. Changes to This Policy</h2>
            <p className="text-muted-foreground">
              This policy may be updated from time to time. Material changes will be
              reflected by updating the "Last updated" date above.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">10. Contact</h2>
            <p className="text-muted-foreground">
              For questions about this policy or your data, contact us at{" "}
              <a
                href="mailto:Support@postgo.fun"
                className="font-medium text-primary underline underline-offset-2"
              >
                Support@postgo.fun
              </a>
              , or by mail at:
            </p>
            <p className="text-muted-foreground">
              House 69, Mirpur-1, Dhaka 1216, Bangladesh
            </p>
          </section>
        </div>

        <p className="text-center text-sm">
          <Link href="/" className="font-medium text-primary underline underline-offset-4">
            ← Back to home
          </Link>
        </p>
      </div>
    </div>
  );
}
