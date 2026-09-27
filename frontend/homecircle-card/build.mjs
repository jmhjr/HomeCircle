import { build } from "esbuild";
import { mkdir, copyFile } from "node:fs/promises";
const output = new URL(
  "../../custom_components/homecircle/frontend/",
  import.meta.url,
);
await mkdir(output, { recursive: true });
await build({
  entryPoints: [new URL("src/card.js", import.meta.url).pathname],
  bundle: true,
  format: "esm",
  target: "es2022",
  minify: true,
  loader: { ".css": "text" },
  outfile: new URL("homecircle-card.js", output).pathname,
  legalComments: "eof",
});
await copyFile(
  new URL("node_modules/leaflet/LICENSE", import.meta.url),
  new URL("LEAFLET-LICENSE.txt", output),
);
console.log("Built local HomeCircle card and Leaflet license.");
