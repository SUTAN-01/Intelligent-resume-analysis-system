from __future__ import annotations

import os
from pathlib import Path
from io import BytesIO

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api_deps import get_current_user, get_db
from app.config import settings
from app.db import Conversation, Message, User, init_db
from app.docs_routes import router as docs_router

from app.rag import RAGService
from app.rag_store import get_vectorstore
from app.schemas import (
    AskRequest, AskResponse, ConversationItem, MessageItem, LoginRequest, 
    RegisterRequest, TokenResponse, AnalysisResult, AnalyzeResumeRequest
)
from app.resume_service import ResumeAnalyzer, extract_text_from_pdf
from app.security import create_access_token, hash_password, verify_password


_BASE_DIR = Path(__file__).resolve().parents[1]

app = FastAPI(title='RAG AI')
app.include_router(docs_router)

cors_origins = [x.strip() for x in settings.cors_allow_origins.split(',') if x.strip()]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

templates = Jinja2Templates(directory=str(_BASE_DIR / 'web' / 'templates'))
static_dir = _BASE_DIR / 'web' / 'static'
if static_dir.is_dir():
    app.mount('/static', StaticFiles(directory=str(static_dir)), name='static')


@app.on_event('startup')
def _startup():
    init_db()
    os.makedirs(settings.chroma_dir, exist_ok=True)


@app.get('/health')
def health():
    return {'ok': True}


@app.get('/', include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@app.get('/resume', include_in_schema=False)
def resume_page(request: Request):
    return templates.TemplateResponse('resume.html', {'request': request})


@app.get('/login', include_in_schema=False)
def login_page(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})


@app.get('/register', include_in_schema=False)
def register_page(request: Request):
    return templates.TemplateResponse('register.html', {'request': request})


@app.get('/chat', include_in_schema=False)
def chat_page(request: Request):
    return templates.TemplateResponse('chat.html', {'request': request})


@app.get('/ui', include_in_schema=False)
def ui_redirect():
    return RedirectResponse(url='/chat')


@app.post('/auth/register')
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail='Username already exists')
    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    return {'ok': True}


@app.post('/auth/login', response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    token = create_access_token(subject=user.username)
    return TokenResponse(access_token=token)


@app.get('/chat/conversations', response_model=list[ConversationItem])
def list_conversations(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Conversation).where(Conversation.user_id == current.id).order_by(Conversation.id.desc())).scalars()
    return [ConversationItem(id=c.id, title=c.title) for c in rows]


@app.get('/chat/conversations/{conversation_id}', response_model=list[MessageItem])
def get_conversation_messages(conversation_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == current.id)).scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail='Conversation not found')
    msgs = db.execute(select(Message).where(Message.conversation_id == conv.id).order_by(Message.id.asc())).scalars()
    return [MessageItem(id=m.id, role=m.role, content=m.content) for m in msgs]


def _vectorstore_count(vs) -> int | None:
    try:
        return int(vs._collection.count())
    except Exception:
        return None


def _ensure_vectorstore_ready() -> int | None:
    try:
        vs = get_vectorstore()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return _vectorstore_count(vs)


@app.post('/chat/ask', response_model=AskResponse)
def ask(payload: AskRequest, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.conversation_id is None:
        #把所有用户会话问题列入数据库
        conv = Conversation(user_id=current.id, title=payload.question[:50])
        db.add(conv)
        db.commit()
        db.refresh(conv)
    else:
        conv = db.execute(select(Conversation).where(Conversation.id == payload.conversation_id, Conversation.user_id == current.id)).scalar_one_or_none()
        if conv is None:
            raise HTTPException(status_code=404, detail='Conversation not found')
    # 保存用户和智能体的对话
    db.add(Message(conversation_id=conv.id, role='user', content=payload.question))
    db.commit()

    count = _ensure_vectorstore_ready()
    if count == 0:
        answer = (
        '向量库为空（还没有构建/构建失败），因此无法从文档中检索到上下文。\n'
        '请先在页面里上传文档后点击“构建向量库”，或运行：python -m scripts.ingest。\n'
        '构建成功后，目录 data/chroma 下应该出现 chroma.sqlite3 等文件。'
        )
        db.add(Message(conversation_id=conv.id, role='assistant', content=answer))
        db.commit()
        return AskResponse(conversation_id=conv.id, answer=answer, sources=[])

    rag = RAGService()
   
    docs = rag.retrieve(payload.question, k=4)

    if not docs:
       

        answer = (
            '本次检索没有返回任何文档片段，所以无法基于文档回答。\n'
            '你可以尝试：换关键词/更具体的问题；或确认已构建向量库且 data/chroma 目录非空。'
        )
        
        db.add(Message(conversation_id=conv.id, role='assistant', content=answer))
        db.commit()
        return AskResponse(conversation_id=conv.id, answer=answer, sources=[])

    result = rag.answer(question=payload.question, docs=docs)

    db.add(Message(conversation_id=conv.id, role='assistant', content=result.answer))
    db.commit()

    return AskResponse(conversation_id=conv.id, answer=result.answer, sources=result.sources)


@app.post('/resume/analyze', response_model=AnalysisResult)
async def analyze_resume(
    file: UploadFile = File(...),
    job_description: str | None = Form(None)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail='只支持PDF格式的简历')
    
    pdf_bytes = await file.read()
    text = extract_text_from_pdf(pdf_bytes)
    
    analyzer = ResumeAnalyzer()
    resume_info = analyzer.analyze_resume(text)
    
    match_result = None
    if job_description:
        match_result = analyzer.match_resume(text, job_description)
    
    return AnalysisResult(resume_info=resume_info, match_result=match_result)
