from __future__ import annotations

import re
import hashlib
import logging
import json
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from openai import OpenAI

from app.config import settings
from app.schemas import BasicInfo, JobInfo, BackgroundInfo, ResumeInfo, MatchResult

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
        logger.info(f"Extracted text length: {len(text)}")
        return clean_text(text)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def parse_json_safely(content: str):
    try:
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        return json.loads(content)
    except Exception as e:
        logger.error(f"JSON parsing error: {e}, content: {content[:200]}")
        return None


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

        prompt = f'''从以下简历文本中提取基本信息。

要求：
1. 只返回有效的JSON格式，不要包含任何其他文字
2. JSON格式：{{"name":"姓名","phone":"电话","email":"邮箱","address":"地址"}}
3. 如果某项信息找不到，值设为null

简历文本：
{text[:2000]}
'''

        try:
            resp = self._client.chat.completions.create(
                model=settings.openai_chat_model,
                temperature=0,
                messages=[
                    {'role': 'system', 'content': '你是一个专业的简历信息提取助手。只返回JSON格式的数据，不要包含任何解释说明。'},
                    {'role': 'user', 'content': prompt},
                ],
            )
            content = resp.choices[0].message.content or ''
            logger.info(f"Basic info API response: {content[:300]}")

            result = parse_json_safely(content)
            if result:
                info = BasicInfo(
                    name=result.get('name'),
                    phone=result.get('phone'),
                    email=result.get('email'),
                    address=result.get('address')
                )
                cache_result(cache_key, info)
                return info
            else:
                logger.error("Failed to parse basic info JSON")
                return BasicInfo()
        except Exception as e:
            logger.error(f"Error extracting basic info: {e}")
            return BasicInfo()

    def extract_job_info(self, text: str) -> JobInfo:
        cache_key = f'job_info_{get_cache_key(text)}'
        cached = get_cached_result(cache_key)
        if cached:
            return cached

        prompt = f'''从以下简历文本中提取求职信息。

要求：
1. 只返回有效的JSON格式，不要包含任何其他文字
2. JSON格式：{{"job_intention":"求职意向","expected_salary":"期望薪资"}}
3. 如果某项信息找不到，值设为null

简历文本：
{text[:2000]}
'''

        try:
            resp = self._client.chat.completions.create(
                model=settings.openai_chat_model,
                temperature=0,
                messages=[
                    {'role': 'system', 'content': '你是一个专业的简历信息提取助手。只返回JSON格式的数据，不要包含任何解释说明。'},
                    {'role': 'user', 'content': prompt},
                ],
            )
            content = resp.choices[0].message.content or ''
            logger.info(f"Job info API response: {content[:300]}")

            result = parse_json_safely(content)
            if result:
                info = JobInfo(
                    job_intention=result.get('job_intention'),
                    expected_salary=result.get('expected_salary')
                )
                cache_result(cache_key, info)
                return info
            else:
                logger.error("Failed to parse job info JSON")
                return JobInfo()
        except Exception as e:
            logger.error(f"Error extracting job info: {e}")
            return JobInfo()

    def extract_background_info(self, text: str) -> BackgroundInfo:
        cache_key = f'background_info_{get_cache_key(text)}'
        cached = get_cached_result(cache_key)
        if cached:
            return cached

        prompt = f'''你是一个专业的简历分析专家。请从以下简历文本中提取背景信息。

简历文本：
{text[:2000]}

请严格按照以下JSON格式输出结果，不要包含任何其他文字：
{{
    "work_years": "工作年限，如：3年以上",
    "education": "最高学历，如：本科",
    "project_experience": "项目经历，详细描述每个项目的名称、职责和成果"
}}

注意事项：
1. 如果某项信息找不到，值设为null
2. project_experience 需要详细提取，包括项目名称、担任角色、主要职责和取得的成果
3. 如果有多个项目，用分号分隔
'''

        try:
            resp = self._client.chat.completions.create(
                model=settings.openai_chat_model,
                temperature=0,
                messages=[
                    {'role': 'system', 'content': '你是一个专业的简历信息提取助手。只返回JSON格式的数据，不要包含任何解释说明。'},
                    {'role': 'user', 'content': prompt},
                ],
            )
            content = resp.choices[0].message.content or ''
            logger.info(f"Background info API response: {content[:300]}")

            result = parse_json_safely(content)
            if result:
                info = BackgroundInfo(
                    work_years=result.get('work_years'),
                    education=result.get('education'),
                    project_experience=result.get('project_experience')
                )
                cache_result(cache_key, info)
                return info
            else:
                logger.error("Failed to parse background info JSON")
                return BackgroundInfo()
        except Exception as e:
            logger.error(f"Error extracting background info: {e}")
            return BackgroundInfo()

    def analyze_resume(self, text: str) -> ResumeInfo:
        cache_key = f'resume_info_{get_cache_key(text)}'
        cached = get_cached_result(cache_key)
        if cached:
            return cached

        logger.info(f"Analyzing resume text length: {len(text)}")

        basic_info = self.extract_basic_info(text)
        job_info = self.extract_job_info(text)
        background_info = self.extract_background_info(text)

        info = ResumeInfo(
            basic_info=basic_info,
            job_info=job_info,
            background_info=background_info,
            raw_text=text[:500]
        )
        cache_result(cache_key, info)
        return info

    def match_resume(self, resume_text: str, job_description: str) -> MatchResult:
        cache_key = f'match_{get_cache_key(resume_text + job_description)}'
        cached = get_cached_result(cache_key)
        if cached:
            return cached

        prompt = f'''你是一个专业的HR招聘专家，擅长分析简历与岗位需求的匹配度。

请分析以下简历与岗位需求的匹配度：

岗位需求：
{job_description[:1500]}

简历内容：
{resume_text[:2000]}

请严格按照以下JSON格式输出结果，不要包含任何其他文字：
{{
    "overall_score": 整数分数(0-100),
    "skill_match_rate": 整数分数(0-100),
    "experience_relevance": 整数分数(0-100),
    "education_match": 整数分数(0-100),
    "keywords_matched": ["匹配的关键词1", "匹配的关键词2", ...],
    "missing_keywords": ["缺失的关键词1", "缺失的关键词2", ...]
}}

注意事项：
1. 所有分数必须是0-100之间的整数
2. keywords_matched 列出简历中出现且岗位需求需要的关键词
3. missing_keywords 列出岗位需求需要但简历中未提及的关键词
4. 如果无法确定某个值，使用合理的默认值
'''

        try:
            resp = self._client.chat.completions.create(
                model=settings.openai_chat_model,
                temperature=0,
                messages=[
                    {'role': 'system', 'content': '你是一个专业的HR招聘助手。只返回JSON格式的数据，不要包含任何解释说明。'},
                    {'role': 'user', 'content': prompt},
                ],
            )
            content = resp.choices[0].message.content or ''
            logger.info(f"Match result API response: {content[:300]}")

            result = parse_json_safely(content)
            if result:
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
            else:
                logger.error("Failed to parse match result JSON")
                return MatchResult(
                    overall_score=0,
                    skill_match_rate=0,
                    experience_relevance=0,
                    education_match=0,
                    keywords_matched=[],
                    missing_keywords=[]
                )
        except Exception as e:
            logger.error(f"Error matching resume: {e}")
            return MatchResult(
                overall_score=0,
                skill_match_rate=0,
                experience_relevance=0,
                education_match=0,
                keywords_matched=[],
                missing_keywords=[]
            )
