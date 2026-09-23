const isDevelopment = process.env.APP_VARIANT === "development";

export default {
  dependencies: {
    "expo-dev-client": isDevelopment
      ? {}
      : {
          platforms: {
            android: null,
            ios: null,
          },
        },
  },
};
