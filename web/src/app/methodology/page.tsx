import fs from "fs";
import path from "path";
import Nav from "@/components/Nav";
import MarkdownContent from "@/components/MarkdownContent";

export const metadata = {
  title: "How It Works — WaveScout",
  description: "How WaveScout detects surf spots from satellite imagery.",
};

export default function MethodologyPage() {
  const filePath = path.join(process.cwd(), "public", "data", "methodology.md");
  const content = fs.readFileSync(filePath, "utf-8");

  return (
    <>
      <Nav />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
          <MarkdownContent content={content} />
        </div>
      </main>
    </>
  );
}
