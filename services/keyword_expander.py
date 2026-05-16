"""Keyword expansion service - translates & expands user keywords to English for arXiv search"""
import logging
from services.ollama import chat

logger = logging.getLogger(__name__)

# Fast-path: common Chinese AI/ML/CS terms → English equivalents
_QUICK_MAP = {
    "大模型": ["large language model", "LLM", "foundation model"],
    "大语言模型": ["large language model", "LLM", "GPT"],
    "神经网络": ["neural network", "deep neural network"],
    "机器学习": ["machine learning", "ML"],
    "深度学习": ["deep learning", "DNN"],
    "计算机视觉": ["computer vision", "CV", "image recognition"],
    "自然语言处理": ["natural language processing", "NLP", "text mining"],
    "强化学习": ["reinforcement learning", "RL"],
    "知识图谱": ["knowledge graph", "KG", "ontology"],
    "推荐系统": ["recommendation system", "recommender system", "collaborative filtering"],
    "图神经网络": ["graph neural network", "GNN", "graph learning"],
    "扩散模型": ["diffusion model", "score-based model", "DDPM"],
    "多模态": ["multimodal", "vision-language", "MLLM"],
    "智能体": ["agent", "autonomous agent", "multi-agent"],
    "提示词": ["prompt engineering", "in-context learning"],
    "微调": ["fine-tuning", "PEFT", "LoRA", "instruction tuning"],
    "向量数据库": ["vector database", "vector store", "embedding search"],
    "检索增强": ["retrieval augmented generation", "RAG", "dense retrieval"],
    "联邦学习": ["federated learning", "distributed learning"],
    "元学习": ["meta-learning", "few-shot learning", "learning to learn"],
    "少样本": ["few-shot learning", "low-resource", "data-efficient"],
    "零样本": ["zero-shot learning", "zero-shot transfer"],
    "模型压缩": ["model compression", "quantization", "pruning", "knowledge distillation"],
    "注意力机制": ["attention mechanism", "self-attention", "transformer"],
    "预训练": ["pre-training", "pretraining", "self-supervised"],
    "生成式": ["generative model", "generative AI"],
    "对话系统": ["dialogue system", "conversational AI", "chatbot"],
    "语音识别": ["speech recognition", "ASR", "audio processing"],
    "目标检测": ["object detection", "YOLO", "visual grounding"],
    "图像分割": ["image segmentation", "semantic segmentation", "instance segmentation"],
    "代码生成": ["code generation", "program synthesis", "GitHub Copilot"],
    "数据增强": ["data augmentation", "synthetic data"],
}


def _is_chinese(text: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in text)


async def expand_keywords(keywords: list) -> list:
    """Normalize, translate and expand keywords to English search terms.

    - Splits on comma / semicolon (full-width or half-width)
    - Quick-maps common Chinese AI/ML terms to English
    - Falls back to Ollama AI translation for unknown Chinese terms
    - Deduplicates while preserving order
    """
    # Step 1: normalize + split
    normalized = []
    for kw in keywords:
        for part in str(kw).replace(";", ",").replace("；", ",").replace("、", ",").split(","):
            part = part.strip()
            if part:
                normalized.append(part)

    result = []
    to_ai = []

    for kw in normalized:
        if _is_chinese(kw):
            if kw in _QUICK_MAP:
                result.extend(_QUICK_MAP[kw])
            else:
                to_ai.append(kw)
        else:
            result.append(kw)

    # Step 2: AI translate remaining Chinese terms
    if to_ai:
        try:
            english = await _ai_translate(to_ai)
            result.extend(english)
        except Exception as e:
            logger.warning(f"AI keyword translation failed: {e}")
        # Keep originals as display labels
        result.extend(to_ai)

    # Step 3: also keep all original normalized terms
    result.extend(normalized)

    # Step 4: deduplicate, preserve order, skip blanks
    seen: set = set()
    final = []
    for kw in result:
        key = kw.lower().strip()
        if key and key not in seen:
            seen.add(key)
            final.append(kw)

    return final


async def _ai_translate(terms: list) -> list:
    """Use Ollama to translate unknown Chinese AI/ML terms to English."""
    joined = ", ".join(terms)
    prompt = (
        f"Translate these Chinese AI/ML terms to English for arXiv paper search. "
        f"For each term provide 1-3 English translations/abbreviations used in academic papers. "
        f"Return ONLY a comma-separated list of English terms, no explanations, no Chinese.\n\n"
        f"Terms: {joined}"
    )
    response = await chat([{"role": "user", "content": prompt}])
    raw = [t.strip().strip("\"\'") for t in response.split(",")]
    return [t for t in raw if t and not _is_chinese(t) and len(t) > 1]
