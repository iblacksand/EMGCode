package:
    cd web && bun run build
    cd web && rm -rf ../server/build && mv build ../server
    cd server && ouch c -y main.py build requirements.txt web.zip
