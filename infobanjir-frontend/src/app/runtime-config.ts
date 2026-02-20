type RuntimeEnv = {
  API_URL?: string;
};

type RuntimeWindow = Window & {
  __HYDROINTEL_ENV__?: RuntimeEnv;
};

const runtimeWindow = window as RuntimeWindow;
const runtimeEnv = runtimeWindow.__HYDROINTEL_ENV__ ?? {};

export const runtimeConfig = {
  apiUrl: runtimeEnv.API_URL?.trim() || "http://localhost:8081/api/ask",
};

