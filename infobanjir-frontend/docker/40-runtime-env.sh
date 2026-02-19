#!/bin/sh
set -eu

cat > /usr/share/nginx/html/assets/env.js <<EOF
window.__HYDROINTEL_ENV__ = {
  API_URL: "${API_BASE_URL:-/api/ask}"
};
EOF

