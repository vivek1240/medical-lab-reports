import os
import tempfile

from backend.config import settings
from backend.schemas.lab_report import LabReport


def parse_pdf_bytes(file_bytes: bytes, file_name: str, llama_api_key: str | None = None) -> str:
    try:
        from llama_parse import LlamaParse
    except ImportError as exc:
        raise RuntimeError("llama_parse is not installed") from exc

    api_key = llama_api_key or settings.llama_cloud_api_key
    if not api_key:
        raise RuntimeError("LLAMA_CLOUD_API_KEY is missing")

    parser = LlamaParse(
        api_key=api_key,
        use_vendor_multimodal_model=True,
        vendor_multimodal_model_name="openai-gpt4o",
        high_res_ocr=True,
        result_type="text",
    )
    suffix = os.path.splitext(file_name)[1] or ".pdf"
    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp.flush()
        documents = parser.load_data(tmp.name, extra_info={"file_name": os.path.basename(file_name)})
    return "\n\n".join(doc.text for doc in documents)


def extract_lab_data(parsed_text: str, openai_api_key: str | None = None) -> LabReport:
    try:
        from llama_index.llms.openai import OpenAI
        from llama_index.program.openai import OpenAIPydanticProgram
    except ImportError as exc:
        raise RuntimeError("llama_index is not installed") from exc

    api_key = openai_api_key or settings.openai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")

    llm = OpenAI(model="gpt-4o-mini", api_key=api_key)
    program = OpenAIPydanticProgram.from_defaults(
        output_cls=LabReport,
        llm=llm,
        prompt_template_str="""
You are an expert medical lab report parser. Extract all relevant information from the lab report text below.

Instructions:
- Extract patient demographics accurately
- Identify all test names, values, units, and reference ranges
- Group tests by their categories/panels if mentioned
- Capture any flags (High, Low, Critical, Abnormal)
- Extract lab name, dates, and sample type
- Handle variations in report formats
- If information is not present, set it as null
- Be precise with numerical values and units

Report text:
{input_text}
""",
    )
    return program(input_text=parsed_text)
