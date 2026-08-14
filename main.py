"""
M7 Cheats — Aplicação Principal

O main.py fica na raiz do projeto e todo o frontend público fica diretamente
em ./frontend/. Não utiliza Flask/Jinja templates.

Estrutura esperada:
    _m7/
    ├── main.py
    ├── db.py
    └── frontend/
        ├── index.html
        ├── login.html
        ├── register.html
        ├── account.html
        ├── admin.html
        ├── about.html
        ├── careers.html
        ├── cart.html
        ├── contact.html
        ├── help.html
        ├── partners.html
        ├── payment.html
        ├── press.html
        ├── returns.html
        ├── technical.html
        ├── track.html
        ├── warranty.html
        ├── header.html
        ├── styles.css
        ├── app.js
        └── demais assets...
"""

from datetime import datetime
import mimetypes
import os
from pathlib import Path

from flask import Flask, send_from_directory

# ============================================================================
# DIRETÓRIOS
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

# ============================================================================
# APLICAÇÃO
# ============================================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "m7-dev-key-2026",
)

# Metadados simples disponíveis para o restante da aplicação Python, caso
# sejam necessários no futuro. O HTML não depende de Jinja.
APP_NAME = "M7 Cheats"
APP_VERSION = "2.0.0"
CURRENT_YEAR = datetime.now().year

# ============================================================================
# PÁGINAS HTML
# ============================================================================

HTML_PAGES = {
    "index": "index.html",
    "about": "about.html",
    "account": "account.html",
    "admin": "admin.html",
    "careers": "careers.html",
    "cart": "cart.html",
    "contact": "contact.html",
    "help": "help.html",
    "login": "login.html",
    "register": "register.html",
    "partners": "partners.html",
    "payment": "payment.html",
    "press": "press.html",
    "returns": "returns.html",
    "technical": "technical.html",
    "track": "track.html",
    "warranty": "warranty.html",
    "header": "header.html",
}


def frontend_file(filename: str):
    """Envia um arquivo que está diretamente dentro de frontend/."""
    file_path = FRONTEND_DIR / filename

    if not file_path.is_file():
        return not_found(None)

    return send_from_directory(FRONTEND_DIR, filename)


# Página inicial -------------------------------------------------------------
@app.get("/")
def index():
    return frontend_file(HTML_PAGES["index"])


@app.get("/index")
def index_alias():
    return frontend_file(HTML_PAGES["index"])


@app.get("/index.html")
def index_html():
    return frontend_file(HTML_PAGES["index"])


# Demais páginas -------------------------------------------------------------

def make_page_route(filename: str):
    def page():
        return frontend_file(filename)
    return page


for route_name, filename in HTML_PAGES.items():
    if route_name == "index":
        continue

    # /about, /about.html, /register, /register.html, etc.
    app.add_url_rule(
        f"/{route_name}",
        endpoint=f"page_{route_name}",
        view_func=make_page_route(filename),
    )
    app.add_url_rule(
        f"/{route_name}.html",
        endpoint=f"page_{route_name}_html",
        view_func=make_page_route(filename),
    )


# ============================================================================
# ARQUIVOS DO FRONTEND
# ============================================================================

@app.get("/styles.css")
def styles_css():
    return frontend_file("styles.css")


@app.get("/app.js")
def app_js():
    return frontend_file("app.js")


@app.get("/favicon.ico")
def favicon():
    return frontend_file("favicon.ico")


@app.get("/static/<path:filename>")
def static_compat(filename: str):
    """Compatibilidade caso algum HTML antigo ainda use /static/."""
    return send_from_directory(FRONTEND_DIR, filename)


@app.get("/assets/<path:filename>")
def assets(filename: str):
    """Compatibilidade para assets como /assets/m7-hero.png."""
    return send_from_directory(FRONTEND_DIR, filename)


@app.get("/frontend/<path:filename>")
def frontend_public(filename: str):
    """Acesso direto opcional a arquivos dentro de frontend/."""
    return send_from_directory(FRONTEND_DIR, filename)


# Qualquer arquivo público diretamente dentro de frontend -------------------
@app.get("/<path:filename>")
def frontend_root_files(filename: str):
    """
    Serve arquivos diretamente de frontend/.

    Exemplos:
        /m7-hero.png
        /logo.svg
        /fonts/m7.woff2
        /images/banner.webp
    """
    # Evita que uma rota desconhecida vire acesso arbitrário fora do frontend.
    target = (FRONTEND_DIR / filename).resolve()

    try:
        target.relative_to(FRONTEND_DIR.resolve())
    except ValueError:
        return not_found(None)

    if not target.is_file():
        return not_found(None)

    return send_from_directory(target.parent, target.name)


# ============================================================================
# ERRO 404
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """404 independente de Jinja/templates."""
    not_found_file = FRONTEND_DIR / "404.html"

    if not_found_file.is_file():
        return send_from_directory(FRONTEND_DIR, "404.html"), 404

    return """<!doctype html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>M7 — 404</title>
    <style>
        body{margin:0;min-height:100vh;display:grid;place-items:center;
             background:#030811;color:#f4f8ff;font-family:Arial,sans-serif;text-align:center}
        h1{font-size:80px;margin:0;color:#0d7cff;text-shadow:0 0 24px rgba(13,124,255,.35)}
        p{color:#91a0b4}
        a{color:#0d7cff;text-decoration:none}
    </style>
</head>
<body>
    <main>
        <h1>404</h1>
        <p>A página solicitada não existe.</p>
        <a href="/">Voltar para a M7</a>
    </main>
</body>
</html>""", 404


# ============================================================================
# ERRO 500
# ============================================================================

@app.errorhandler(500)
def server_error(error):
    """500 independente de Jinja/templates."""
    error_file = FRONTEND_DIR / "500.html"

    if error_file.is_file():
        return send_from_directory(FRONTEND_DIR, "500.html"), 500

    return """<!doctype html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>M7 — Erro</title>
    <style>
        body{margin:0;min-height:100vh;display:grid;place-items:center;
             background:#030811;color:#f4f8ff;font-family:Arial,sans-serif;text-align:center}
        h1{color:#0d7cff}
        p{color:#91a0b4}
        a{color:#0d7cff;text-decoration:none}
    </style>
</head>
<body>
    <main>
        <h1>M7</h1>
        <p>Ocorreu um erro interno no servidor.</p>
        <a href="/">Voltar para a M7</a>
    </main>
</body>
</html>""", 500


# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

def start_server():
    debug_mode = os.getenv("FLASK_ENV", "development").lower() == "development"
    port = int(os.getenv("PORT", "5000"))

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                        M7 CHEATS                             ║")
    print("║                    COMMUNITY PLATFORM                      ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  URL:        http://localhost:{port:<30}║")
    print(f"║  Modo:       {'DESENVOLVIMENTO' if debug_mode else 'PRODUÇÃO':<30}║")
    print("║  Frontend:   ./frontend                                   ║")
    print("║  Templates:  DESATIVADOS                                  ║")
    print("║  Status:     ONLINE                                       ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug_mode,
        use_reloader=debug_mode,
    )


if __name__ == "__main__":
    start_server()