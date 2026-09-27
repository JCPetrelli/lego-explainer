port := "5733"

# Serve the gallery of builds and open it
run:
    open "http://localhost:{{port}}/index.html" &
    python3 -m http.server {{port}} --directory builds

# Validate a spec and build its HTML
build SPEC:
    python3 -m lego_explainer.build {{SPEC}} --open

test:
    python3 -m pytest -q

# Headless-Chrome check of a built page: hover, popup, both explode stages
smoke HTML PIECE:
    cd tests/smoke && [ -d node_modules ] || npm install --silent
    mkdir -p tests/smoke/shots
    node tests/smoke/smoke.mjs "$(realpath {{HTML}})" tests/smoke/shots/shot {{PIECE}}
