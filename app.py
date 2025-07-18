import streamlit as st
from grok_search import GrokContractorSearch

# Set page config
st.set_page_config(
    page_title="SantoScore",
    page_icon="🔧",
    layout="wide"
)

# Initialize Grok search
@st.cache_resource
def get_grok_search():
    return GrokContractorSearch()

grok_search = get_grok_search()

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
</style>
""", unsafe_allow_html=True)

# Main title
st.title("SantaScore")
st.markdown("SantaScore helps you find and compare contractors using real customer reviews, ratings, and up-to-date web data. Each contractor receives a SantaScore (0-10) based on quality, reputation, and service.")

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

# Search and display results
if search_button:
    if not service_type.strip():
        st.error("Please enter a service type to search for contractors.")
    else:
        with st.spinner(f"Searching for {service_type} contractors..."):
            try:
                # Search for contractors
                contractors = grok_search.search_contractors(
                    service_type=service_type.strip(),
                    location=location.strip(),
                    max_results=max_results
                )
                
                if not contractors:
                    st.warning("No contractors found. Please try different search terms.")
                else:
                    # Sort contractors by quality score (highest first)
                    contractors.sort(key=lambda x: x.quality_score, reverse=True)
                    
                    # Display summary
                    st.success(f"Found {len(contractors)} contractors for {service_type}")
                    
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
                            <p><strong>Quality Score:</strong> <span class="{score_class}">{contractor.quality_score:.1f}/10</span></p>
                            <p><strong>Overall Rating:</strong> {contractor.rating}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Contact information
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**📞 Contact Information**")
                            if contractor.phone:
                                st.write(f"**Phone:** {contractor.phone}")
                            if contractor.email:
                                st.write(f"**Email:** {contractor.email}")
                            if contractor.website:
                                st.write(f"**Website:** {contractor.website}")
                            if contractor.address:
                                st.write(f"**Address:** {contractor.address}")
                        
                        with col2:
                            st.markdown("**🔧 Services & Description**")
                            if contractor.services:
                                st.write(f"**Services:** {contractor.services}")
                            if contractor.description:
                                st.write(f"**Description:** {contractor.description}")
                        
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
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.write("Please try again or check your API key.")

# Information when no search has been performed
else:
    st.info("👆 Enter a service type and location to search for contractors.")
    
    # No feature list or example search shown

# Footer
st.markdown("---")
st.markdown("SantaScore Contractor Search")