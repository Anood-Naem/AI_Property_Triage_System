from pathlib import Path
import html as html_lib
import re
import base64
import requests
import streamlit as st

from config import N8N_WEBHOOK_URL
from knowledgebase_service import store_report_in_knowledgebase


def load_report_styles():
    css_path = Path(__file__).parent / "report_styles.css"

    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as file:
            st.markdown(f"<style>{file.read()}</style>", unsafe_allow_html=True)


def render_main_form():
    load_report_styles()

    st.markdown(
        '<div class="main-title">AI Property Triage System</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sub-title">Real estate listing intake, analysis, routing, and reporting</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-title">Submit New Property Listing</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p class="small-text">Enter the property details below and submit them for analysis.</p>',
        unsafe_allow_html=True,
    )

    agent_name = st.text_input(
        "Listing Agent Name",
        placeholder="Example: Dana Cohen",
    )

    description = st.text_area(
        "Property Description",
        placeholder=(
            "Example: 3-room apartment in Haifa, asking price 1,200,000 ILS, "
            "renovated kitchen, balcony and parking."
        ),
        height=170,
    )

    image_urls_text = st.text_area(
        "Image URLs",
        placeholder="Enter image URLs separated by commas or new lines",
        height=80,
    )

    uploaded_images = st.file_uploader(
        "Upload Property Images",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="main_property_images",
    )

    if st.button("Submit Listing"):
        current_uploaded_images = (
            uploaded_images
            or st.session_state.get("main_property_images")
            or []
        )

        result = submit_listing(
            agent_name=agent_name,
            description=description,
            image_urls_text=image_urls_text,
            uploaded_images=current_uploaded_images,
        )

        if result:
            if result.get("status") == "success" and result.get("report"):
                kb_status = store_report_in_knowledgebase(result)
                result["_kb_status"] = kb_status

            st.session_state["last_listing_result"] = result

    if "last_listing_result" in st.session_state:
        render_n8n_result(st.session_state["last_listing_result"])


def build_uploaded_images_payload(uploaded_images):
    images_payload = []

    for image in uploaded_images or []:
        try:
            image_bytes = image.getvalue()

            if not image_bytes:
                continue

            images_payload.append(
                {
                    "filename": image.name or "uploaded_image.jpg",
                    "mime_type": image.type or "image/jpeg",
                    "base64": base64.b64encode(image_bytes).decode("utf-8"),
                }
            )

        except Exception as error:
            st.warning(
                f"Could not read uploaded image {getattr(image, 'name', '')}: {error}"
            )

    return images_payload


def parse_image_urls(image_urls_text):
    return [
        url.strip()
        for url in re.split(r"[\n,]+", image_urls_text or "")
        if url.strip()
    ]


def submit_listing(agent_name, description, image_urls_text, uploaded_images):
    if not description.strip():
        st.warning("Please enter a property description.")
        return None

    image_urls = parse_image_urls(image_urls_text)
    uploaded_images_payload = build_uploaded_images_payload(uploaded_images)

    payload = {
        "agent_name": agent_name,
        "description": description,
        "image_urls": image_urls,
        "uploaded_images": uploaded_images_payload,
        "uploaded_image_names": [
            image["filename"] for image in uploaded_images_payload
        ],
    }

    try:
        with st.spinner("Processing listing..."):
            response = requests.post(
                N8N_WEBHOOK_URL,
                json=payload,
                timeout=180,
            )

        try:
            result = response.json()
        except Exception:
            result = {
                "status": "error",
                "message": response.text,
            }

        result["_http_status_code"] = response.status_code

        # Source metadata for current report context and Pinecone Knowledge Base
        result["_source_agent_name"] = agent_name
        result["_source_description"] = description
        result["_source_image_urls"] = image_urls
        result["_source_uploaded_image_names"] = [
            image["filename"] for image in uploaded_images_payload
        ]

        return result

    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": "Could not connect to the n8n workflow. Make sure n8n is running.",
        }

    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "message": "The n8n workflow took too long to respond.",
        }

    except Exception as error:
        return {
            "status": "error",
            "message": f"Error: {error}",
        }


def get_user_friendly_rejection_message(reason):
    reason_lower = (reason or "").lower()

    if "prompt injection" in reason_lower:
        return (
            "This submission cannot be processed. "
            "Please enter only valid real estate listing details."
        )

    if "off-topic" in reason_lower or "not a property listing" in reason_lower:
        return (
            "This submission does not appear to be a valid real estate listing. "
            "Please provide property details such as type, location, price, rooms, and key features."
        )

    if "spam" in reason_lower or "promotional" in reason_lower:
        return (
            "This submission appears to contain spam or promotional content. "
            "Please submit a genuine property listing."
        )

    if "offensive" in reason_lower:
        return (
            "This submission contains inappropriate content and cannot be processed. "
            "Please revise the listing and try again."
        )

    if "too short" in reason_lower:
        return (
            "The property description is too short. "
            "Please provide more details about the listing."
        )

    return (
        "This submission could not be processed. "
        "Please make sure it contains a valid real estate listing."
    )


def render_n8n_result(result):
    status = result.get("status")
    http_status = result.get("_http_status_code", 200)

    if http_status != 200 or status == "error":
        st.markdown(
            '<div class="error-box">Listing was rejected or failed.</div>',
            unsafe_allow_html=True,
        )
        st.error(result.get("message", "Unknown error."))
        return

    if status == "success":
        st.markdown(
            '<div class="success-box">Listing processed successfully.</div>',
            unsafe_allow_html=True,
        )

        report = result.get("report")

        # Safety check:
        # If the report exists but was not stored yet, store it now.
        if report and "_kb_status" not in result:
            kb_status = store_report_in_knowledgebase(result)
            result["_kb_status"] = kb_status
            st.session_state["last_listing_result"] = result

        # kb_status = result.get("_kb_status")
        #
        # if isinstance(kb_status, dict):
        #     if kb_status.get("stored"):
        #         st.success("Knowledge Base: report saved successfully.")
        #     elif kb_status.get("message"):
        #         st.warning(kb_status.get("message"))
        #     else:
        #         st.warning("Knowledge Base: no status message returned.")
        # else:
        #     st.warning("Knowledge Base: no save status found.")

        if report:
            render_report_card(result)
        else:
            st.warning("n8n returned success, but no report field was found.")
            st.json(result)

        return

    if status == "rejected":
        st.markdown(
            '<div class="error-box">Submission could not be processed.</div>',
            unsafe_allow_html=True,
        )

        technical_reason = result.get("reason", "")
        friendly_message = get_user_friendly_rejection_message(technical_reason)

        st.error(friendly_message)
        return

    if status == "blocked":
        st.markdown(
            '<div class="error-box">Generated report requires human review.</div>',
            unsafe_allow_html=True,
        )

        st.warning(
            result.get(
                "reason",
                result.get("message", "The report requires human review."),
            )
        )

        report = result.get("report")

        if report and "_kb_status" not in result:
            kb_status = store_report_in_knowledgebase(result)
            result["_kb_status"] = kb_status
            st.session_state["last_listing_result"] = result

       # kb_status = result.get("_kb_status")

        # if isinstance(kb_status, dict):
        #     if kb_status.get("stored"):
        #         st.success("Knowledge Base: report saved successfully.")
        #     elif kb_status.get("message"):
        #         st.warning(kb_status.get("message"))

        if report:
            render_report_card(result)

        return

    st.warning("Received an unknown response from n8n.")
    st.json(result)


def get_report_value(report, label):
    patterns = [
        rf"\*\*{re.escape(label)}:\*\*\s*(.+)",
        rf"{re.escape(label)}:\s*(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, report, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            return value if value else "—"

    return "—"


def get_report_header(report):
    for line in report.splitlines():
        clean_line = line.strip()

        if clean_line.startswith("🏠"):
            return clean_line.replace("🏠", "").strip()

    return "Property Report"


def normalize_report_header(header, property_type, team):
    if header and header != "Property Report":
        parts = [part.strip().title() for part in header.split("·")]
        return " · ".join(parts)

    return f"{property_type.title()} · {team.title()}"


def extract_report_section(report, title):
    pattern = rf"##\s*{re.escape(title)}:?\s*(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, report, re.DOTALL | re.IGNORECASE)

    if not match:
        return ""

    return match.group(1).strip()


def is_meaningful_section(content):
    if not content:
        return False

    cleaned = str(content).strip().lower()

    empty_values = [
        "—",
        "-",
        "- —",
        "- —: —",
        "—: —",
        "no image analysis was provided.",
        "-: —",
        "-: — (—/5), confidence —",
        "-: (—/5), confidence —",
    ]

    if cleaned in empty_values:
        return False

    cleaned_letters = re.sub(r"[^a-zA-Zא-ת]+", "", cleaned)

    if cleaned_letters in ("", "confidence"):
        return False

    cleaned_without_symbols = re.sub(
        r"[\s\-\•\*:—_/().,%0-9]",
        "",
        cleaned,
    )

    return bool(cleaned_without_symbols)


def format_inline_markdown(text):
    escaped = html_lib.escape(str(text))
    escaped = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def markdown_list_to_html(content):
    if not is_meaningful_section(content):
        return ""

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    html_parts = []
    list_items = []

    def flush_list():
        nonlocal list_items

        if list_items:
            html_parts.append("<ul>" + "".join(list_items) + "</ul>")
            list_items = []

    for line in lines:
        is_bullet = line.startswith(("-", "*", "•"))

        if is_bullet:
            item = re.sub(r"^[-*•]\s*", "", line).strip()

            if is_meaningful_section(item):
                list_items.append(f"<li>{format_inline_markdown(item)}</li>")
        else:
            flush_list()
            html_parts.append(f"<p>{format_inline_markdown(line)}</p>")

    flush_list()
    return "".join(html_parts)


def build_report_section(title, content):
    section_html = markdown_list_to_html(content)

    if not section_html:
        return ""

    return (
        '<section class="report-inner-section">'
        f'<h3>{html_lib.escape(title)}</h3>'
        f'<div class="report-section-content">{section_html}</div>'
        '</section>'
    )


def render_report_card(result):
    report = result.get("report", "")
    team = str(result.get("team", "—")).title()
    property_type = str(result.get("property_type", "—")).title()

    report_header = normalize_report_header(
        get_report_header(report),
        property_type,
        team,
    )

    location = get_report_value(report, "Location")
    price = get_report_value(report, "Price")
    rooms = get_report_value(report, "Rooms")
    confidence = get_report_value(report, "Report confidence")

    key_features = extract_report_section(report, "Key features")
    image_analysis = extract_report_section(report, "Image analysis")
    similar_listings = extract_report_section(report, "Similar past listings")
    market_insight = extract_report_section(report, "Market insight")
    analyst_notes = extract_report_section(report, "Analyst notes")

    sections_html = "".join(
        [
            build_report_section("Key features", key_features),
            build_report_section("Image analysis", image_analysis),
            build_report_section("Similar past listings", similar_listings),
            build_report_section("Market insight", market_insight),
            build_report_section("Analyst notes", analyst_notes),
        ]
    )

    sections_container_html = ""

    if sections_html:
        sections_container_html = (
            '<div class="report-divider"></div>'
            '<div class="report-sections">'
            f'{sections_html}'
            '</div>'
        )

    report_html = (
        '<div class="report-wrapper">'
        '<div class="report-main-card unified-report-card">'
        '<div class="report-header-row">'
        '<div>'
        '<div class="report-status-pill">✅ Report received</div>'
        f'<h2>🏠 {html_lib.escape(report_header)}</h2>'
        '</div>'
        f'<div class="report-team-badge">{html_lib.escape(team)}</div>'
        '</div>'

        '<div class="report-kpi-grid">'
        '<div class="report-kpi">'
        '<span>Location</span>'
        f'<strong>{html_lib.escape(location)}</strong>'
        '</div>'

        '<div class="report-kpi">'
        '<span>Price</span>'
        f'<strong>{html_lib.escape(price)}</strong>'
        '</div>'

        '<div class="report-kpi">'
        '<span>Rooms</span>'
        f'<strong>{html_lib.escape(rooms)}</strong>'
        '</div>'

        '<div class="report-kpi">'
        '<span>Confidence</span>'
        f'<strong>{html_lib.escape(confidence)}</strong>'
        '</div>'
        '</div>'

        '<div class="report-meta">'
        f'Team: {html_lib.escape(team)} | Property Type: {html_lib.escape(property_type)}'
        '</div>'

        f'{sections_container_html}'

        '</div>'
        '</div>'
    )

    st.markdown("## Report")
    st.markdown(report_html, unsafe_allow_html=True)