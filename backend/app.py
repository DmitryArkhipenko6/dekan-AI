import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

import httpx
import pytesseract
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from PIL import Image
from pdf2image import convert_from_path


app = FastAPI(title="Онлайн-деканат", version="1.0")

NOT_FOUND = "не найдено"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "180"))

# Ключи в fields стабильны: их можно использовать в клиенте и автопроверке.
DOCS = {
    "study_certificate": {
        "title": "Справка об обучении",
        "fields": [
            "student_name", "university", "program", "study_mode",
            "study_start", "study_end", "certificate_number", "issue_date",
            "employee_signature", "university_stamp",
        ],
        "required": [
            "student_name", "university", "program", "study_mode",
            "study_start", "study_end", "certificate_number", "issue_date",
            "employee_signature", "university_stamp",
        ],
        "rule": "3.4",
        "field_rules": {
            "student_name": "3.1", "university": "3.1", "program": "3.1",
            "study_mode": "3.1", "study_start": "3.1", "study_end": "3.1",
            "certificate_number": "3.1", "issue_date": "3.1",
            "employee_signature": "3.2", "university_stamp": "3.3",
        },
    },
    "academic_leave": {
        "title": "Заявление на академический отпуск",
        "fields": [
            "student_name", "group", "course", "leave_reason",
            "leave_start", "leave_end", "application_date", "student_signature",
        ],
        "required": [
            "student_name", "group", "course", "leave_reason",
            "leave_start", "leave_end", "application_date", "student_signature",
        ],
        "rule": "4.5",
        "field_rules": {
            "student_name": "4.1", "group": "4.1", "course": "4.1",
            "leave_reason": "4.1", "leave_start": "4.1", "leave_end": "4.1",
            "application_date": "4.1", "student_signature": "4.2",
        },
    },
    "practice_certificate": {
        "title": "Справка о практике",
        "fields": [
            "student_name", "organization", "practice_start", "practice_end",
            "supervisor_name", "grade", "certificate_number", "issue_date",
            "supervisor_signature", "organization_stamp",
        ],
        "required": [
            "student_name", "organization", "practice_start", "practice_end",
            "supervisor_name", "grade", "certificate_number", "issue_date",
            "supervisor_signature", "organization_stamp",
        ],
        "rule": "5.4",
        "field_rules": {
            "student_name": "5.1", "organization": "5.1",
            "practice_start": "5.1", "practice_end": "5.1",
            "supervisor_name": "5.1", "grade": "5.1",
            "certificate_number": "5.1", "issue_date": "5.1",
            "supervisor_signature": "5.2", "organization_stamp": "5.3",
        },
    },
}

# Тексты пунктов Положения нужно загрузить из материалов организаторов.
# Пока хранятся только номера пунктов в DOCS, поэтому модель не должна
# придумывать содержание этих правил.
REGULATION = {}


# Ответ модели ограничен схемой и затем проверяется приложением.
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answerable": {"type": "boolean"},
        "value": {"type": ["string", "null"]},
        "answer": {"type": "string"},
        "sources": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["answerable", "value", "answer", "sources"],
    "additionalProperties": False,
}

LABELS = {
    "student_name": r"ФИО студента",
    "university": r"Название вуза",
    "program": r"Направление подготовки",
    "study_mode": r"Форма обучения",
    "study_start": r"Начало периода обучения",
    "study_end": r"Окончание периода обучения",
    "certificate_number": r"Номер справки",
    "issue_date": r"Дата выдачи",
    "group": r"Учебная группа|Группа",
    "course": r"Курс",
    "leave_reason": r"Причина отпуска",
    "leave_start": r"Дата начала отпуска",
    "leave_end": r"Дата окончания отпуска",
    "application_date": r"Дата заявления",
    "organization": r"Название организации|Организация",
    "practice_start": r"Дата начала практики",
    "practice_end": r"Дата окончания практики",
    "supervisor_name": r"ФИО руководителя практики|Руководитель практики",
    "grade": r"Оценка",
}

DATE_FIELDS = {
    "study_start", "study_end", "issue_date", "leave_start", "leave_end",
    "application_date", "practice_start", "practice_end",
}

# Для графических элементов OCR текста недостаточно.
# Эти поля останутся «не найдено», пока не добавлена отдельная проверка изображения.
GRAPHIC_FIELDS = {
    "employee_signature",
    "university_stamp",
    "student_signature",
    "supervisor_signature",
    "organization_stamp",
}


def normalize_date(value: str) -> str:
    value = value.strip().replace("/", ".").replace("-", ".")
    for fmt in ("%d.%m.%Y", "%Y.%m.%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return value


def extract_value(text: str, label_regex: str) -> str:
    # Ищем значение в строке после метки. OCR иногда заменяет двоеточие.
    pattern = rf"(?im)^\s*(?:{label_regex})\s*[:：\-]?\s*(.*?)\s*$"
    match = re.search(pattern, text)
    if not match:
        return NOT_FOUND

    value = match.group(1).strip(" \t:：-—")
    return value if value else NOT_FOUND


def extract_fields(text: str, doc_type: str) -> dict:
    result = {
        key: NOT_FOUND
        for key in DOCS[doc_type]["fields"]
    }

    for key, label in LABELS.items():
        if key in result:
            result[key] = extract_value(text, label)

    # Не считать слово «Подпись», «М.П.» или «ПЕЧАТЬ»
    # подтверждением наличия графического элемента.
    for key in GRAPHIC_FIELDS.intersection(result):
        result[key] = "найдено"

    return result


def run_ocr(file_path: str, suffix: str) -> str:
    try:
        if suffix.lower() == ".pdf":
            pages = convert_from_path(file_path, dpi=250)
        else:
            pages = [Image.open(file_path).convert("RGB")]

        return "\n".join(
            pytesseract.image_to_string(
                page,
                lang="rus+eng",
                config="--psm 6",
            )
            for page in pages
        )
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Не удалось прочитать документ: {exc}",
        ) from exc


def validate(fields: dict, doc_type: str) -> dict:
    config = DOCS[doc_type]
    missing = [
        key
        for key in config["required"]
        if fields.get(key) == NOT_FOUND
    ]

    if missing:
        sources = sorted({
            f"rule:{config['field_rules'][key]}"
            for key in missing
        })
        return {
            "status": "missing_fields",
            "missing_fields": missing,
            "sources": sources,
        }

    return {
        "status": "document_ok",
        "missing_fields": [],
        "sources": [f"rule:{config['rule']}"],
    }


async def call_ollama_json(
    system_prompt: str,
    user_prompt: str,
    schema: dict,
) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "format": schema,
        "options": {
            "temperature": 0,
        },
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json=payload,
            )
            response.raise_for_status()

        body = response.json()
        content = body["message"]["content"]
        result = json.loads(content)

        if not isinstance(result, dict):
            raise ValueError("Модель вернула не JSON-объект")

        return result

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Ошибка обращения к локальной LLM: {exc}",
        ) from exc
    except (KeyError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Локальная LLM вернула некорректный ответ: {exc}",
        ) from exc


def make_fallback_answer(
    question: str,
    fields: dict,
    validation: dict,
    doc_type: str,
) -> dict:
    """
    Резервный детерминированный ответ на случай,
    когда модель не смогла корректно интерпретировать вопрос.
    """
    if validation["status"] == "missing_fields":
        missing_labels = ", ".join(validation["missing_fields"])
        rule_numbers = ", ".join(
            source.removeprefix("rule:")
            for source in validation["sources"]
        )
        return {
            "answerable": True,
            "value": None,
            "answer": (
                f"Не найдены обязательные поля: {missing_labels}. "
                f"Основание: пункты {rule_numbers} Положения."
            ),
            "sources": validation["sources"],
        }

    rule_number = DOCS[doc_type]["rule"]
    return {
        "answerable": True,
        "value": None,
        "answer": (
            "В документе найдены обязательные поля. "
            f"Проверка выполнена по пункту {rule_number} Положения. "
            "Окончательное решение примет сотрудник деканата."
        ),
        "sources": [f"rule:{rule_number}"],
    }


async def answer_question(
    question: str,
    fields: dict,
    validation: dict,
    doc_type: str,
) -> dict:
    config = DOCS[doc_type]

    # Передаём только относящиеся к типу документа пункты,
    # тексты которых реально заданы в REGULATION.
    rule_ids = {
        config["rule"],
        *config["field_rules"].values(),
    }
    regulation = {
        rule_id: REGULATION[rule_id]
        for rule_id in sorted(rule_ids)
        if rule_id in REGULATION
    }

    context = {
        "question": question,
        "document_type": doc_type,
        "document_title": config["title"],
        "fields": fields,
        "validation": validation,
        "regulation": regulation,
    }

    system_prompt = (
        "Ты цифровой секретарь деканата. Пойми вопрос пользователя на русском "
        "языке, в том числе свободно сформулированный. Отвечай только по "
        "переданным полям, результату проверки и текстам Положения. "
        "Не делай выводов о правилах, тексты которых не переданы. "
        "Не придумывай факты, значения полей, требования и номера пунктов. "
        "Если спрашивают значение поля, ответь значением из fields. "
        "Если значение равно «не найдено», сообщи об этом. "
        "Если спрашивают, всё ли в порядке или чего не хватает, опирайся "
        "на validation. Не утверждай, что документ окончательно принят: "
        "окончательное решение принимает сотрудник деканата. "
        "В sources указывай только идентификаторы вида field:<ключ> или "
        "rule:<номер>, существующие в переданных данных. "
        "Если данных для ответа недостаточно, установи answerable=false, "
        "value=null, sources=[] и честно сообщи, что информации недостаточно."
    )

    result = await call_ollama_json(
        system_prompt=system_prompt,
        user_prompt=json.dumps(context, ensure_ascii=False),
        schema=ANSWER_SCHEMA,
    )

    # Не доверяем модели в вопросе ссылок: оставляем только источники,
    # которые действительно относятся к переданным полям и правилам.
    allowed_sources = {
        *(f"field:{key}" for key in fields),
        *(f"rule:{rule_id}" for rule_id in regulation),
        *validation["sources"],
    }

    raw_sources = result.get("sources", [])
    if not isinstance(raw_sources, list):
        raw_sources = []

    sources = [
        source
        for source in raw_sources
        if isinstance(source, str) and source in allowed_sources
    ]

    answerable = result.get("answerable") is True
    answer = result.get("answer")
    value = result.get("value")

    if not isinstance(answer, str) or not answer.strip():
        return make_fallback_answer(
            question,
            fields,
            validation,
            doc_type,
        )

    if not answerable:
        return {
            "answerable": False,
            "value": None,
            "answer": answer,
            "sources": [],
        }

    # Если модель утверждает, что ответила, но не предоставила источник,
    # используем безопасный ответ, основанный на детерминированной проверке.
    if not sources:
        return make_fallback_answer(
            question,
            fields,
            validation,
            doc_type,
        )

    return {
        "answerable": True,
        "value": value if isinstance(value, str) else None,
        "answer": answer.strip(),
        "sources": sources,
    }


@app.post("/api/check")
async def check_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    question: str = Form(...),
):
    if document_type not in DOCS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Неизвестный тип документа. Допустимые типы: "
                f"{', '.join(DOCS)}"
            ),
        )

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".pdf"}:
        raise HTTPException(
            status_code=415,
            detail="Поддерживаются JPG, PNG и PDF.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Загружен пустой файл.",
        )

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp:
            temp.write(contents)
            temp_path = temp.name

        text = run_ocr(temp_path, suffix)
        fields = extract_fields(text, document_type)

        # Даты приводятся к ISO, только если поле найдено.
        for key in DATE_FIELDS.intersection(fields):
            if fields[key] != NOT_FOUND:
                fields[key] = normalize_date(fields[key])

        validation = validate(fields, document_type)
        answer = await answer_question(
            question,
            fields,
            validation,
            document_type,
        )

        return {
            "document_type": document_type,
            "fields": fields,
            "validation": validation,
            "answers": [answer],
            "ocr_text": text,
        }

    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "document_types": list(DOCS),
    }
