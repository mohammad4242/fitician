import Svg, { Path } from "react-native-svg";

export interface GoogleBrandIconProps {
  readonly size?: number;
  readonly testID?: string;
}

export function GoogleBrandIcon({ size = 20, testID }: GoogleBrandIconProps) {
  return (
    <Svg accessible={false} height={size} testID={testID} viewBox="0 0 24 24" width={size}>
      <Path
        d="M21.35 12.27c0-.78-.07-1.54-.23-2.27H12v4.3h5.23a4.5 4.5 0 0 1-1.94 2.96v2.46h3.14c1.84-1.69 2.92-4.18 2.92-7.45Z"
        fill="#4285F4"
      />
      <Path
        d="M12 21.5c2.63 0 4.84-.87 6.45-2.35l-3.14-2.46c-.87.58-1.98.93-3.31.93-2.54 0-4.69-1.72-5.46-4.04H3.3v2.54A9.74 9.74 0 0 0 12 21.5Z"
        fill="#34A853"
      />
      <Path
        d="M6.54 13.58A5.86 5.86 0 0 1 6.23 12c0-.55.11-1.08.31-1.58V7.88H3.3A9.5 9.5 0 0 0 2.5 12c0 1.49.36 2.9.8 4.12l3.24-2.54Z"
        fill="#FBBC05"
      />
      <Path
        d="M12 6.38c1.43 0 2.71.49 3.72 1.45l2.79-2.79C16.84 3.44 14.63 2.5 12 2.5a9.74 9.74 0 0 0-8.7 5.38l3.24 2.54C7.31 8.1 9.46 6.38 12 6.38Z"
        fill="#EA4335"
      />
    </Svg>
  );
}
