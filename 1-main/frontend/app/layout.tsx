import React from "react";

export const metadata = {
  title: "Shorts Factory",
  description: "Turn raw footage into viral vertical reels.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "Inter, sans-serif", background: "#0f172a" }}>
        {children}
      </body>
    </html>
  );
}
