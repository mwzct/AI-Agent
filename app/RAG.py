from pathlib import Path

from langchain.tools import tool
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"

def split_text(text: str, chunk_size: int = 500, overlap: int = 80):
    """将长文本切成有重叠的文本片段。"""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("必须满足chunk_size > overlap >= 0")

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks

def load_document():
    """读取知识库中的Markdown和TXT文件，并切分文本。"""
    documents = []

    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    for path in sorted(KNOWLEDGE_DIR.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".md", ".txt"}:
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")

        for index, chunk in enumerate(split_text(text)):
            documents.append({
                "source": str(path.relative_to(KNOWLEDGE_DIR.absolute().parent)),
                "chunk_id": index,
                "text": chunk
            })

    return documents

#服务启动、首次导入模块时加载文档并建立检索索引
documents = load_document()
vectorizer = None
document_vectors = None

if documents:
    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 4),
        max_features=5000,
    )
    document_vectors = vectorizer.fit_transform(
        [doc["text"] for doc in documents]
    )

def retrieve_documents(query: str, top_k: int = 3) -> str:
    """根据用户问题，返回最相关的文档片段。"""
    if not query.strip():
        return "检索问题不能为空。"

    if not documents or vectorizer is None:
        return "知识库目前没有可检索的文档，请先添加.md或.txt文件。"

    query_vector = vectorizer.transform([query])
    scores = cosine_similarity(
        query_vector,
        document_vectors,
    ).ravel()

    ranked_indices = scores.argsort()[::-1]

    results = []

    for index in ranked_indices:
        score = float(scores[index])

        if score <=0:
            continue

        doc = documents[index]

        results.append(
            f"来源：{doc['source']}\n"
            f"相关度：{score:.3f}\n"
            f"内容：{doc['text']}"
        )

        if len(results) >= top_k:
            break

    if not results:
        return "没有找到明显相关的知识库内容。"

    return "\n\n---\n\n".join(results)

@tool
def search_knowledge_base(query:str) -> str:
    """检索本地知识库。当用户询问目的地攻略、景点介绍、交通方式、当地美食推荐时，调用此工具。
    不适用于实时价格、库存、订单查询或需要联网的最新动态。"""
    return retrieve_documents(query)