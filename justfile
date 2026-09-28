port := "5733"
repo_url := "https://github.com/JCPetrelli/brickwise"
pages_url := "https://jcpetrelli.github.io/brickwise"

# Serve the gallery of builds and open it
run:
    #!/usr/bin/env bash
    dir="$(python3 -c 'from brickwise.build import default_builds_dir; print(default_builds_dir())')"
    mkdir -p "$dir"
    [ -f "$dir/index.html" ] || python3 -c "from brickwise.gallery import write_gallery; write_gallery('$dir')"
    (sleep 1; open "http://localhost:{{port}}/index.html" 2>/dev/null || xdg-open "http://localhost:{{port}}/index.html") &
    python3 -m http.server {{port}} --directory "$dir"

# Validate a spec and build its page into the builds folder
build SPEC:
    python3 -m brickwise.build {{SPEC}} --open

# Rebuild the committed example pages from examples/*.json
examples:
    for f in examples/*.json; do python3 -m brickwise.build "$f" --html "${f%.json}.html" --source-link {{repo_url}} --og-image {{pages_url}}/docs/images/social-preview.png; done
    python3 -c "from brickwise.gallery import write_gallery; write_gallery('examples', title='Brickwise examples', og_image='{{pages_url}}/docs/images/social-preview.png')"

# Link the skill into ~/.claude/skills (manual install without the plugin system)
install:
    mkdir -p ~/.claude/skills
    ln -sfn "$(pwd)/skills/brickwise" ~/.claude/skills/brickwise
    @echo "Installed: ~/.claude/skills/brickwise -> $(pwd)/skills/brickwise"

test:
    python3 -m pytest -q

# Headless-Chrome check of a page: hover, popup, both explode stages
smoke HTML PIECE:
    cd tests/smoke && [ -d node_modules ] || npm install --silent
    mkdir -p tests/smoke/shots
    node tests/smoke/smoke.mjs "$(realpath {{HTML}})" tests/smoke/shots/shot {{PIECE}}
