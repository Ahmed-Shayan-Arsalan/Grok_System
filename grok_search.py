import os
import re
import json
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from dataclasses import dataclass, asdict

load_dotenv()

@dataclass
class Review:
    reviewer_name: str
    rating: str
    review_text: str
    date: str = ""
    source: str = ""

@dataclass
class Contractor:
    name: str
    phone: str = ""
    email: str = ""
    website: str = ""
    address: str = ""
    services: str = ""
    rating: str = ""
    description: str = ""
    license_status: str = ""
    reviews: List[Review] = None
    quality_score: float = 0.0

    def __post_init__(self):
        if self.reviews is None:
            self.reviews = []

class GrokContractorSearch:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("GROK_API_KEY"),
            base_url="https://api.x.ai/v1"
        )
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """
        Load system prompt from system.txt file
        """
        try:
            with open("system.txt", "r", encoding="utf-8") as file:
                return file.read().strip()
        except FileNotFoundError:
            print("Warning: system.txt not found. Using default system prompt.")
            return "You are a contractor search specialist. Help users find legitimate contractors and businesses."
        except Exception as e:
            print(f"Error loading system prompt: {e}")
            return "You are a contractor search specialist. Help users find legitimate contractors and businesses."
    
    def search_contractors(self, service_type: str, location: str = "", max_results: int = 15) -> List[Contractor]:
        """
        Search for contractors using Grok-4 API (web search)
        """
        # Enhanced user prompt with explicit requirement for exactly 5 reviews (Prompt Engineering)
        user_prompt = f"""I need to find {max_results} {service_type} contractors{' in ' + location if location else ''}.

Please search for legitimate contractors and businesses that provide {service_type} services.

For each contractor, provide the following information in this exact format (keep all fields as concise as possible):

CONTRACTOR 1:
Name: [Business Name]
Phone: [Phone Number]
Email: [Email Address if available]
Website: [Website URL if available]
Address: [Physical Address]
Services: [Services Offered]
Rating: [Overall Rating like 4.8/5 or 4.8 stars]
Description: [Brief Description, 1-2 sentences max]
License Status: [Active/Inactive/Unknown, and license number if available]
Reviews:
- Reviewer: John S. | Rating: 5/5 | Review: "Excellent service, very professional" | Date: 2024-01-15
- Reviewer: Sarah M. | Rating: 4/5 | Review: "Good work, arrived on time" | Date: 2024-01-10
- Reviewer: Mike D. | Rating: 5/5 | Review: "Outstanding quality and fair pricing" | Date: 2024-01-08
- Reviewer: Lisa R. | Rating: 4/5 | Review: "Professional team, clean work" | Date: 2024-01-12
- Reviewer: David K. | Rating: 5/5 | Review: "Highly recommend, great results" | Date: 2024-01-05

CRITICAL REQUIREMENTS:
1. Each contractor MUST have exactly 5 real customer reviews. If you cannot find 5, do not include the contractor at all.
2. All reviews must be real, with actual reviewer names, individual ratings, and specific review text. No placeholders or generic reviews.
3. Each review should be on a separate line with the format: Reviewer: [Name] | Rating: [Rating] | Review: "[Review text, 1-2 sentences max]" | Date: [Date]
4. Do NOT make up or pad reviews. Only use real, verifiable reviews.
5. Each contractor MUST include their active license status (Active/Inactive/Unknown) and license number if available.
6. Continue this format for all contractors."""
        
        try:
            # Single API call to get all contractor data
            response = self.client.chat.completions.create(
                model="grok-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            # Parse the response
            contractors = self._parse_response(response.choices[0].message.content)
            
            # Only use the reviews Grok returns (no padding, no extra API calls)
            # Calculate quality scores for all contractors
            contractors = self._calculate_quality_scores(contractors, service_type)
            
            # Limit results to max_results
            return contractors[:max_results]
        except Exception as e:
            print(f"Error searching contractors: {e}")
            return []
    
    def _parse_response(self, content: str) -> List[Contractor]:
        """
        Parse Grok's response to extract contractor information including reviews
        """
        contractors = []
        
        # Split by CONTRACTOR sections
        sections = re.split(r'CONTRACTOR\s+\d+:', content)
        
        for section in sections[1:]:  # Skip the first empty section
            if not section.strip():
                continue
                
            contractor_data = self._extract_contractor_info(section)
            if contractor_data.get('name'):
                contractors.append(Contractor(**contractor_data))
        
        # If structured parsing fails, try alternative parsing
        if not contractors:
            contractors = self._parse_alternative_format(content)
        
        return contractors
    
    def _extract_contractor_info(self, text: str) -> Dict[str, Any]:
        """
        Extract contractor information from a text section including reviews
        """
        data = {
            'name': '',
            'phone': '',
            'email': '',
            'website': '',
            'address': '',
            'services': '',
            'rating': '',
            'description': '',
            'license_status': '',
            'reviews': []
        }
        
        lines = text.split('\n')
        reviews_section = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if we're in the reviews section
            if line.lower().startswith('reviews:'):
                reviews_section = True
                continue
            
            # If we're in reviews section, parse review lines
            if reviews_section:
                # Check if this line is a review with the specified format
                if line.startswith('- Reviewer:') or line.startswith('Reviewer:'):
                    review = self._parse_single_review(line)
                    if review:
                        data['reviews'].append(review)
                elif any(line.lower().startswith(field + ':') for field in ['name', 'phone', 'email', 'website', 'address', 'services', 'rating', 'description', 'license status']):
                    reviews_section = False
                else:
                    # Try to parse as a different review format
                    review = self._parse_alternative_review_format(line)
                    if review:
                        data['reviews'].append(review)
            
            # Extract other information based on field labels
            if not reviews_section:
                if line.lower().startswith('name:'):
                    data['name'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('phone:'):
                    data['phone'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('email:'):
                    data['email'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('website:'):
                    data['website'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('address:'):
                    data['address'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('services:'):
                    data['services'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('rating:'):
                    data['rating'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('description:'):
                    data['description'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('license status:'):
                    data['license_status'] = line.split(':', 1)[1].strip()
        
        return data
    
    def _parse_single_review(self, line: str) -> Review:
        """
        Parse a single review line in the format: Reviewer: Name | Rating: X/5 | Review: "Text" | Date: YYYY-MM-DD
        """
        try:
            # Remove leading dash and 'Reviewer:' prefix
            line = line.lstrip('- ').replace('Reviewer:', '').strip()
            
            # Split by | to get components
            parts = [part.strip() for part in line.split('|')]
            
            reviewer_name = ""
            rating = ""
            review_text = ""
            date = ""
            
            for part in parts:
                if part.lower().startswith('rating:'):
                    rating = part.split(':', 1)[1].strip()
                elif part.lower().startswith('review:'):
                    review_text = part.split(':', 1)[1].strip().strip('"\'')
                elif part.lower().startswith('date:'):
                    date = part.split(':', 1)[1].strip()
                elif not reviewer_name and not any(part.lower().startswith(prefix) for prefix in ['rating:', 'review:', 'date:']):
                    reviewer_name = part.strip()
            
            # Only return review if we have both reviewer name and review text
            if reviewer_name and review_text:
                return Review(
                    reviewer_name=reviewer_name,
                    rating=rating,
                    review_text=review_text,
                    date=date,
                    source="Web Search"
                )
        except Exception as e:
            print(f"Error parsing review line: {e}")
        
        return None
    
    def _parse_alternative_review_format(self, line: str) -> Review:
        """
        Parse reviews in alternative formats that Grok might return - NO hardcoded fallbacks
        """
        try:
            # Pattern: "John S. - 5/5 stars - Great service!"
            pattern1 = r'([A-Z][a-z]+\s+[A-Z]\.?)\s*[-–]\s*(\d+(?:\.\d+)?(?:/5|/10|\s*stars?))\s*[-–]\s*["\']?([^"\']+)["\']?'
            match1 = re.search(pattern1, line)
            if match1:
                return Review(
                    reviewer_name=match1.group(1),
                    rating=match1.group(2),
                    review_text=match1.group(3),
                    source="Web Search"
                )
            
            # Pattern: "Sarah M. (4/5): Excellent work done quickly"
            pattern2 = r'([A-Z][a-z]+\s+[A-Z]\.?)\s*\((\d+(?:\.\d+)?(?:/5|/10|\s*stars?))\):\s*["\']?([^"\']+)["\']?'
            match2 = re.search(pattern2, line)
            if match2:
                return Review(
                    reviewer_name=match2.group(1),
                    rating=match2.group(2),
                    review_text=match2.group(3),
                    source="Web Search"
                )
            
            # Pattern: Look for quoted reviews with names and ratings nearby - ONLY if all parts are found
            quote_pattern = r'["\']([^"\']{20,})["\']'
            name_pattern = r'([A-Z][a-z]+\s+[A-Z]\.?)'
            rating_pattern = r'(\d+(?:\.\d+)?(?:/5|/10|\s*stars?))'
            
            quote_match = re.search(quote_pattern, line)
            name_match = re.search(name_pattern, line)
            rating_match = re.search(rating_pattern, line)
            
            # Only return if we found both name and review text
            if quote_match and name_match:
                return Review(
                    reviewer_name=name_match.group(1),
                    rating=rating_match.group(1) if rating_match else "",
                    review_text=quote_match.group(1),
                    source="Web Search"
                )
        except Exception as e:
            print(f"Error parsing alternative review format: {e}")
        
        return None
    

    def _calculate_quality_scores(self, contractors: List[Contractor], service_type: str) -> List[Contractor]:
        """
        Calculate quality scores for contractors using Grok API (now using grok-3-fast for speed)
        """
        try:
            # Prepare contractor data for scoring
            contractor_data = []
            for contractor in contractors:
                contractor_info = {
                    "name": contractor.name,
                    "rating": contractor.rating,
                    "services": contractor.services,
                    "description": contractor.description,
                    "license_status": contractor.license_status,
                    "reviews": [{"reviewer": r.reviewer_name, "rating": r.rating, "text": r.review_text} for r in contractor.reviews]
                }
                contractor_data.append(contractor_info)
            
            scoring_prompt = f"""You are an expert evaluator of {service_type} contractors. Based on the provided contractor information, rate each contractor on a scale of 0-10 (where 10 is the best and 0 is the worst).

Consider these factors when scoring:
1. Overall rating/reputation
2. Quality of services offered
3. Customer review sentiment and ratings
4. Completeness of contact information
5. Professional description and experience

Here are the contractors to evaluate:
{json.dumps(contractor_data, indent=2)}

For each contractor, provide a score from 0-10 and a brief explanation (1-2 sentences max). Format your response as:

CONTRACTOR: [Name]
SCORE: [0-10 score]
EXPLANATION: [Brief explanation of why this score was given, 1-2 sentences max]

Continue for all contractors."""
            
            response = self.client.chat.completions.create(
                model="grok-3-fast",
                messages=[
                    {"role": "system", "content": "You are a professional contractor evaluation expert. Provide objective scores based on the information provided."},
                    {"role": "user", "content": scoring_prompt}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            # Parse scores and assign to contractors
            scores = self._parse_quality_scores(response.choices[0].message.content)
            
            # Assign scores to contractors
            for i, contractor in enumerate(contractors):
                if i < len(scores):
                    contractor.quality_score = scores[i]
                else:
                    contractor.quality_score = 5.0  # Default score if not found
            
            return contractors
            
        except Exception as e:
            print(f"Error calculating quality scores: {e}")
            # Return contractors with default scores if scoring fails
            for contractor in contractors:
                contractor.quality_score = 5.0
            return contractors
    
    def _parse_quality_scores(self, content: str) -> List[float]:
        """
        Parse quality scores from Grok's response
        """
        scores = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('SCORE:'):
                try:
                    score_text = line.split(':', 1)[1].strip()
                    # Extract numeric score
                    score_match = re.search(r'(\d+(?:\.\d+)?)', score_text)
                    if score_match:
                        score = float(score_match.group(1))
                        # Ensure score is between 0 and 10
                        score = max(0, min(10, score))
                        scores.append(score)
                except (ValueError, IndexError):
                    scores.append(5.0)  # Default score if parsing fails
        
        return scores
    
    def _parse_alternative_format(self, content: str) -> List[Contractor]:
        """
        Alternative parsing method for different response formats
        """
        contractors = []
        lines = content.split('\n')
        
        current_contractor = {'reviews': []}
        business_name_pattern = r'^[A-Z][A-Za-z\s&\-\'\.\,\(\)]+(?:LLC|Inc|Corporation|Corp|Company|Co\.|Services|Solutions|Group)?$'
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for business names
            if re.match(business_name_pattern, line) and len(line) > 5 and len(line) < 100:
                if current_contractor and current_contractor.get('name'):
                    contractors.append(Contractor(**current_contractor))
                    current_contractor = {'reviews': []}
                current_contractor['name'] = line
            
            # Extract other information...
            phone_match = re.search(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b', line)
            if phone_match:
                current_contractor['phone'] = phone_match.group()
            
            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', line)
            if email_match:
                current_contractor['email'] = email_match.group()
            
            website_match = re.search(r'https?://[^\s]+|www\.[^\s]+', line)
            if website_match:
                current_contractor['website'] = website_match.group()
            
            if re.search(r'\b\d+\s+[A-Za-z\s]+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Way|Ct|Court)\b', line):
                current_contractor['address'] = line
            
            rating_match = re.search(r'(\d+\.?\d*)\s*(?:\/\s*5|\s*stars?|\s*out\s*of\s*5)', line, re.IGNORECASE)
            if rating_match:
                current_contractor['rating'] = rating_match.group()
            
            # Parse reviews in alternative format - only if valid data found
            review = self._parse_alternative_review_format(line)
            if review:
                if 'reviews' not in current_contractor:
                    current_contractor['reviews'] = []
                current_contractor['reviews'].append(review)
        
        # Add last contractor if exists
        if current_contractor and current_contractor.get('name'):
            contractors.append(Contractor(**current_contractor))
        
        return contractors
