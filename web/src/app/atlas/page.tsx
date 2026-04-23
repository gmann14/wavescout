import { redirect } from "next/navigation";

export const metadata = {
  title: "Section Analysis — WaveScout",
  description:
    "Open the main discovery map with section analysis enabled.",
};

export default function AtlasPage() {
  redirect("/?analysis=atlas");
}
