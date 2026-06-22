package:
    cd web && bun run build
    cd web && mv build ../server
    cd server && ouch c -y main.py build requirements.txt web.zip
    cd server && rm -rf build
