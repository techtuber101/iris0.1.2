'use client';

import Image from 'next/image';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';

interface KortixLogoProps {
  size?: number;
  height?: number;
  isCollapsed?: boolean;
}
export function KortixLogo({ size = 24, height, isCollapsed = false }: KortixLogoProps) {
  const { theme, systemTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // After mount, we can access the theme
  useEffect(() => {
    setMounted(true);
  }, []);

  // Use symbol when collapsed, otherwise use the full logo
  const logoSrc = isCollapsed
    ? '/iris-symbol.png'
    : !mounted
      ? '/irislogo.png'
      : theme === 'dark' || (theme === 'system' && systemTheme === 'dark')
        ? '/irislogowhite.png'
        : '/irislogo.png';

  // Calculate proper dimensions for logo
  // Symbol is square, full logo is roughly 4:1 aspect ratio
  const logoWidth = size;
  const logoHeight = isCollapsed 
    ? size // Square for symbol
    : height || Math.round(size * 0.25); // Maintain aspect ratio for full logo

  return (
    <Image
        src={logoSrc}
        alt="Iris"
        width={logoWidth}
        height={logoHeight}
        className="flex-shrink-0"
        style={{ 
          width: logoWidth, 
          height: logoHeight, 
          minWidth: logoWidth, 
          minHeight: logoHeight,
          objectFit: 'contain'
        }}
      />
  );
}
