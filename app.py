import streamlit as st
import arxiv
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import re

# --- CONFIG ---
NUM_PAPERS = 4
SUMMARIZER_MODEL = "sshleifer/distilbart-cnn-12-6"
LLM_MODEL = "MBZUAI/LaMini-Flan-T5-783M"

# --- MODELS ---
summarizer = pipeline("summarization", model=SUMMARIZER_MODEL)
tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL)
model = AutoModelForSeq2SeqLM.from_pretrained(LLM_MODEL)

# --- CLEAN TEXT ---
def clean_text(text):
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

# --- SECTION PROMPTS ---
SECTION_PROMPTS = {
    "Introduction": """Write a detailed academic introduction (~300 words) for a literature review on the use of AI in healthcare, based on the following paper summaries.

Paper summaries:
{summaries}
""",
    "Key Approaches and Findings": """Describe in detail (~400 words) the most important technical approaches, methodologies, and key findings from the following summaries.

Paper summaries:
{summaries}
""",
    "Comparative Analysis": """Write a thorough comparative analysis (~400 words) of the research papers summarized below.

Paper summaries:
{summaries}
""",
    "Gaps and Future Directions": """Write a comprehensive discussion (~300 words) about the gaps, limitations, and future research directions based on the paper summaries below.

Paper summaries:
{summaries}
"""
}

# --- FUNCTIONS ---
def fetch_papers(topic):
    search = arxiv.Search(query=topic, max_results=NUM_PAPERS, sort_by=arxiv.SortCriterion.Relevance)
    results = list(search.results())
    return results

def summarize_paper(abstract):
    try:
        return summarizer(abstract, max_length=100, min_length=30, do_sample=False)[0]["summary_text"]
    except:
        return abstract[:300]

def generate_section(prompt_text):
    input_ids = tokenizer(prompt_text, return_tensors="pt", truncation=True, max_length=1024)
    output = model.generate(**input_ids, max_new_tokens=700)
    return tokenizer.decode(output[0], skip_special_tokens=True)

def create_bibliography(papers):
    bib = []
    for i, paper in enumerate(papers, 1):
        authors = ", ".join([a.name for a in paper.authors])
        title = paper.title.strip()
        url = paper.entry_id
        bib.append(f"{i}. {authors} ({paper.published.year}). *{title}*. arXiv. {url}")
    return "\n".join(bib)

# --- STREAMLIT UI ---
st.title("📚 Literature Review Generator")
st.write("Enter a research topic to generate a structured literature review using arXiv papers and Hugging Face models.")

topic = st.text_input("Enter your topic (e.g., 'AI in healthcare')")

if st.button("Generate Review"):
    if not topic.strip():
        st.warning("Please enter a topic.")
    else:
        with st.spinner("Fetching and processing papers..."):
            papers = fetch_papers(topic)
            if not papers:
                st.error("No relevant papers found.")
            else:
                summaries = []
                for paper in papers:
                    abstract = paper.summary.strip().replace("\n", " ")
                    summary = summarize_paper(abstract)
                    summaries.append(f"- {summary}")
                summary_text = "\n".join(summaries)

                sections = []
                for name, prompt in SECTION_PROMPTS.items():
                    filled_prompt = prompt.format(summaries=summary_text)
                    section_text = generate_section(filled_prompt)
                    sections.append(f"### {name}\n{clean_text(section_text)}")

                st.markdown("\n\n".join(sections))
                st.markdown("## Bibliography")
                st.markdown(create_bibliography(papers))
