from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from app.config import settings
from app.rag_store import format_docs_for_prompt, get_vectorstore


SYSTEM_PROMPT_ZH = (
    '你是一个基于本地简历文档回答问题的人工智能助手。\n'
    '要求：\n'
    '1) 只根据给定的"文档上下文"回答；不要编造。\n'
    '2) 如果上下文不足以回答，请明确说明"文档中未找到相关信息"，并说明还需要哪些信息。\n'
    '3) 输出中文，尽量简洁、结构化。'
    '4) 如果有的话，从简历文本中提取姓名、电话、邮箱、地址等关键基本信息，以及求职意向、期望薪资等求职信息，还有工作年限、学历背景、项目经历等背景信息'
)

@dataclass(frozen=True)
class RAGResult:
    answer: str
    sources: list[dict]


class RAGService:
    def __init__(self):
        if not settings.openai_api_key:
            raise RuntimeError('OPENAI_API_KEY is required')
        self._vs = get_vectorstore()
        self._client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    def retrieve(self, query: str, k: int = 4):
        return self._vs.similarity_search(query, k=k)

    def answer(self, *, question: str, docs) -> RAGResult:
        context = format_docs_for_prompt(docs)
        user_content = (
            f'文档上下文：\n{context}\n\n'
            f'用户问题：\n{question}\n\n'
            f'请基于上下文回答，并给出要点总结。'
        )
        resp = self._client.chat.completions.create(
            model=settings.openai_chat_model,
            temperature=0,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT_ZH},
                {'role': 'user', 'content': user_content},
            ],
        )
        answer = resp.choices[0].message.content or ''

        sources: list[dict] = []
        for d in docs:
            sources.append({
                'source': d.metadata.get('source', ''),
                # 'page': d.metadata.get('page', None),
                # 'snippet': (d.page_content[:200] + '...') if len(d.page_content) > 200 else d.page_content,
            })
        return RAGResult(answer=answer, sources=sources) 
