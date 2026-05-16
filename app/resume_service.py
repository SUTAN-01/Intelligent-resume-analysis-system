from __future__ import annotations

import re
import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Optional
from io import BytesIO

from langchain_community.document_loaders import PyPDFLoader
from openai import OpenAI

from app.config import settings
from app.schemas import BasicInfo, JobInfo, BackgroundInfo, ResumeInfo, MatchResult


_cache = {}


def get_cache_key(data: str) -> str:
    return hashlib.md5(data.encode('utf-8')).hexdigest()


def cache_result(key: str, result):
    _cache[key] = result


def get_cached_result(key: str):
    return _cache.get(key)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    temp_path = Path('temp_resume.pdf')
    temp_path.write_bytes(pdf_bytes)
    
    try:
        loader = PyPDFLoader(str(temp_path))
        pages = loader.load()
        text = '\n'.join([page.page_content for page in pages])
        return clean_text(text)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\u4e00-\u9fa5.,;!?@-]', '', text)
    text = text.strip()
    return text


class ResumeAnalyzer:
    def __init__(self):
        if not settings.openai_api_key:
            raise RuntimeError('OPENAI_API_KEY is required')
        self._client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    
    def extract_basic_info(self, text: str) -> BasicInfo:
        cache_key = f'basic_info_{get_cache_key(text)}'
        cached = get_cached_result(cache_key)
        if cached:
            return cached
        
        prompt = f'''
从以下简历文本中提取基本信息，以JSON格式返回：
{{
    "name": "姓名",
    "phone": "电话号码",
    "email": "邮箱地址",
    "address": "居住地址"
}}
如果找不到某项信息，则返回null。

简历文本：
{text}
'''
        
        try:
            resp = self._client.chat.completions.create(
                model=settings.openai_chat_model,
                temperature=0,
                messages=[
                    {'role': 'system', 'content': '你是一个专业的简历信息提取助手，只返回JSON格式的数据。'},
                    {'role': 'user', 'content': prompt},
                ],
            )
            content = resp.choices[0].message.content or ''
            
            import json
            result = json.loads(content)
            info = BasicInfo(
                name=result.get('name'),
                phone=result.get('phone'),
                email=result.get('email'),
                address=result.get('address')
            )
            cache_result(cache_key, info)
            return info
        except Exception:
            return BasicInfo()
    
    def extract_job_info(self, text: str) -> JobInfo:
        cache_key = f'job_info_{get_cache_key(text)}'
        cached = get_cached_result(cache_key)
        if cached:
            return cached
        
        prompt = f'''
从以下简历文本中提取求职信息，以JSON格式返回：
{{
    "job_intention": "求职意向",
    "expected_salary": "期望薪资"
}}
如果找不到某项信息，则返回null。

简历文本：
{text}
'''
        
        try:
            resp = self._client.chat.completions.create(
                model=settings.openai_chat_model,
                temperature=0,
                messages=[
                    {'role': 'system', 'content': '你是一个专业的简历信息提取助手，只返回JSON格式的数据。'},
                    {'role': 'user', 'content': prompt},
                ],
            )
            content = resp.choices[0].message.content or ''
            
            import json
            result = json.loads(content)
            info = JobInfo(
                job_intention=result.get('job_intention'),
                expected_salary=result.get('expected_salary')
            )
            cache_result(cache_key, info)
            return info
        except Exception:
            return JobInfo()
    
    def extract_background_info(self, text: str) -> BackgroundInfo:
        cache_key = f'background_info_{get_cache_key(text)}'
        cached = get_cached_result(cache_key)
        if cached:
            return cached
        
        prompt = f'''
从以下简历文本中提取背景信息，以JSON格式返回：
{{
    "work_years": "工作年限",
    "education": "学历背景",
    "project_experience": "项目经历（简要总结）"
}}
如果找不到某项信息，则返回null。

简历文本：
{text}
'''
        
        try:
            resp = self._client.chat.completions.create(
                model=settings.openai_chat_model,
                temperature=0,
                messages=[
                    {'role': 'system', 'content': '你是一个专业的简历信息提取助手，只返回JSON格式的数据。'},
                    {'role': 'user', 'content': prompt},
                ],
            )
            content = resp.choices[0].message.content or ''
            
            import json
            result = json.loads(content)
            info = BackgroundInfo(
                work_years=result.get('work_years'),
                education=result.get('education'),
                project_experience=result.get('project_experience')
            )
            cache_result(cache_key, info)
            return info
        except Exception:
            return BackgroundInfo()
    
    def analyze_resume(self, text: str) -> ResumeInfo:
        cache_key = f'resume_info_{get_cache_key(text)}'
        cached = get_cached_result(cache_key)
        if cached:
            return cached
        
        basic_info = self.extract_basic_info(text)
        job_info = self.extract_job_info(text)
        background_info = self.extract_background_info(text)
        
        info = ResumeInfo(
            basic_info=basic_info,
            job_info=job_info,
            background_info=background_info,
            raw_text=text
        )
        cache_result(cache_key, info)
        return info
    
    def match_resume(self, resume_text: str, job_description: str) -> MatchResult:
        cache_key = f'match_{get_cache_key(resume_text + job_description)}'
        cached = get_cached_result(cache_key)
        if cached:
            return cached
        
        prompt = f'''
请分析以下简历与岗位需求的匹配度，以JSON格式返回结果：
{{
    "overall_score": 总体匹配度分数(0-100),
    "skill_match_rate": 技能匹配率(0-100),
    "experience_relevance": 工作经验相关性(0-100),
    "education_match": 学历匹配度(0-100),
    "keywords_matched": ["匹配到的关键词列表"],
    "missing_keywords": ["缺失的关键词列表"]
}}

岗位需求：
{job_description}

简历内容：
{resume_text}
'''
        
        try:
            resp = self._client.chat.completions.create(
                model=settings.openai_chat_model,
                temperature=0,
                messages=[
                    {'role': 'system', 'content': '你是一个专业的HR招聘助手，能够精准评估简历与岗位的匹配度。只返回JSON格式的数据。'},
                    {'role': 'user', 'content': prompt},
                ],
            )
            content = resp.choices[0].message.content or ''
            
            import json
            result = json.loads(content)
            match_result = MatchResult(
                overall_score=float(result.get('overall_score', 0)),
                skill_match_rate=float(result.get('skill_match_rate', 0)),
                experience_relevance=float(result.get('experience_relevance', 0)),
                education_match=float(result.get('education_match', 0)),
                keywords_matched=result.get('keywords_matched', []),
                missing_keywords=result.get('missing_keywords', [])
            )
            cache_result(cache_key, match_result)
            return match_result
        except Exception:
            return MatchResult(
                overall_score=0,
                skill_match_rate=0,
                experience_relevance=0,
                education_match=0,
                keywords_matched=[],
                missing_keywords=[]
            )
