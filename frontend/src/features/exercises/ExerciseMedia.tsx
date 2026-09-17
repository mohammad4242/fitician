import { useState } from "react";

import type { MediaType } from "./types";
import { publicMediaPath } from "../../shared/publicMedia";

const placeholderPath = "/exercises/exercise-placeholder.svg";

type ExerciseMediaProps = {
  ambient?: boolean;
  path: string;
  name: string;
  mediaType: MediaType;
};

export function ExerciseMedia({ ambient = false, path, name, mediaType }: ExerciseMediaProps) {
  const [failed, setFailed] = useState(false);
  const alt = localizedAlt(name);
  const resolvedPath = publicMediaPath(path);

  if (mediaType === "placeholder" || failed || !resolvedPath) {
    return <img src={placeholderPath} alt={alt} />;
  }

  if (mediaType === "video") {
    return (
      <video
        src={resolvedPath}
        aria-label={alt}
        autoPlay={ambient}
        controls={!ambient}
        loop={ambient}
        muted
        playsInline
        preload="metadata"
        onError={() => setFailed(true)}
      />
    );
  }

  return <img src={resolvedPath} alt={alt} onError={() => setFailed(true)} />;
}

function localizedAlt(name: string): string {
  return /[\u0600-\u06ff]/.test(name)
    ? `نمایش حرکت ${name}`
    : `${name} demonstration`;
}
