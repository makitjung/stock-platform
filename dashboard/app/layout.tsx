import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stock Platform Dashboard",
  description: "트렌드 분석 및 뉴스 브리핑 대시보드",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
