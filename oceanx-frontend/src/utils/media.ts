export const toMediaUrl = (input?: string | null): string => {
  if (!input) return "";
  const normalized = input.replace(/\\/g, "/");
  // Convert backend paths to nginx media URLs (absolute URLs through nginx)
  const mediaBase =
    process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost";
  if (normalized.startsWith("/data/videos/")) {
    return `${mediaBase}/media/videos/${normalized.replace("/data/videos/", "")}`;
  }
  if (normalized.startsWith("/rois/")) {
    return `${mediaBase}/media/rois/${normalized.replace("/rois/", "")}`;
  }
  return normalized;
};
