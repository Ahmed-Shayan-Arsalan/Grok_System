import streamlit as st
from grok_search import GrokContractorSearch
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import time
import re
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Persistent notification bar logic
if 'show_email_notification' not in st.session_state:
    st.session_state['show_email_notification'] = False
if 'email_notification_time' not in st.session_state:
    st.session_state['email_notification_time'] = 0

# Show persistent notification bar if needed
if st.session_state.get('show_email_notification', False):
    st.markdown('''
    <div style="position:fixed;top:80px;right:20px;z-index:9999;background:#28a745;color:white;padding:16px 32px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.15);font-size:1.1em;">
        ✅ Email sent successfully!
    </div>
    ''', unsafe_allow_html=True)
    # If 4 seconds have passed, hide the notification and rerun
    if time.time() - st.session_state['email_notification_time'] > 4:
        st.session_state['show_email_notification'] = False
        st.experimental_rerun()

# Set page config
st.set_page_config(
   page_title="SantoScore v0.2",
    page_icon="🔧",
    layout="wide"
)

# Initialize session state
if 'search_results' not in st.session_state:
   st.session_state.search_results = None
if 'search_params' not in st.session_state:
   st.session_state.search_params = None

# Initialize Grok search
@st.cache_resource
def get_grok_search():
    return GrokContractorSearch()

grok_search = get_grok_search()

# Email configuration

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# Add validation to ensure credentials are loaded
if not SENDER_EMAIL or not SENDER_PASSWORD:
    st.error("Email credentials not found. Please check your .env file.")
    st.stop()

# Validation functions

def is_valid_email(email):
    if not email:
        return False
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w{2,}$"
    return re.match(pattern, email) is not None

def is_valid_website(url):
    if not url:
        return False
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False

def is_valid_phone(phone):
    if not phone:
        return False
    # Accepts (123) 456-7890, 123-456-7890, 1234567890, +1 123 456 7890, etc.
    pattern = r"^(\+\d{1,3}[- ]?)?(\(?\d{3}\)?[- ]?)?\d{3}[- ]?\d{4}$"
    return re.match(pattern, phone) is not None

# Enhanced website validation function
def is_website_safe_for_display(url):
    """Additional validation for displaying websites to users"""
    if not url or not url.strip():
        return False, "No website provided"
    
    # Use the same validation as in grok_search.py
    from grok_search import validate_website_safety
    return validate_website_safety(url)

# Function to send email
def send_quote_request(contractor_name, contractor_email, user_email, problem_statement, send_to_business, contractor_details=None):
    try:
        # --- Main email to sales@santoelectronics.com (unchanged) ---
        msg = MIMEMultipart('alternative')
        msg['From'] = SENDER_EMAIL
        msg['Subject'] = f"🔧 Quote Request for {contractor_name} - SantoScore"
        # Create HTML email body with all business details
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; border-radius: 10px;">
                <h2 style="color: #007bff; text-align: center; border-bottom: 3px solid #007bff; padding-bottom: 10px;">
                    🔧 New Quote Request via SantoScore
                </h2>
                
                <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h3 style="color: #28a745; margin-top: 0;">📋 Contractor Information</h3>
                    <p><strong>Business Name:</strong> {contractor_name}</p>
                    {f'<p><strong>Phone:</strong> {contractor_details.phone}</p>' if contractor_details and contractor_details.phone else ''}
                    {f'<p><strong>Email:</strong> {contractor_details.email}</p>' if contractor_details and contractor_details.email else ''}
                    {f'<p><strong>Website:</strong> <a href="{contractor_details.website}" target="_blank">{contractor_details.website}</a></p>' if contractor_details and contractor_details.website else ''}
                    {f'<p><strong>Address:</strong> {contractor_details.address}</p>' if contractor_details and contractor_details.address else ''}
                    {f'<p><strong>License Status:</strong> <span style="color: #28a745; font-weight: bold;">{contractor_details.license_status}</span></p>' if contractor_details and contractor_details.license_status else ''}
                    {f'<p><strong>Services Offered:</strong> {contractor_details.services}</p>' if contractor_details and contractor_details.services else ''}
                    {f'<p><strong>Quality Score:</strong> <span style="color: #007bff; font-weight: bold; font-size: 1.1em;">{contractor_details.quality_score:.1f}/10</span></p>' if contractor_details and hasattr(contractor_details, 'quality_score') else ''}
                    {f'<p><strong>Overall Rating:</strong> <span style="color: #ffc107; font-weight: bold;">{contractor_details.rating}</span></p>' if contractor_details and contractor_details.rating else ''}
                    {f'<p style="color: #dc3545; font-weight: bold;">Note: This business could not be emailed directly as no business email was found.</p>' if not contractor_email else ''}
                </div>
                
                <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h3 style="color: #dc3545; margin-top: 0;">👤 Customer Information</h3>
                    <p><strong>Customer Email:</strong> <a href="mailto:{user_email}">{user_email}</a></p>
                    <p><strong>Service Request:</strong></p>
                    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; border-radius: 4px; margin: 10px 0;">
                        <em>"{problem_statement}"</em>
                    </div>
                </div>
                
                {f'''
                <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h3 style="color: #6f42c1; margin-top: 0;">📝 Business Description</h3>
                    <p>{contractor_details.description}</p>
                </div>
                ''' if contractor_details and contractor_details.description else ''}
                
                <div style="background-color: #e9ecef; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Quote Request Settings:</strong></p>
                    <p style="margin: 5px 0; color: {'#28a745' if send_to_business else '#dc3545'};">
                        Send to Business: <strong>{'✅ Yes' if send_to_business else '❌ No'}</strong>
                    </p>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <p style="background-color: #007bff; color: white; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <strong>Please follow up with this customer regarding their service needs.</strong>
                    </p>
                    <p style="font-size: 0.9em; color: #666;">
                        This quote request was generated via <strong>SantoScore</strong> - Your trusted contractor search platform
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        # Create plain text version as fallback
        text_body = f"""
        New Quote Request via SantoScore
        ================================
        
        CONTRACTOR INFORMATION:
        -----------------------
        Business Name: {contractor_name}
        {"Phone: " + contractor_details.phone if contractor_details and contractor_details.phone else ""}
        {"Email: " + contractor_details.email if contractor_details and contractor_details.email else ""}
        {"Website: " + contractor_details.website if contractor_details and contractor_details.website else ""}
        {"Address: " + contractor_details.address if contractor_details and contractor_details.address else ""}
        {"License Status: " + contractor_details.license_status if contractor_details and contractor_details.license_status else ""}
        {"Services: " + contractor_details.services if contractor_details and contractor_details.services else ""}
        {"Quality Score: " + str(contractor_details.quality_score) + "/10" if contractor_details and hasattr(contractor_details, 'quality_score') else ""}
        {"Overall Rating: " + contractor_details.rating if contractor_details and contractor_details.rating else ""}
        {"NOTE: This business could not be emailed directly as no business email was found." if not contractor_email else ""}
        
        CUSTOMER INFORMATION:
        ---------------------
        Customer Email: {user_email}
        Service Request: {problem_statement}
        
        {"BUSINESS DESCRIPTION:" if contractor_details and contractor_details.description else ""}
        {"--------------------" if contractor_details and contractor_details.description else ""}
        {contractor_details.description if contractor_details and contractor_details.description else ""}
        
        QUOTE REQUEST SETTINGS:
        -----------------------
        Send to Business: {'Yes' if send_to_business else 'No'}
        
        Please follow up with this customer regarding their service needs.
        
        This quote request was generated via SantoScore - Your trusted contractor search platform
        """
        # Attach both HTML and plain text versions
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        # Determine recipients
        recipients = ["sales@santoelectronics.com"]
        # Do not send to contractor email for now, even if send_to_business is True
        # if send_to_business and contractor_email:
        #     recipients.append(contractor_email)
        msg['To'] = ', '.join(recipients)
        # --- Send main email to sales only ---
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        # --- Do NOT send a separate email to the business (feature disabled for now) ---
        # (business email logic is fully commented out)
        return True, "Quote request sent successfully!"
    except Exception as e:
        return False, f"Error sending quote request: {str(e)}"

# Custom CSS for styling
st.markdown("""
<style>
    .contractor-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        background-color: #f9f9f9;
    }
    .score-high { color: #28a745; font-weight: bold; font-size: 1.2em; }
    .score-medium { color: #ffc107; font-weight: bold; font-size: 1.2em; }
    .score-low { color: #dc3545; font-weight: bold; font-size: 1.2em; }
    .review-item {
        background-color: white;
        padding: 15px;
        margin: 8px 0;
        border-radius: 8px;
        border-left: 4px solid #007bff;
    }
    .rank-badge {
        display: inline-block;
        background-color: #007bff;
        color: white;
        padding: 5px 10px;
        border-radius: 15px;
        font-weight: bold;
        margin-right: 10px;
    }
   .quote-button {
       background-color: #28a745;
       color: white;
       padding: 8px 16px;
       border-radius: 5px;
       text-decoration: none;
       font-weight: bold;
       margin-top: 10px;
   }
</style>
""", unsafe_allow_html=True)

# Main title
st.title("SantoScore")
st.markdown("SantoScore helps you find and compare contractors using real customer reviews, ratings, and up-to-date web data. Each contractor receives a SantoScore (0-10) based on quality, reputation, and service.")

# Search form
with st.form("search_form"):
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        service_type = st.text_input("Service Type", placeholder="e.g., plumber, electrician, roofer")
    
    with col2:
        location = st.text_input("Location", placeholder="e.g., New York, NY")
    
    with col3:
        max_results = st.selectbox("Results", options=[5, 10, 15, 20], index=0)
    
    search_button = st.form_submit_button("🔍 Search Contractors", type="primary")

# Handle search
if search_button:
    if not service_type.strip():
        st.error("Please enter a service type to search for contractors.")
    else:
        with st.spinner(f"Searching for {service_type} contractors..."):
            try:
                # Store search parameters
                st.session_state.search_params = {
                    'service_type': service_type.strip(),
                    'location': location.strip(),
                    'max_results': max_results
                }
                # Search for contractors
                contractors = grok_search.search_contractors(
                    service_type=service_type.strip(),
                    location=location.strip(),
                    max_results=max_results
                )
                if contractors:
                    # Sort contractors by quality score (highest first)
                    contractors.sort(key=lambda x: x.quality_score, reverse=True)
                    st.session_state.search_results = contractors
                else:
                    st.session_state.search_results = []
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.write("Please try again or check your API key.")

# Display results from session state
if st.session_state.search_results is not None:
    contractors = st.session_state.search_results
    if not contractors:
        st.warning("No contractors found. Please try different search terms.")
    else:
        # Display summary
        params = st.session_state.search_params
        st.success(f"Found {len(contractors)} contractors for {params['service_type']}")
        st.markdown("---")
        # Display contractors
        for i, contractor in enumerate(contractors, 1):
            # Quality score color coding
            if contractor.quality_score >= 8:
                score_class = "score-high"
            elif contractor.quality_score >= 6:
                score_class = "score-medium"
            else:
                score_class = "score-low"
            # Contractor card
            st.markdown(f"""
            <div class="contractor-card">
                <h3>
                    <span class="rank-badge">#{i}</span>
                    {contractor.name}
                </h3>
                <p><strong>SantoScore:</strong> <span class="{score_class}">{contractor.quality_score:.1f}/10</span></p>
            </div>
            """, unsafe_allow_html=True)
            # Contact information and Quote button
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.markdown("**📞 Contact Information**")
                if is_valid_phone(contractor.phone):
                    st.write(f"**Phone:** {contractor.phone}")
                else:
                    st.write("**Phone:** N/A")
                if is_valid_email(contractor.email):
                    st.write(f"**Email:** {contractor.email}")
                else:
                    st.write("**Email:** N/A")
                if contractor.website:
                    is_safe, reason = is_website_safe_for_display(contractor.website)
                    if is_safe:
                        st.write(f"**Website:** {contractor.website}")
                    else:
                        st.write("**Website:** N/A (safety concerns)")
                else:
                    st.write("**Website:** N/A")
                if contractor.address:
                    st.write(f"**Address:** {contractor.address}")
                if contractor.license_status:
                    st.write(f"**License Status:** {contractor.license_status}")
            with col2:
                st.markdown("**🔧 Services & Description**")
                if contractor.services:
                    st.write(f"**Services:** {contractor.services}")
                if contractor.description:
                    st.write(f"**Description:** {contractor.description}")
            with col3:
                st.markdown("**📝 Request Quote**")
                if st.button(f"Get Quote", key=f"quote_{i}"):
                    st.session_state[f"show_quote_form_{i}"] = True
            # Quote form (shown when button is clicked)
            if st.session_state.get(f"show_quote_form_{i}", False):
                with st.container():
                    st.markdown("---")
                    st.markdown(f"### Quote Request Form for {contractor.name}")
                    # Use columns for better layout
                    form_col1, form_col2 = st.columns([2, 1])
                    with form_col1:
                        user_email = st.text_input("Your Email*", key=f"email_{i}")
                        st.caption("Your email is secure. We will never share your email address.")
                        problem_statement = st.text_area(
                            "Problem Statement*", 
                            placeholder="Please describe the work you need done...",
                            key=f"problem_{i}",
                            height=100
                        )
                        send_to_business = st.checkbox(
                            "Send quote request to the business as well",
                            value=False,
                            key=f"send_business_{i}"
                        )
                    with form_col2:
                        st.markdown("**Quote Details:**")
                        st.info(f"Contractor: {contractor.name}")
                        if contractor.email and send_to_business:
                            st.info(f"Will be sent to: {contractor.email}")
                    # Action buttons
                    button_col1, button_col2 = st.columns([1, 1])
                    with button_col1:
                        if st.button("Send Quote Request", key=f"submit_{i}", type="primary"):
                            if not user_email or not problem_statement:
                                st.error("Please fill in all required fields.")
                            elif not is_valid_email(user_email):
                                st.error("Please enter a valid email address.")
                            elif send_to_business and contractor.email and not is_valid_email(contractor.email):
                                st.error("This contractor's email is invalid. Cannot send to business.")
                            else:
                                success, message = send_quote_request(
                                    contractor.name,
                                    contractor.email if is_valid_email(contractor.email) else None,
                                    user_email,
                                    problem_statement,
                                    send_to_business,
                                    contractor  # Pass all contractor details
                                )
                                if success:
                                    st.success(message)
                                    st.session_state['show_email_notification'] = True
                                    st.session_state['email_notification_time'] = time.time()
                                    # Clear the form
                                    st.session_state[f"show_quote_form_{i}"] = False
                                    st.rerun()
                                else:
                                    st.error(message)
                    with button_col2:
                        if st.button("Cancel", key=f"cancel_{i}"):
                            st.session_state[f"show_quote_form_{i}"] = False
                            st.rerun()
                    
                    # Santo Electronics membership section
                    st.markdown("---")
                    
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.markdown("**If you are not a member, join us now!**")
                        st.markdown("""
                        <a href="https://www.santoelectronics.com/premium" target="_blank">
                            <button style='background-color: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; font-weight: bold; width: 100%;'>Signup</button>
                        </a>
                        """, unsafe_allow_html=True)
                    with col2:
                        st.markdown("**If you are a member, login here:**")
                        st.markdown("""
                        <a href="https://www.santoelectronics.com/account/login" target="_blank">
                            <button style='background-color: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 5px; font-weight: bold; width: 100%;'>Login</button>
                        </a>
                        """, unsafe_allow_html=True)
                    st.markdown("---")
            # Reviews section
            st.markdown("**⭐ Customer Reviews**")
            if contractor.reviews:
                for review in contractor.reviews:
                    st.markdown(f"""
                    <div class="review-item">
                        <strong>{review.reviewer_name}</strong>
                        {f" • {review.rating}" if review.rating else ""}
                        {f" • {review.date}" if review.date else ""}
                        <br><br>
                        "{review.review_text}"
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.write("No reviews available")
            st.markdown("---")

# Information when no search has been performed
elif st.session_state.search_results is None:
    st.info("👆 Enter a service type and location to search for contractors.")

# Footer
st.markdown("---")
st.markdown("SantoScore v1.0 Contractor Search")
