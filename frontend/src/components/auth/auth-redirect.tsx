'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/AuthProvider';

interface AuthRedirectProps {
  redirectTo?: string;
  children: React.ReactNode;
}

/**
 * Component that automatically redirects authenticated users to a specified route.
 * Only renders children if user is not authenticated or still loading.
 */
export function AuthRedirect({ redirectTo = '/dashboard', children }: AuthRedirectProps) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Only redirect if user is authenticated and not loading
    if (!isLoading && user) {
      router.push(redirectTo);
    }
  }, [user, isLoading, router, redirectTo]);

  // Don't render children if user is authenticated (to prevent flash of content)
  if (!isLoading && user) {
    return null;
  }

  // Show children for unauthenticated users or while loading
  return <>{children}</>;
}
