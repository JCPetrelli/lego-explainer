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
