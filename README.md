# Course Template

A template repository for courses built with [Quarto](https://quarto.org/) books and
Jupyter notebooks, using [uv](https://docs.astral.sh/uv/) for Python dependency
management and GitHub Actions for CI build checks and GitHub Pages publishing.

## Using this template

1. Click "Use this template" on GitHub to create a new repository from this one.
2. Update `_variables.yml` with the new repository's URL and GitHub links.
3. Update `_quarto.yml` (title, author) and `pyproject.toml` / `environment.yml`
   (project name).
4. Add course notebooks/`.qmd` chapters and list them under `book.chapters` in
   `_quarto.yml`.
5. Run `uv sync` to install dependencies, then `uv run quarto render .` to build
   locally.

## Structure

- `index.qmd` — book landing page.
- `_quarto.yml` — Quarto book configuration.
- `_variables.yml` — reusable Quarto variables (site URL, repo links).
- `references.qmd` / `references.bib` — bibliography.
- `.github/workflows/pr-build.yml` — renders the book on every PR to `main` as a build check.
- `.github/workflows/publish.yml` — renders and publishes the book to GitHub Pages on push to `main`.
- `pyproject.toml` / `environment.yml` — Python dependencies (uv / conda).
