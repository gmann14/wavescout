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
  const content = fs.existsSync(filePath)
    ? fs.readFileSync(filePath, "utf-8")
    : null;

  return (
    <>
      <Nav />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
          {content ? (
            <MarkdownContent content={content} />
          ) : (
            <div className="rounded-xl border border-navy-700 bg-navy-900 px-6 py-10 text-center text-slate-300">
              Methodology content is unavailable in this build.
            </div>
          )}
        </div>
      </main>
    </>
  );
}
