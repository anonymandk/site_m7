from fastapi import FastAPI, Depends, HTTPException, Header, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import hashlib
import os
import random
from urllib.parse import parse_qs, urlparse


from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.staticfiles import StaticFiles

import db
from db import (
    Product, Coupon, User, UserSession, Order, OrderItem, SessionLocal
)

app = FastAPI(title="NovaShop API", version="2.0")

# --- Rate Limiting ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Configuração de CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Serve static assets (images, css, etc.)
# Prefer `frontend/static` when present, otherwise fall back to root `static/`.
base_dir = os.path.dirname(__file__)
frontend_static_dir = os.path.join(base_dir, 'frontend', 'static')
default_static_dir = os.path.join(base_dir, 'static')
static_dir = frontend_static_dir if os.path.isdir(frontend_static_dir) else default_static_dir
if os.path.isdir(static_dir):
    app.mount('/static', StaticFiles(directory=static_dir), name='static')

# Serve frontend HTML files (index.html, about.html, cart.html, etc.)
frontend_dir = os.path.join(base_dir, 'frontend')
if os.path.isdir(frontend_dir):
    app.mount('/', StaticFiles(directory=frontend_dir, html=True), name='frontend')

# --- Constantes ---
FREE_SHIPPING_MIN = 199
ACCESS_TOKEN_TTL = 15 * 60  # 15 minutos
REFRESH_TOKEN_TTL = 7 * 24 * 60 * 60  # 7 dias

# --- Dados em Memória (produtos, cupons, etc.) ---
PRODUCTS_DATA = [
    {
        "id": 1,
        "name": "NEXUS Watch Pro X",
        "description": "Smartwatch de última geração com display holográfico, processador IA integrado, monitoramento cardíaco 24/7 e 14 dias de bateria.",
        "price": 2497.00,
        "original_price": 3299.00,
        "category": "SMARTWATCH",
        "emoji": "⌚",
        "sold": 847,
        "rating": 4.9,
        "reviews": 847,
        "stock": 15,
        "tags": ["novo", "premium", "frete gratis"],
    },
    {
        "id": 2,
        "name": "AirPulse Neural Pro",
        "description": "Earbuds com cancelamento ativo neural, IA de equalização adaptativa, 48h de bateria com case. Som hi-fi studio quality.",
        "price": 1189.00,
        "original_price": 1599.00,
        "category": "EARBUDS",
        "emoji": "🎧",
        "sold": 2341,
        "rating": 4.8,
        "reviews": 2341,
        "stock": 42,
        "tags": ["top", "mais vendido", "frete gratis"],
    },
    {
        "id": 3,
        "name": "HoloLens Vision 4",
        "description": "Headset AR avançado com display holográfico 4K, rastreamento ocular em 360°, processador quantum-ready, compatível com Windows.",
        "price": 8990.00,
        "original_price": 11500.00,
        "category": "AR HEADSET",
        "emoji": "🥽",
        "sold": 312,
        "rating": 4.9,
        "reviews": 312,
        "stock": 8,
        "tags": ["limited edition", "tecnologia"],
    },
    {
        "id": 4,
        "name": "QuantumPad Ultra",
        "description": "Tablet OLED 12.9\" com processador ARM v9, 16GB RAM, 1TB SSD. Compatível com stylus neural e teclado magnético.",
        "price": 4799.00,
        "original_price": 5999.00,
        "category": "TABLET",
        "emoji": "📱",
        "sold": 1203,
        "rating": 4.7,
        "reviews": 1203,
        "stock": 22,
        "tags": ["premium", "frete gratis"],
    },
    {
        "id": 5,
        "name": "FusionKey Mech Pro",
        "description": "Teclado mecânico RGB com switches hot-swap, design ergonômico, conectividade tri-modo (USB-C, 2.4GHz, Bluetooth). Ideal para gamers.",
        "price": 1890.00,
        "original_price": 2499.00,
        "category": "TECLADO",
        "emoji": "⌨️",
        "sold": 756,
        "rating": 4.8,
        "reviews": 756,
        "stock": 35,
        "tags": ["gamer", "limited edition"],
    },
    {
        "id": 6,
        "name": "NeuroLink Band 3",
        "description": "Pulseira biométrica com sensor IA, rastreia 50+ métricas de saúde, processamento neural local, bateria 30 dias. Compatível com iOS/Android.",
        "price": 3299.00,
        "original_price": 4199.00,
        "category": "BIOMÉTRICO",
        "emoji": "💪",
        "sold": 589,
        "rating": 4.9,
        "reviews": 589,
        "stock": 28,
        "tags": ["ia integrada", "saúde"],
    }
]

COUPONS_DATA = {
    "NOVA10": {"discount": 10, "type": "percent", "min_value": 50, "label": "10% OFF"},
    "NOVA20": {"discount": 20, "type": "percent", "min_value": 100, "label": "20% OFF"},
    "FRETE5": {"discount": 5, "type": "fixed", "min_value": 30, "label": "R$ 5 OFF"},
    "PRIMEIRACOMPRA": {"discount": 15, "type": "percent", "min_value": 80, "label": "15% OFF primeira compra"},
}

QUIZ_QUESTIONS = [
    {
        "id": 1,
        "prompt": "Qual dos seguintes é um tipo de dado primitivo em Python?",
        "options": ["Lista", "Dicionário", "Inteiro", "Classe"],
        "correct_index": 2,
        "explanation": "O tipo inteiro (int) é um tipo primitivo em Python.",
    },
    {
        "id": 2,
        "prompt": "O que significa HTML em desenvolvimento web?",
        "options": ["HyperText Markup Language", "HighText Markdown Language", "Hyperlink Media Language", "HyperText Making Language"],
        "correct_index": 0,
        "explanation": "HTML significa HyperText Markup Language.",
    },
]

LEARNING_TIPS = [
    "Quebre problemas grandes em etapas menores antes de codificar.",
    "Comente seu código com clareza para lembrar por que cada parte existe.",
    "Use o console do navegador para inspecionar variáveis em JavaScript rapidamente.",
    "Pratique algoritmos pequenos diariamente para fortalecer lógica de programação.",
    "Sempre teste seu código com casos extremos para evitar bugs inesperados.",
]

SHIPPING_TABLE = [
    (1, 19999, "SP", 12.90, 3),
    (20000, 23999, "RJ", 14.90, 5),
    (30000, 39999, "MG", 16.90, 6),
    (40000, 48999, "BA", 18.90, 8),
    (50000, 57999, "PE", 19.90, 9),
    (60000, 63999, "CE", 21.90, 10),
    (70000, 73999, "DF", 15.90, 5),
    (80000, 88999, "PR", 17.90, 7),
    (90000, 99999, "RS", 19.90, 8),
    (0, 99999, "OUTROS", 22.90, 10),
]

# --- Helpers ---

def hash_password(password: str) -> str:
    """Gera hash SHA256 da senha."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica se a senha corresponde ao hash."""
    return hash_password(password) == password_hash


def generate_token() -> str:
    """Gera token aleatório."""
    return hashlib.sha256(os.urandom(32)).hexdigest()


def calc_shipping(zip_code: str) -> tuple:
    """Calcula frete baseado no CEP. Retorna (valor, prazo_dias, estado)."""
    try:
        cep_num = int(zip_code.replace("-", "").replace(" ", ""))
    except (ValueError, AttributeError):
        return 22.90, 10, "OUTROS"

    for start, end, state, price, days in SHIPPING_TABLE:
        if start <= cep_num <= end:
            return price, days, state

    return 22.90, 10, "OUTROS"


def generate_pix_code() -> str:
    """Gera um código PIX simulado."""
    payload = f"00020126580014br.gov.bcb.pix0136{os.urandom(16).hex()}52040000530398654"
    total = "05.00"
    payload += f"{total}5802BR5913NOVASHOP6009SAO PAULO62070503***6304"
    checksum = hashlib.md5(payload.encode()).hexdigest()[:4].upper()
    return payload + checksum


def get_current_user(
    authorization: Optional[str] = Header(None),
    session: Session = Depends(db.get_db)
) -> Optional[dict]:
    """Extrai usuário do token Bearer."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.split(" ", 1)[1]
    user_session = session.query(UserSession).filter_by(
        access_token=token, revoked=False
    ).first()
    
    if not user_session or not user_session.access_expires_at:
        return None
    
    if user_session.access_expires_at < datetime.now():
        return None
    
    user = user_session.user
    if not user:
        return None
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "cpf": user.cpf,
        "address": user.address,
        "is_admin": bool(user.is_admin),
        "session_id": user_session.id,
    }


def sanitize_user(user) -> dict:
    """Remove informações sensíveis do usuário."""
    if isinstance(user, dict):
        return {k: v for k, v in user.items() if k != "password_hash"}
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "cpf": user.cpf,
        "address": user.address,
        "is_admin": bool(user.is_admin),
    }


# --- Rotas de Produtos ---

@app.get("/api/products")
@limiter.limit("60/minute")
def list_products(request: Request, q: Optional[str] = None, session: Session = Depends(db.get_db)):
    """Lista todos os produtos com categorias, com suporte a busca."""
    query = session.query(Product)
    if q:
        from sqlalchemy import or_
        query = query.filter(or_(Product.name.ilike(f"%{q}%"), Product.description.ilike(f"%{q}%")))

    products = query.all()
    products_list = []
    for p in products:
        # prefer a per-product static file, fall back to default image
        product_img_path = os.path.join(static_dir, 'images', 'products', f"{p.id}.svg") if 'static' in globals() else None
        if product_img_path and os.path.exists(product_img_path):
            img_url = request.url_for('static', path=f'images/products/{p.id}.svg')
        else:
            # default placeholder
            img_url = request.url_for('static', path='images/products/default.svg') if os.path.exists(os.path.join(static_dir, 'images', 'products', 'default.svg')) else f"/static/images/products/{p.id}.svg"

        products_list.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price": p.price,
            "original_price": p.original_price,
            "category": p.category,
            "emoji": p.emoji,
            "sold": p.sold,
            "rating": p.rating,
            "reviews": p.reviews,
            "stock": p.stock,
            "tags": p.tags or [],
            "image": img_url,
        })
    categories = sorted(set(p["category"] for p in products_list if p.get("category")))
    return {"products": products_list, "categories": categories}


@app.get('/api/users')
def list_users(request: Request, session: Session = Depends(db.get_db)):
    """Lista usuários com foto de perfil."""
    users = session.query(User).all()
    out = []
    for u in users:
        profile_path = os.path.join(static_dir, 'images', 'profiles', f"{u.id}.svg")
        if os.path.exists(profile_path):
            photo = request.url_for('static', path=f'images/profiles/{u.id}.svg')
        else:
            photo = request.url_for('static', path='images/profiles/default.svg') if os.path.exists(os.path.join(static_dir, 'images', 'profiles', 'default.svg')) else f"/static/images/profiles/{u.id}.svg"
        out.append({
            'id': u.id,
            'name': u.name,
            'email': u.email,
            'is_admin': bool(u.is_admin),
            'photo': photo,
        })
    return {'users': out}


@app.get("/api/products/{product_id}")
@limiter.limit("60/minute")
def get_product(request: Request, product_id: int, session: Session = Depends(db.get_db)):
    """Retorna detalhes de um produto específico."""
    product = session.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "original_price": product.original_price,
        "category": product.category,
        "emoji": product.emoji,
        "sold": product.sold,
        "rating": product.rating,
        "reviews": product.reviews,
        "stock": product.stock,
        "tags": product.tags or [],
    }


# --- Rotas de Autenticação ---

@app.post("/api/register", status_code=201)
@limiter.limit("5/minute")
def register(request: Request, data: dict, session: Session = Depends(db.get_db)):
    """Registra novo usuário."""
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")
    cpf = (data.get("cpf") or "").strip()
    address = (data.get("address") or "").strip()

    if not all([name, email, password, cpf, address]):
        raise HTTPException(status_code=400, detail="Preencha todos os campos")

    if session.query(User).filter_by(email=email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        cpf=cpf,
        address=address,
    )
    session.add(user)
    session.flush()

    # Cria sessão imediata
    now = datetime.now()
    user_session = UserSession(
        user_id=user.id,
        access_token=generate_token(),
        refresh_token=generate_token(),
        access_expires_at=now + timedelta(seconds=ACCESS_TOKEN_TTL),
        refresh_expires_at=now + timedelta(seconds=REFRESH_TOKEN_TTL),
        revoked=False,
    )
    session.add(user_session)
    session.commit()

    return {
        "access_token": user_session.access_token,
        "refresh_token": user_session.refresh_token,
        "user": sanitize_user(user),
    }


@app.post("/api/login")
@limiter.limit("5/minute")
def login(request: Request, data: dict, session: Session = Depends(db.get_db)):
    """Autentica usuário e cria sessão."""
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="E-mail e senha são obrigatórios")

    user = session.query(User).filter_by(email=email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    now = datetime.now()
    user_session = UserSession(
        user_id=user.id,
        access_token=generate_token(),
        refresh_token=generate_token(),
        access_expires_at=now + timedelta(seconds=ACCESS_TOKEN_TTL),
        refresh_expires_at=now + timedelta(seconds=REFRESH_TOKEN_TTL),
        revoked=False,
    )
    session.add(user_session)
    session.commit()

    return {
        "access_token": user_session.access_token,
        "refresh_token": user_session.refresh_token,
        "user": sanitize_user(user),
    }


@app.post("/api/logout")
def logout(
    user: dict = Depends(get_current_user),
    session: Session = Depends(db.get_db)
):
    """Revoga sessão do usuário."""
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")

    user_session = session.query(UserSession).get(user["session_id"])
    if user_session:
        user_session.revoked = True
        session.commit()

    return {"message": "Logout efetuado"}


@app.post("/api/refresh")
def refresh(data: dict, session: Session = Depends(db.get_db)):
    """Renova tokens de autenticação."""
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token obrigatório")

    user_session = session.query(UserSession).filter_by(
        refresh_token=refresh_token, revoked=False
    ).first()

    if not user_session or not user_session.refresh_expires_at:
        raise HTTPException(status_code=401, detail="Token de atualização inválido")

    if user_session.refresh_expires_at < datetime.now():
        raise HTTPException(status_code=401, detail="Token expirado")

    user = user_session.user
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido")

    # Revoga token antigo e cria novo
    user_session.revoked = True
    session.commit()

    now = datetime.now()
    new_session = UserSession(
        user_id=user.id,
        access_token=generate_token(),
        refresh_token=generate_token(),
        access_expires_at=now + timedelta(seconds=ACCESS_TOKEN_TTL),
        refresh_expires_at=now + timedelta(seconds=REFRESH_TOKEN_TTL),
        revoked=False,
    )
    session.add(new_session)
    session.commit()

    return {
        "access_token": new_session.access_token,
        "refresh_token": new_session.refresh_token,
        "user": sanitize_user(user),
    }


# --- Rotas de Usuário ---

@app.get("/api/me")
def me(user: dict = Depends(get_current_user)):
    """Retorna dados do usuário autenticado."""
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return {"user": user}


@app.get("/api/my-orders")
def get_my_orders(user: dict = Depends(get_current_user), session: Session = Depends(db.get_db)):
    """Retorna o histórico de pedidos do usuário autenticado."""
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")

    orders = session.query(Order).filter(
        (Order.customer_email == user["email"]) | (Order.customer_cpf == user["cpf"])
    ).order_by(Order.created_at.desc()).all()

    return {
        "orders": [
            {
                "id": o.id,
                "total": o.total,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            } for o in orders
        ]
    }


@app.get("/api/cart")
def get_cart(user: dict = Depends(get_current_user), session: Session = Depends(db.get_db)):
    """Retorna os itens do carrinho do usuário."""
    if not user:
        raise HTTPException(status_code=401, detail="Sessão expirada")

    items = session.query(db.CartItem).filter_by(user_id=user["id"]).all()
    products_map = {p.id: p for p in session.query(Product).all()}

    return {
        "items": [
            {
                "id": it.product_id,
                "name": products_map.get(it.product_id).name if products_map.get(it.product_id) else "Produto removido",
                "price": products_map.get(it.product_id).price if products_map.get(it.product_id) else 0,
                "qty": it.quantity,
            } for it in items
        ]
    }


@app.post("/api/cart")
def add_to_cart(data: dict, user: dict = Depends(get_current_user), session: Session = Depends(db.get_db)):
    """Adiciona ou atualiza item no carrinho do banco."""
    if not user:
        raise HTTPException(status_code=401, detail="Sessão expirada")

    product_id = data.get("id")
    qty = data.get("qty", 1)
    if not product_id:
        raise HTTPException(status_code=400, detail="ID do produto é obrigatório")

    item = session.query(db.CartItem).filter_by(user_id=user["id"], product_id=product_id).first()
    if item:
        item.quantity += qty
    else:
        item = db.CartItem(user_id=user["id"], product_id=product_id, quantity=qty)
        session.add(item)

    session.commit()
    return {"message": "Carrinho atualizado"}


@app.delete("/api/cart/{product_id}")
def remove_from_cart(product_id: int, user: dict = Depends(get_current_user), session: Session = Depends(db.get_db)):
    """Remove item do carrinho."""
    if not user:
        raise HTTPException(status_code=401, detail="Sessão expirada")

    item = session.query(db.CartItem).filter_by(user_id=user["id"], product_id=product_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado no carrinho")

    session.delete(item)
    session.commit()
    return {"message": "Item removido"}


# --- Rotas de Frete e Cupons ---

@app.get("/api/shipping")
@limiter.limit("60/minute")
def get_shipping(request: Request, zip: str = "", subtotal: float = 0.0):
    """Calcula frete baseado no CEP."""
    price, days, state = calc_shipping(zip)
    free = subtotal >= FREE_SHIPPING_MIN

    return {
        "price": 0.0 if free else price,
        "original_price": price,
        "days": days,
        "state": state,
        "free_shipping_eligible": free,
    }


@app.get("/api/coupons")
@limiter.limit("60/minute")
def validate_coupon(request: Request, code: str = "", subtotal: float = 0.0, session: Session = Depends(db.get_db)):
    """Valida cupom de desconto."""
    code = code.upper()

    if not code:
        raise HTTPException(status_code=400, detail="Cupom não informado")

    cp = session.query(Coupon).filter_by(code=code).first()
    if not cp:
        raise HTTPException(status_code=400, detail="Cupom inválido")

    if subtotal < cp.min_value:
        raise HTTPException(
            status_code=400,
            detail=f"Compra mínima: R$ {cp.min_value:.2f}"
        )

    return {
        "valid": True,
        "coupon": {
            "code": cp.code,
            "discount": cp.discount,
            "type": cp.type,
            "min_value": cp.min_value,
            "label": cp.label,
        },
    }


# --- Rotas de Dicas e Quiz ---

@app.get("/api/tips")
def get_tip():
    """Retorna uma dica de aprendizado aleatória."""
    return {"tip": random.choice(LEARNING_TIPS)}


@app.get("/api/quiz")
def get_quiz_question():
    """Retorna uma pergunta do quiz."""
    question = random.choice(QUIZ_QUESTIONS)
    return {
        "question": {
            "id": question["id"],
            "prompt": question["prompt"],
            "options": question["options"],
        }
    }


@app.post("/api/quiz/answer")
def answer_quiz(data: dict):
    """Valida resposta do quiz."""
    question_id = data.get("question_id")
    selected = data.get("selected")

    if question_id is None or selected is None:
        raise HTTPException(status_code=400, detail="Question ID e resposta são obrigatórios")

    question = next((q for q in QUIZ_QUESTIONS if q["id"] == question_id), None)
    if not question:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")

    return {
        "correct": selected == question["correct_index"],
        "correct_index": question["correct_index"],
        "explanation": question["explanation"],
    }


# --- Rotas de Pedidos ---

@app.post("/api/orders", status_code=201)
@limiter.limit("10/minute")
def create_order(
    request: Request,
    data: dict,
    user: dict = Depends(get_current_user),
    session: Session = Depends(db.get_db)
):
    """Cria novo pedido."""
    if not user:
        raise HTTPException(status_code=401, detail="Autenticação necessária")

    if not data or "items" not in data:
        raise HTTPException(status_code=400, detail="Dados inválidos")

    customer_zip = data.get("customer", {}).get("zip", "")

    items = []
    subtotal_items = 0

    for item in data["items"]:
        prod = session.query(Product).get(item["id"])
        if not prod:
            raise HTTPException(status_code=400, detail=f"Produto {item['id']} não encontrado")

        qty = item.get("qty", 1)
        if qty > prod.stock:
            raise HTTPException(status_code=400, detail=f"Estoque insuficiente para {prod.name}")

        subtotal = prod.price * qty
        items.append({"product": prod, "qty": qty, "subtotal": subtotal})
        subtotal_items += subtotal

    # Aplicar cupom
    coupon_applied = None
    discount = 0
    coupon_code = data.get("coupon", "").upper()
    if coupon_code:
        cp = session.query(Coupon).filter_by(code=coupon_code).first()
        if cp and subtotal_items >= cp.min_value:
            if cp.type == "percent":
                discount = subtotal_items * cp.discount / 100
            else:
                discount = cp.discount
            coupon_applied = cp.code

    # Calcular frete
    shipping_price, shipping_days, shipping_state = calc_shipping(customer_zip)
    if subtotal_items >= FREE_SHIPPING_MIN:
        shipping_price = 0

    total_final = subtotal_items - discount + shipping_price

    # Gerar PIX
    pix_code = generate_pix_code()
    pix_expires = datetime.now() + timedelta(minutes=30)

    # Criar pedido
    order_obj = Order(
        customer_name=user["name"],
        customer_email=user["email"],
        customer_cpf=user.get("cpf", ""),
        customer_address=user.get("address", ""),
        customer_zip=customer_zip,
        subtotal=round(subtotal_items, 2),
        discount=round(discount, 2),
        shipping=round(shipping_price, 2),
        shipping_days=shipping_days,
        total=round(total_final, 2),
        coupon_code=coupon_applied,
        payment=data.get("payment", "pix"),
        pix_code=pix_code,
        pix_expires_at=pix_expires,
        created_at=datetime.now(),
        status="pending_payment",
    )
    session.add(order_obj)
    session.flush()

    for it in items:
        prod = it["product"]
        oi = OrderItem(
            order=order_obj,
            product_id=prod.id,
            name=prod.name,
            qty=it["qty"],
            price=prod.price,
            subtotal=round(it["subtotal"], 2),
        )
        session.add(oi)
        prod.stock = max(0, prod.stock - it["qty"])
        prod.sold = (prod.sold or 0) + it["qty"]

    session.commit()

    # Limpar carrinho do banco se existir
    if user:
        session.query(db.CartItem).filter_by(user_id=user["id"]).delete()
        session.commit()

    return {
        "order_id": order_obj.id,
        "total": order_obj.total,
        "pix_code": pix_code,
        "pix_expires_at": pix_expires.isoformat() if pix_expires else None,
        "message": "Pedido criado! Aguardando pagamento.",
    }


@app.get("/api/orders/{order_id}")
def get_order(
    order_id: int,
    user: dict = Depends(get_current_user),
    session: Session = Depends(db.get_db)
):
    """Retorna detalhes de um pedido."""
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")

    order_obj = session.query(Order).get(order_id)
    if not order_obj:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    items = [
        {
            "id": it.product_id,
            "name": it.name,
            "qty": it.qty,
            "price": it.price,
            "subtotal": it.subtotal,
        }
        for it in order_obj.items
    ]

    return {
        "id": order_obj.id,
        "customer": {
            "name": order_obj.customer_name,
            "email": order_obj.customer_email,
            "cpf": order_obj.customer_cpf,
            "address": order_obj.customer_address,
            "zip": order_obj.customer_zip,
        },
        "items_detail": items,
        "subtotal": order_obj.subtotal,
        "discount": order_obj.discount,
        "shipping": order_obj.shipping,
        "shipping_days": order_obj.shipping_days,
        "total": order_obj.total,
        "coupon": order_obj.coupon_code,
        "payment": order_obj.payment,
        "pix_code": order_obj.pix_code,
        "pix_expires_at": order_obj.pix_expires_at.isoformat() if order_obj.pix_expires_at else None,
        "created_at": order_obj.created_at.isoformat() if order_obj.created_at else None,
        "status": order_obj.status,
    }


# --- Rotas de Admin ---

@app.post("/api/products", status_code=201)
def create_product(
    data: dict,
    user: dict = Depends(get_current_user),
    session: Session = Depends(db.get_db)
):
    """Cria novo produto (admin)."""
    if not user:
        raise HTTPException(status_code=401, detail="Autenticação necessária")

    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Acesso negado")

    product = Product(
        name=data.get("name"),
        description=data.get("description"),
        price=data.get("price", 0.0),
        original_price=data.get("original_price"),
        category=data.get("category"),
        emoji=data.get("emoji"),
        sold=data.get("sold", 0),
        rating=data.get("rating", 0.0),
        reviews=data.get("reviews", 0),
        stock=data.get("stock", 0),
        tags=data.get("tags", []),
    )
    session.add(product)
    session.commit()

    return {"id": product.id, "message": "Produto criado."}


@app.put("/api/products/{product_id}")
def update_product(
    product_id: int,
    data: dict,
    user: dict = Depends(get_current_user),
    session: Session = Depends(db.get_db)
):
    """Atualiza produto (admin)."""
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Acesso negado")

    product = session.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    for key, value in data.items():
        if hasattr(product, key):
            setattr(product, key, value)

    session.commit()
    return {"message": "Produto atualizado com sucesso"}


@app.delete("/api/products/{product_id}")
def delete_product(
    product_id: int,
    user: dict = Depends(get_current_user),
    session: Session = Depends(db.get_db)
):
    """Remove produto (admin)."""
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Acesso negado")

    product = session.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    session.delete(product)
    session.commit()
    return {"message": "Produto removido com sucesso"}


# --- Event Handlers ---

@app.on_event("startup")
def startup():
    """Inicializa o banco de dados na startup."""
    db.init_db()
    db.migrate_from_memory([], {}, [], [])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
