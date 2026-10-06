import { useState } from "react";

import type { MediaType } from "./types";
import { publicMediaPath } from "../../shared/publicMedia";

const placeholderPath = "/exercises/exercise-placeholder.svg";

type ExerciseMediaProps = {
  ambient?: boolean;
  lazy?: boolean;
  path: string;
  name: string;
  mediaType: MediaType;
};

export function ExerciseMedia({ ambient = false, lazy = false, path, name, mediaType }: ExerciseMediaProps) {
  const [failed, setFailed] = useState(false);
  const alt = localizedAlt(name);
  const resolvedPath = publicMediaPath(path);
  const posterPath = mediaType === "video" ? exerciseVideoPosterPath(path) : null;
  const resolvedPosterPath = posterPath === null ? undefined : publicMediaPath(posterPath);

  if (mediaType === "placeholder" || failed || !resolvedPath) {
    return <img src={placeholderPath} alt={alt} />;
  }

  if (mediaType === "video") {
    return (
      <video
        src={resolvedPath}
        poster={resolvedPosterPath}
        aria-label={alt}
        autoPlay={ambient}
        controls={!ambient}
        loop={ambient}
        muted
        playsInline
        preload={lazy ? "none" : "metadata"}
        onError={() => setFailed(true)}
      />
    );
  }

  return <img loading={lazy ? "lazy" : undefined} src={resolvedPath} alt={alt} onError={() => setFailed(true)} />;
}

function exerciseVideoPosterPath(path: string): string | null {
  if (!path.startsWith("/media/exercises/") && !path.startsWith("/exercises/")) return null;
  if (!/\.(?:mp4|webm)$/iu.test(path)) return null;
  return path.replace(/\.(?:mp4|webm)$/iu, ".poster.webp");
}

function localizedAlt(name: string): string {
  return /[\u0600-\u06ff]/.test(name)
    ? `نمایش حرکت ${name}`
    : `${name} demonstration`;
}
