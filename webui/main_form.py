import requests
import streamlit as st

from config import N8N_WEBHOOK_URL


def render_main_form():
    st.markdown('<div class="main-title">AI Property Triage System</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="sub-title">Real estate listing intake, analysis, routing, and reporting</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">Submit New Property Listing</div>', unsafe_allow_html=True)

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
        placeholder="Example: 3-room apartment in Haifa, asking price 1,200,000 ILS, renovated kitchen, balcony and parking.",
        height=170,
    )

    image_urls_text = st.text_area(
        "Image URLs",
        placeholder="Enter image URLs separated by commas",
        height=80,
    )

    uploaded_images = st.file_uploader(
        "Upload Property Images",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="main_property_images",
    )



    if st.button("Submit Listing"):
        submit_listing(
            agent_name,
            description,
            image_urls_text,
            uploaded_images,

        )


def submit_listing(agent_name, description, image_urls_text, uploaded_images):
    if not description.strip():
        st.warning("Please enter a property description.")
        return

    payload = {
        "agent_name": agent_name,
        "description": description,
        "image_urls": [url.strip() for url in image_urls_text.split(",") if url.strip()],
        "uploaded_image_names": [image.name for image in uploaded_images] if uploaded_images else [],
    }

    try:
        with st.spinner("Processing listing..."):
            response = requests.post(
                N8N_WEBHOOK_URL,
                json=payload,
                timeout=120,
            )

        try:
            result = response.json()
        except Exception:
            result = {
                "success": False,
                "status": "error",
                "message": response.text,
            }

        is_rejected = (
            result.get("success") is False
            or result.get("status") == "rejected"
            or response.status_code != 200
        )

        if is_rejected:
            st.markdown(
                '<div class="error-box">Listing was rejected or failed.</div>',
                unsafe_allow_html=True,
            )

            reason = result.get("reason") or result.get("message") or "No reason provided."
            st.error(reason)

            st.subheader("AI Report")
            st.json(result)
            return

        st.markdown(
            '<div class="success-box">Listing processed successfully.</div>',
            unsafe_allow_html=True,
        )

        st.subheader("AI Report")
        st.json(result)

    except requests.exceptions.ConnectionError:
        st.error("Could not connect to the analysis service.")

    except requests.exceptions.Timeout:
        st.error("The analysis service took too long to respond.")

    except Exception as error:
        st.error(f"Error: {error}")