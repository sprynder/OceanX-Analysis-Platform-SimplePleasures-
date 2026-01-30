import { NextResponse } from "next/server";
import fs from "node:fs/promises";
import path from "node:path";

const ROOTS: Record<string, string> = {
  videos: "/data/videos",
  rois: "/data/rois",
};

const MIME_TYPES: Record<string, string> = {
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
  ".gif": "image/gif",
  ".bmp": "image/bmp",
  ".tif": "image/tiff",
  ".tiff": "image/tiff",
};

export async function GET(
  _request: Request,
  context: { params: { path: string[] } }
) {
  const segments = context.params.path || [];
  if (segments.length < 2) {
    return NextResponse.json({ error: "Invalid media path" }, { status: 400 });
  }

  const [rootKey, ...relativeParts] = segments;
  const baseRoot = ROOTS[rootKey];
  if (!baseRoot) {
    return NextResponse.json({ error: "Unsupported media root" }, { status: 400 });
  }

  const resolvedRoot = path.resolve(baseRoot);
  const requestedPath = path.resolve(baseRoot, ...relativeParts);
  if (!requestedPath.startsWith(resolvedRoot)) {
    return NextResponse.json({ error: "Invalid media path" }, { status: 400 });
  }

  try {
    const file = await fs.readFile(requestedPath);
    const ext = path.extname(requestedPath).toLowerCase();
    const contentType = MIME_TYPES[ext] || "application/octet-stream";

    return new NextResponse(file, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=60",
      },
    });
  } catch (error) {
    return NextResponse.json({ error: "Media not found" }, { status: 404 });
  }
}
