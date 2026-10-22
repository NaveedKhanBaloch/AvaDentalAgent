import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'DentalVoice AI',
  description: 'AI-powered dental clinic operations dashboard',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
