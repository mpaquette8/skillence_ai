# // file: web/routes.py
"""
Routes FastAPI HTML pour le lien magique (MVP v0.2).

Ce module gère :
- la page de demande de lien,
- la génération du token (passwordless),
- le callback qui crée une session utilisateur,
- un tableau de bord minimal protégé pour valider l’auth.
"""

# Inventaire des dépendances
# - fastapi (tierce) : APIRouter, Request, HTTPException, status
# - fastapi.responses (tierce) : HTMLResponse, RedirectResponse
# - typing (stdlib) : Optional (pour l’utilisateur courant)
# - datetime (stdlib) : datetime/timezone/timedelta pour les expirations
# - secrets (stdlib) : génération de tokens URL-safe
# - hashlib (stdlib) : hash du user-agent (journalisation session)
# - logging (stdlib) : traçabilité (simule l’envoi d’e-mail)
# - urllib.parse (stdlib) : parse_qs pour lire les formulaires sans dépendance
# - storage.base (local) : get_session pour accéder à la DB
# - storage.models (local) : User, LoginToken, UserSession
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional, List
from datetime import datetime, timedelta, timezone
import secrets
import hashlib
import logging
from urllib.parse import parse_qs
import re
from html import escape

from storage.base import get_session
from storage.models import User, LoginToken, UserSession, Lesson, Request as LessonRequestModel
from api.services.lessons import create_lesson, get_lesson_by_id
from agents.lesson_generator import LessonRequest


logger = logging.getLogger("skillence_ai.web")

router = APIRouter(prefix="/web", tags=["web"])

SESSION_COOKIE_NAME = "skillence_session"
SESSION_TTL = timedelta(hours=24)
MAGIC_LINK_TTL = timedelta(minutes=15)
PAGE_SIZE = 10
BASE_STYLES = """
<style>
* { box-sizing: border-box; }
body {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f5f6fb;
  color: #1f2937;
  margin: 0;
}
a { color: #2563eb; text-decoration: none; }
a:hover { text-decoration: underline; }
header {
  background: linear-gradient(120deg, #2563eb 0%, #6366f1 100%);
  color: white;
  padding: 1.6rem;
}
.container {
  max-width: 960px;
  margin: -48px auto 32px;
  padding: 0 16px 32px;
}
.card {
  background: white;
  border-radius: 14px;
  padding: 24px;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.12);
  margin-bottom: 24px;
}
.card h2 {
  margin-top: 0;
  font-size: 1.3rem;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}
@media (max-width: 768px) {
  .grid { grid-template-columns: 1fr; }
}
.banner {
  padding: 16px 20px;
  border-radius: 12px;
  margin-bottom: 16px;
  font-weight: 500;
}
.banner.success {
  background: #dcfce7;
  color: #166534;
}
.banner.error {
  background: #fee2e2;
  color: #b91c1c;
}
form label {
  display: block;
  font-size: 0.9rem;
  margin-bottom: 4px;
  font-weight: 500;
}
form input[type="text"],
form select {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  margin-bottom: 16px;
  font-size: 1rem;
}
form button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #2563eb;
  border: none;
  color: white;
  padding: 10px 18px;
  border-radius: 999px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 10px 25px rgba(37, 99, 235, 0.25);
}
form button:hover {
  background: #1d4ed8;
}
.lesson-list ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
.lesson-list li {
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  margin-bottom: 12px;
  background: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.lesson-list small {
  color: #6b7280;
}
.markdown h1, .markdown h2, .markdown h3 { margin-top: 1.5rem; }
.markdown p { line-height: 1.6; }
.markdown ul, .markdown ol { padding-left: 1.2rem; }
.badge {
  background: #eef2ff;
  color: #4338ca;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  margin-left: 8px;
}
.metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 16px 0;
}
.metrics span {
  background: #f1f5f9;
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 0.9rem;
}
.nav-links {
  margin-top: 12px;
  font-size: 0.95rem;
}
.nav-links a {
  margin-right: 12px;
}
.muted {
  color: #6b7280;
  margin-bottom: 16px;
}
</style>
"""


def _now() -> datetime:
    """Renvoie l’instant courant en UTC."""
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime) -> datetime:
    """Garantit un datetime timezone-aware (SQLite peut renvoyer un naive)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _render_page(title: str, content: str, *, user_email: Optional[str] = None, banner: Optional[str] = None, banner_type: str = "success") -> HTMLResponse:
    """Enveloppe le contenu HTML dans un layout commun."""
    banner_html = ""
    if banner:
        banner_html = f'<div class="banner {banner_type}">{banner}</div>'

    intro = ""
    if user_email:
        intro = f"<p class=\"muted\">Bienvenue, <strong>{escape(user_email)}</strong></p>"

    html = f"""
    <html>
      <head>
        <title>{escape(title)}</title>
        <meta charset="utf-8" />
        {BASE_STYLES}
      </head>
      <body>
        <header>
          <h1>Skillence AI</h1>
          <p>Générez et explorez vos leçons pédagogiques</p>
        </header>
        <div class="container">
          {intro}
          {banner_html}
          {content}
        </div>
      </body>
    </html>
    """
    return HTMLResponse(content=html.strip())


def _render_login_page(message: Optional[str] = None) -> HTMLResponse:
    """Retourne le formulaire de login avec un message optionnel."""
    banner = message if message else None
    content = """
    <div class="card" style="max-width:520px;margin:auto;">
      <h2>Connexion / Inscription</h2>
      <p>Renseignez votre e-mail, nous vous envoyons un lien magique pour vous connecter.</p>
      <form method="POST">
        <label>E-mail :</label>
        <input type="email" name="email" required minlength="5" />
        <button type="submit">Recevoir le lien magique</button>
      </form>
      <p style="color:#6b7280;font-size:0.85rem;">
        Pour l’instant, le lien est affiché dans les logs (mode développement).
      </p>
    </div>
    """
    return _render_page("Skillence AI — Connexion", content, banner=banner)


def _send_magic_link(email: str, token: str) -> None:
    """Simule l’envoi d’un e-mail contenant le lien magique."""
    logger.info("Magic link pour %s -> /web/login/callback?token=%s", email, token)


def _resolve_user_from_session(session_id: str) -> Optional[str]:
    """Retourne l’e-mail utilisateur si la session existe et est valide."""
    with get_session() as db:
        session = (
            db.query(UserSession)
            .filter(UserSession.id == session_id)
            .first()
        )
        if session is None:
            return None

        if _as_aware(session.expires_at) <= _now():
            db.delete(session)
            return None

        email = session.user.email
    return email


@router.get("/login", response_class=HTMLResponse)
def show_login() -> HTMLResponse:
    """Affiche le formulaire de demande de lien magique."""
    return _render_login_page()


@router.post("/login", response_class=HTMLResponse)
async def request_magic_link(request: Request) -> HTMLResponse:
    """Reçoit le formulaire HTML, génère un token passwordless."""
    body = await request.body()
    form_data = parse_qs(body.decode("utf-8"))
    raw_email = form_data.get("email", [""])[0]
    normalized_email = raw_email.strip().lower()

    if "@" not in normalized_email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Adresse e-mail invalide")

    with get_session() as db:
        user = db.query(User).filter(User.email == normalized_email).first()
        if user is None:
            user = User(email=normalized_email)
            db.add(user)
            db.flush()

        token_value = secrets.token_urlsafe(24)
        login_token = LoginToken(
            user_id=user.id,
            token=token_value,
            expires_at=_now() + MAGIC_LINK_TTL,
        )
        db.add(login_token)
        # commit automatique à la sortie du contexte

    _send_magic_link(normalized_email, token_value)
    return _render_login_page("Lien envoyé ! Consultez votre boîte mail.")


@router.get("/login/callback")
def consume_magic_link(request: Request, token: str) -> RedirectResponse:
    """Consomme un token, crée la session et redirige vers le dashboard."""
    with get_session() as db:
        record = (
            db.query(LoginToken)
            .filter(LoginToken.token == token)
            .first()
        )

        if record is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Lien invalide")
        if record.redeemed_at is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Lien déjà utilisé")
        if _as_aware(record.expires_at) <= _now():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Lien expiré")

        record.redeemed_at = _now()

        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        agent_hash = hashlib.sha256(user_agent.encode("utf-8")).hexdigest()

        session = UserSession(
            user_id=record.user_id,
            expires_at=_now() + SESSION_TTL,
            ip_address=client_ip,
            user_agent_hash=agent_hash[:64],
        )
        db.add(session)
        db.flush()
        session_id = session.id
        # commit automatique à la sortie

    response = RedirectResponse(url="/web/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=False,  # à activer en production (HTTPS)
    )
    return response


def _render_markdown(text: str) -> str:
    """Convertit un sous-ensemble Markdown en HTML simple (headings + listes)."""
    if not text or text.strip() == "":
        return "<p>(contenu vide)</p>"

    html_parts: List[str] = []
    in_list = False

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            continue

        if line.startswith("### "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<h3>{escape(line[4:].strip())}</h3>")
        elif line.startswith("## "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<h2>{escape(line[3:].strip())}</h2>")
        elif line.startswith("# "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<h1>{escape(line[2:].strip())}</h1>")
        elif line.startswith("- "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{escape(line[2:].strip())}</li>")
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<p>{escape(line)}</p>")

    if in_list:
        html_parts.append("</ul>")

    return "\n".join(html_parts)


def _render_list(items: List[str], ordered: bool = False) -> str:
    """Rend une liste HTML à partir d'une liste de chaînes."""
    if not items:
        return "<p>Aucun élément.</p>"
    tag = "ol" if ordered else "ul"
    inner = "".join(f"<li>{escape(item)}</li>" for item in items)
    return f"<{tag}>{inner}</{tag}>"


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    """Page protégée minimale : confirme que l’utilisateur est connecté."""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    user_email = _resolve_user_from_session(session_id) if session_id else None
    if not session_id or user_email is None:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_303_SEE_OTHER)

    message = request.query_params.get("message")
    banner = None
    banner_type = "success"
    if message == "lesson_created":
        banner = "Leçon générée avec succès."
    elif message == "error":
        banner = "Erreur lors de la génération. Consultez les logs."
        banner_type = "error"

    page_param = request.query_params.get("page", "1")
    try:
        page = max(int(page_param), 1)
    except ValueError:
        page = 1
    offset = (page - 1) * PAGE_SIZE

    lessons_data = []
    total_count = 0
    with get_session() as db:
        total_count = db.query(Lesson).count()
        rows = (
            db.query(Lesson, LessonRequestModel)
            .join(LessonRequestModel, Lesson.request_id == LessonRequestModel.id)
            .order_by(Lesson.created_at.desc())
            .offset(offset)
            .limit(10)
            .all()
        )
        for lesson, req in rows:
            lessons_data.append(
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "audience": req.audience,
                    "created_at": lesson.created_at.strftime("%Y-%m-%d %H:%M"),
                    "duration": req.duration,
                }
            )

    lesson_cards = []

    if lessons_data:
        for entry in lessons_data:
            lesson_cards.append(
                f"""
                <li>
                  <div>
                    <a href="/web/lessons/{entry['id']}"><strong>{escape(entry['title'])}</strong></a>
                    <div><small>{escape(entry['audience'])} · {escape(entry['duration'])}</small></div>
                  </div>
                  <small>{escape(entry['created_at'])}</small>
                </li>
                """
            )
        lesson_list = "<ul>" + "".join(lesson_cards) + "</ul>"
    else:
        lesson_list = "<p>Aucune leçon disponible pour le moment.</p>"

    nav_links: List[str] = []
    if page > 1:
        nav_links.append(f'<a href="/web/dashboard?page={page - 1}">Page précédente</a>')
    if offset + PAGE_SIZE < total_count:
        nav_links.append(f'<a href="/web/dashboard?page={page + 1}">Voir plus</a>')
    navigation = " | ".join(nav_links)

    content = f"""
      <div class="grid">
        <div class="card">
          <h2>Générer une nouvelle leçon</h2>
          <form method="POST" action="/web/dashboard">
            <label>Sujet</label>
            <input type="text" name="subject" required minlength="2" maxlength="200"/>

            <label>Audience</label>
            <select name="audience">
              <option value="enfant">enfant</option>
              <option value="lycéen">lycéen</option>
              <option value="adulte">adulte</option>
            </select>

            <label>Durée</label>
            <select name="duration">
              <option value="short">short</option>
              <option value="medium">medium</option>
              <option value="long">long</option>
            </select>

            <button type="submit">⚡ Générer</button>
          </form>
        </div>

        <div class="card lesson-list">
          <h2>Dernières leçons</h2>
          {lesson_list}
          <div class="nav-links">{navigation}</div>
        </div>
      </div>
    """
    return _render_page("Skillence AI — Tableau de bord", content, user_email=user_email, banner=banner, banner_type=banner_type)


@router.post("/dashboard", response_class=HTMLResponse)
async def dashboard_generate(request: Request) -> HTMLResponse:
    """Traite le formulaire de génération et redirige vers le dashboard."""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    user_email = _resolve_user_from_session(session_id) if session_id else None
    if not session_id or user_email is None:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_303_SEE_OTHER)

    body = await request.body()
    data = parse_qs(body.decode("utf-8"))
    subject = (data.get("subject") or [""])[0].strip()
    audience = (data.get("audience") or [""])[0]
    duration = (data.get("duration") or [""])[0]

    try:
        payload = LessonRequest(subject=subject, audience=audience, duration=duration)
        create_lesson(payload)
    except Exception as exc:  # pragma: no cover - catch-all to redirect user
        logger.error("Erreur génération dashboard: %s", exc)
        return RedirectResponse(
            url="/web/dashboard?message=error",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return RedirectResponse(
        url="/web/dashboard?message=lesson_created",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/lessons/{lesson_id}", response_class=HTMLResponse)
def lesson_detail(request: Request, lesson_id: str) -> HTMLResponse:
    """Affiche le contenu Markdown et les métriques pour une leçon donnée."""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    user_email = _resolve_user_from_session(session_id) if session_id else None
    if not session_id or user_email is None:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_303_SEE_OTHER)

    lesson_data = get_lesson_by_id(lesson_id)
    if lesson_data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Leçon introuvable")

    readability = lesson_data.get("quality", {}).get("readability", {})
    content_html = _render_markdown(lesson_data.get("content", ""))
    objectives_html = _render_list(lesson_data.get("objectives") or [])
    plan_html = _render_list(lesson_data.get("plan") or [], ordered=True)

    content = f"""
      <div class="card">
        <p><a href="/web/dashboard">← Retour au tableau de bord</a></p>
        <h1>{escape(lesson_data['title'])} <span class="badge">{escape(lesson_data.get('quality', {}).get('readability', {}).get('audience_target', ''))}</span></h1>
        <div class="metrics">
          <span>Score FK : {readability.get('flesch_kincaid_score', 'N/A')}</span>
          <span>Niveau : {readability.get('readability_level', 'N/A')}</span>
          <span>Message : {readability.get('quality_message', 'N/A')}</span>
        </div>
        <section>
          <h2>Objectifs</h2>
          {objectives_html}
        </section>
        <section>
          <h2>Plan</h2>
          {plan_html}
        </section>
        <section class="markdown">
          <h2>Contenu</h2>
          {content_html}
        </section>
      </div>
    """
    return _render_page(f"Skillence AI — {lesson_data['title']}", content, user_email=user_email)
