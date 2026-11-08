
import re
import unicodedata


def normalize_text(text: str) -> str:
    """
    Standardize an RFQ message before extracting information.

    Operations:
    1. Unicode normalization
    2. Convert to lowercase
    3. Remove leading and trailing spaces
    4. Replace repeated spaces with a single space
    """

    # Standardize Unicode characters
    text = unicodedata.normalize("NFKC", text)

    # Convert text to lowercase
    text = text.lower()

    # Remove spaces at the beginning and end
    text = text.strip()

    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)

    return text


def extract_category(text: str):
    """
    Identify the packaging category from an RFQ message.

    Returns one of the seven allowed categories,
    or None if no recognizable category is found.
    """

    text = normalize_text(text)

    # 1. BOPP bags: check specific bag-related descriptions.
    if re.search(
        r"\bbopp\b.*\b(bags?|sacks?)\b",
        text
    ) or re.search(
        r"\bbags?\b.*\bbopp\b",
        text
    ):
        return "bopp_bag"

    # 2. FIBC products.
    if re.search(r"\b(fibc|jumbo|bulk)\b", text):
        return "fibc"

    # 3. Woven sacks.
    if re.search(
        r"\b(woven\s+sacks?|woven\s+bags?|"
        r"cement\s+bags?|cement\s+sacks?|ad\s*star)\b",
        text
    ):
        return "woven_sack"

    # 4. Corrugated boxes and plain boxes.
    if re.search(r"\b(corrugated\s+)?box(?:es)?\b", text):
        return "corrugated_box"

    # 5. Mono cartons.
    if re.search(r"\bmono\s*cartons?\b", text):
        return "mono_carton"

    # 6. Pouches.
    if re.search(r"\bpouch(?:es)?\b", text):
        return "pouch"

    # 7. Film, including shrink wrap and stretch wrap.
    if re.search(
        r"\b(shrink|stretch)\s+(film|wrap)\b",
        text
    ):
        return "film"

    if re.search(r"\bfilm\b", text):
        return "film"

    return None



# Multipliers for Indian and international number words
NUMBER_MULTIPLIERS = {
    "k": 1000,
    "thousand": 1000,
    "hazar": 1000,
    "hazaar": 1000,
    "hajaar": 1000,
    "lakh": 100000,
    "lakhs": 100000,
    "lac": 100000,
    "lacs": 100000,
    "crore": 10000000,
    "crores": 10000000,
    "million": 1000000,
}


def convert_number(value: str):
    """
    Convert a number expression into an int or float.

    Examples:
        "40 hazaar" -> 40000
        "2.5 lac"   -> 250000
        "15K"       -> 15000
        "1,50,000"  -> 150000
    """

    value = normalize_text(value)

    # Remove commas used as number separators.
    value = value.replace(",", "")

    # Match a numeric value and an optional multiplier.
    match = re.fullmatch(
        r"(\d+(?:\.\d+)?)\s*([a-z]+)?",
        value
    )

    if not match:
        return None

    number = float(match.group(1))
    suffix = match.group(2)

    if suffix:
        if suffix not in NUMBER_MULTIPLIERS:
            return None

        number *= NUMBER_MULTIPLIERS[suffix]

    # Return whole numbers as integers.
    if number.is_integer():
        return int(number)

    return number


def extract_number_candidates(text: str) -> list:
    """
    Extract numeric expressions from a complete RFQ message.

    Each result contains:
    - value: Converted numerical value
    - raw: Original numeric expression
    - start: Starting character position
    - end: Ending character position
    """

    text = normalize_text(text)

    number_words = "|".join(
        sorted(NUMBER_MULTIPLIERS.keys(), key=len, reverse=True)
    )

    pattern = (
        r"(?<![\w.])"
        r"(\d[\d,]*(?:\.\d+)?)"
        r"\s*"
        r"(" + number_words + r")?"
        r"(?!\w)"
    )

    candidates = []

    for match in re.finditer(pattern, text):

        raw = match.group(0).strip()

        value = convert_number(raw)

        if value is None:
            continue

        candidates.append({
            "value": value,
            "raw": raw,
            "start": match.start(),
            "end": match.end()
        })

    return candidates


def classify_number_candidate(text: str, candidate: dict) -> dict:
    """
    Classify a number based on its surrounding context.

    Possible roles:
        - capacity
        - specification
        - quantity_candidate
    """

    text = normalize_text(text)

    start = candidate["start"]
    end = candidate["end"]

    # Examine nearby words before and after the number.
    
    after = text[end:end + 40]

    # Rule 1: Exclude GSM specifications.
    if re.match(r"\s*gsm\b", after):
        return {
            **candidate,
            "role": "specification",
            "unit": None
        }

    # Rule 2: Exclude micron specifications.
    if re.match(r"\s*(mic|micron|microns)\b", after):
        return {
            **candidate,
            "role": "specification",
            "unit": None
        }

    # Rule 3: Exclude bag capacity.
    if re.match(
        r"\s*(kg|kgs|kilograms?)\s+(bag\s+)?capacity\b",
        after
    ) or re.match(
        r"\s*capacity\b",
        after
    ):
        return {
            **candidate,
            "role": "capacity",
            "unit": None
        }

    # Rule 4: Exclude fill weight, such as 25 kg bag.
    if re.match(
        r"\s*(kg|kgs|kilograms?)\s+bag\b",
        after
    ):
        return {
            **candidate,
            "role": "capacity",
            "unit": None
        }

    # Rule 5: Recognize item counts.
    if re.match(
        r"\s*(pcs?|pieces?|units?)\b",
        after
    ):
        return {
            **candidate,
            "role": "quantity_candidate",
            "unit": "pcs"
        }

    # Rule 6: Recognize metric tonnes.
    if re.match(
    r"\s*(mt|ton|tons|tonne|tonnes)\b",
    after
    ):
        return {
        **candidate,
        "role": "quantity_candidate",
        "unit": "mt"
    }

    # Rule 7: Recognize weight-based quantities.
    if re.match(
        r"\s*(kg|kgs|kilograms?)\b",
        after
    ):
        return {
            **candidate,
            "role": "quantity_candidate",
            "unit": "kg"
        }

    # Rule 8: A number without an explicit unit.
    # It remains a possible quantity, not a confirmed one.
    return {
        **candidate,
        "role": "quantity_candidate",
        "unit": None
    }


def extract_quantity(text: str):
    """
    Extract the actual order quantity and unit.

    Returns:
        (quantity, unit)

    Example:
        "Need 500 pcs" -> (500, "pcs")
    """

    text = normalize_text(text)

    candidates = extract_number_candidates(text)

    classified = [
        classify_number_candidate(text, candidate)
        for candidate in candidates
    ]

    # Keep only actual quantity candidates.
    valid = [
        item for item in classified
        if item["role"] == "quantity_candidate"
    ]

    if not valid:
        return None, None

    # Prefer candidates with explicitly stated units.
    explicit = [
        item for item in valid
        if item["unit"] is not None
    ]

    if explicit:

        # Prefer item count (pcs) when both pcs and
        # capacity/weight information are present.
        pcs_candidates = [
            item for item in explicit
            if item["unit"] == "pcs"
        ]

        if pcs_candidates:
            selected = pcs_candidates[-1]
        else:
            selected = explicit[-1]

        return selected["value"], selected["unit"]

    # If no unit is stated, infer pieces from a
    # packaging product description.
    return valid[-1]["value"], "pcs"

def extract_gsm(text: str):
    text = normalize_text(text)

    match = re.search(r"\b(\d+(?:\.\d+)?)\s*gsm\b", text)

    if not match:
        return None

    return int(float(match.group(1)))


def extract_micron(text: str):
    text = normalize_text(text)

    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(?:mic|micron|microns)\b",
        text
    )

    if not match:
        return None

    return int(float(match.group(1)))

INDIAN_LOCATIONS = [
    # States
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",

    # Union Territories
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Puducherry",
    "Chandigarh",

    # Common Indian cities
    "Mumbai",
    "Pune",
    "Nagpur",
    "Nashik",
    "Aurangabad",
    "Kolhapur",
    "Thane",
    "Navi Mumbai",
    "Bengaluru",
    "Mysore",
    "Mangalore",
    "Chennai",
    "Coimbatore",
    "Madurai",
    "Hyderabad",
    "Warangal",
    "Ahmedabad",
    "Surat",
    "Vadodara",
    "Rajkot",
    "Gandhinagar",
    "Jaipur",
    "Jodhpur",
    "Udaipur",
    "Kota",
    "New Delhi",
    "Gurugram",
    "Noida",
    "Faridabad",
    "Lucknow",
    "Kanpur",
    "Varanasi",
    "Agra",
    "Prayagraj",
    "Patna",
    "Ranchi",
    "Kolkata",
    "Howrah",
    "Bhubaneswar",
    "Cuttack",
    "Bhopal",
    "Indore",
    "Jabalpur",
    "Raipur",
    "Chandigarh",
    "Amritsar",
    "Ludhiana",
    "Jalandhar",
    "Dehradun",
    "Haridwar",
    "Shimla",
    "Srinagar",
    "Jammu",
    "Guwahati",
    "Thiruvananthapuram",
    "Kochi",
    "Kozhikode",
    "Visakhapatnam",
    "Vijayawada",
]

def extract_location(text: str):
    text = normalize_text(text)

    locations = sorted(
        INDIAN_LOCATIONS,
        key=len,
        reverse=True
    )

    found = []

    for location in locations:
        pattern = r"(?<!\w)" + re.escape(location.lower()) + r"(?!\w)"

        for match in re.finditer(pattern, text):

            # Ignore a match if it overlaps an already found,
            # longer location name.
            overlaps = any(
                match.start() < item["end"]
                and match.end() > item["start"]
                for item in found
            )

            if not overlaps:
                found.append({
                    "location": location,
                    "start": match.start(),
                    "end": match.end()
                })

    if not found:
        return None

    found.sort(key=lambda item: item["start"])

    return found[-1]["location"]


def parse_rfq(text: str) -> dict:
    category = extract_category(text)
    quantity, unit = extract_quantity(text)
    gsm = extract_gsm(text)
    micron = extract_micron(text)
    location = extract_location(text)

    return {
        "category": category,
        "quantity": quantity,
        "unit": unit,
        "gsm": gsm,
        "micron": micron,
        "location": location
    }

