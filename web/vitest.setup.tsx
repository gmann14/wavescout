import "@testing-library/jest-dom/vitest";
import React from "react";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("next/image", () => ({
  default: ({
    alt,
    src,
    unoptimized: _unoptimized,
    ...props
  }: React.ImgHTMLAttributes<HTMLImageElement> & {
    src: string;
    unoptimized?: boolean;
  }) => (
    <img alt={alt} src={src} {...props} />
  ),
}));
