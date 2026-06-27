package:
    cd web && bun run build
    cd web && rm -rf ../server/build && mv build ../server
    cd server && ouch c -y src/ build pyproject.toml web.zip
