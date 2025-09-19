'use client';

import { Changelog } from "@/components/home/sections/changelog";
import { AuthRedirect } from '@/components/auth/auth-redirect';

export default function ChangelogPage() {
  return (
    <AuthRedirect>
      <section id="changelog">
        <Changelog />
      </section>
    </AuthRedirect>
  );
}