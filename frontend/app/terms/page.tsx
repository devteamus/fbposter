import type { Metadata } from "next";
import Link from "next/link";
import { Facebook } from "lucide-react";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "Terms of Service for FB Auto-Poster.",
};

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-muted/30 px-4 py-12">
      <div className="mx-auto w-full max-w-2xl space-y-8">
        <div className="flex flex-col items-center space-y-2 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Facebook className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Terms of Service</h1>
          <p className="text-sm text-muted-foreground">FB Auto-Poster</p>
          <p className="text-xs text-muted-foreground">Last updated: August 2026</p>
        </div>

        <div className="space-y-6 rounded-xl border bg-card p-6 text-sm leading-relaxed shadow-sm md:p-8">
          <section className="space-y-2">
            <h2 className="text-base font-semibold">1. Acceptance of Terms</h2>
            <p className="text-muted-foreground">
              By creating an account or using FB Auto-Poster ("the Service"), you agree to
              these Terms of Service. If you do not agree, please do not use the Service.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">2. Description of Service</h2>
            <p className="text-muted-foreground">
              The Service lets a Facebook Page owner or manager upload a CSV file of
              captions, media links, and optional comments, and have that content
              automatically published to their own connected Facebook Page(s) on a
              schedule, using the Facebook Graph API.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">3. Your Responsibilities</h2>
            <ul className="list-disc space-y-1.5 pl-5 text-muted-foreground">
              <li>You must only connect Facebook Pages that you own or are authorized to manage.</li>
              <li>
                You are solely responsible for the content you upload and publish through the
                Service, including ensuring it complies with Facebook's own Terms of Service,
                Community Standards, and applicable law.
              </li>
              <li>You are responsible for keeping your account credentials confidential.</li>
              <li>
                You must not use the Service to publish spam, misleading content, or content
                that infringes on the rights of others.
              </li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">4. Facebook Platform Compliance</h2>
            <p className="text-muted-foreground">
              Your use of the Service is also subject to Meta's Platform Terms and
              Facebook's Terms of Service. The Service acts only on the permissions you
              explicitly grant through Facebook Login, and only to publish content you
              provide to Pages you connect.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">5. No Warranty</h2>
            <p className="text-muted-foreground">
              The Service is provided "as is" without warranties of any kind. We do not
              guarantee that scheduled posts will always publish successfully, that the
              Facebook API will always be available, or that the Service will be
              uninterrupted or error-free. Facebook API changes, rate limits, or account
              restrictions outside our control may affect posting.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">6. Limitation of Liability</h2>
            <p className="text-muted-foreground">
              To the fullest extent permitted by law, we are not liable for any indirect,
              incidental, or consequential damages arising from your use of the Service,
              including lost reach, engagement, or any action taken against your Facebook
              Page or account by Meta.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">7. Account Suspension &amp; Termination</h2>
            <p className="text-muted-foreground">
              We may suspend or terminate access to the Service for accounts that violate
              these Terms, misuse the Service, or use it in a way that risks the Service's
              standing with the Facebook Platform. You may stop using the Service and
              request deletion of your account at any time.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">8. Changes to These Terms</h2>
            <p className="text-muted-foreground">
              These Terms may be updated from time to time. Continued use of the Service
              after changes are posted constitutes acceptance of the updated Terms.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold">9. Contact</h2>
            <p className="text-muted-foreground">
              For questions about these Terms, contact us at{" "}
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
