# ui/category_mappings.py

YES_NO = {
    0: "No",
    1: "Yes"
}

GENDER = {
    0: "Female",
    1: "Male"
}

MARITAL_STATUS = {
    1: "Single",
    2: "Married",
    3: "Widowed",
    4: "Divorced",
    5: "De facto union",
    6: "Legally separated"
}

APPLICATION_MODE = {
    1: "1st phase - general contingent",
    2: "Ordinance No. 612/93",
    5: "1st phase - special contingent (Azores)",
    7: "Holder of another higher education course",
    10: "Ordinance No. 854-B/99",
    15: "International student (Bachelor)",
    16: "1st phase - special contingent (Madeira)",
    17: "2nd phase - general contingent",
    18: "3rd phase - general contingent",
    26: "Different Plan",
    27: "Other Institution",
    39: "Over 23 years old",
    42: "Transfer",
    43: "Change of course",
    44: "Technological specialization diploma",
    51: "Change of institution/course",
    53: "Short-cycle diploma",
    57: "Change of institution/course (International)"
}

COURSE = {
    33: "Biofuel Production Technologies",
    171: "Animation and Multimedia Design",
    8014: "Social Service (Evening)",
    9003: "Agronomy",
    9070: "Communication Design",
    9085: "Veterinary Nursing",
    9119: "Informatics Engineering",
    9130: "Equinculture",
    9147: "Management",
    9238: "Social Service",
    9254: "Tourism",
    9500: "Nursing",
    9556: "Oral Hygiene",
    9670: "Advertising and Marketing Management",
    9773: "Journalism and Communication",
    9853: "Basic Education",
    9991: "Management (Evening)"
}

ATTENDANCE = {
    0: "Evening",
    1: "Daytime"
}

PREVIOUS_QUALIFICATION = {
    1: "Secondary education",
    2: "Higher education - Bachelor's degree",
    3: "Higher education - Degree",
    4: "Higher education - Master's",
    5: "Higher education - Doctorate",
    6: "Attended higher education",
    9: "12th year - not completed",
    10: "11th year - not completed",
    12: "Other - 11th year",
    14: "10th year",
    15: "10th year - not completed",
    19: "Basic education - 3rd cycle",
    38: "Basic education - 2nd cycle",
    39: "Technological specialization course",
    40: "Higher education degree - 1st cycle",
    42: "Professional higher technical course",
    43: "Higher education Master's - 2nd cycle"
}

NATIONALITY = {
    1: "Portuguese",
    2: "German",
    6: "Spanish",
    11: "Italian",
    13: "Dutch",
    14: "English",
    17: "Lithuanian",
    21: "Angolan",
    22: "Cape Verdean",
    24: "Guinean",
    25: "Mozambican",
    26: "Santomean",
    32: "Turkish",
    41: "Brazilian",
    62: "Romanian",
    100: "Moldovan",
    101: "Mexican",
    103: "Ukrainian",
    105: "Russian",
    108: "Cuban",
    109: "Colombian"
}

MOTHER_QUALIFICATION = {
    1: "Secondary education - 12th year",
    2: "Bachelor's degree",
    3: "Higher education degree",
    4: "Master's degree",
    5: "Doctorate",
    6: "Attended higher education",
    9: "12th year - not completed",
    10: "11th year - not completed",
    11: "7th year (old)",
    12: "Other - 11th year",
    14: "10th year",
    18: "General commerce course",
    19: "Basic education - 3rd cycle",
    22: "Technical-professional course",
    26: "7th year",
    27: "2nd cycle general high school",
    29: "9th year - not completed",
    30: "8th year",
    34: "Unknown",
    35: "Cannot read or write",
    36: "Can read without 4th year schooling",
    37: "Basic education - 1st cycle",
    38: "Basic education - 2nd cycle",
    39: "Technological specialization course",
    40: "Higher education degree - 1st cycle",
    41: "Specialized higher studies",
    42: "Professional higher technical course",
    43: "Master's degree - 2nd cycle",
    44: "Doctorate - 3rd cycle"
}

FATHER_QUALIFICATION = {
    **MOTHER_QUALIFICATION,
    13: "2nd year complementary high school",
    20: "Complementary high school course",
    25: "Complementary high school - not completed",
    31: "Administration and Commerce course",
    33: "Supplementary Accounting and Administration"
}

BASE_OCCUPATION = {
    0: "Student",
    1: "Managers / executives",
    2: "Scientific and intellectual professionals",
    3: "Intermediate-level technicians",
    4: "Administrative staff",
    5: "Personal services / security / sales",
    6: "Skilled agriculture / fisheries / forestry",
    7: "Skilled industry / construction / crafts",
    8: "Machine operators / assembly workers",
    9: "Unskilled workers",
    10: "Armed Forces",
    90: "Other",
    99: "Unknown / not specified"
}

MOTHER_OCCUPATION = {
    **BASE_OCCUPATION,
    122: "Health professional",
    123: "Teacher",
    125: "ICT specialist",
    131: "Science / engineering technician",
    132: "Health technician",
    134: "Legal / social / cultural technician",
    141: "Office / secretarial worker",
    143: "Accounting / financial / registry operator",
    144: "Other administrative support",
    151: "Personal service worker",
    152: "Seller",
    153: "Personal care worker",
    171: "Skilled construction worker",
    173: "Printing / precision / craft worker",
    175: "Food / woodworking / clothing worker",
    191: "Cleaning worker",
    192: "Unskilled agricultural worker",
    193: "Unskilled industrial / construction worker",
    194: "Meal preparation assistant"
}

FATHER_OCCUPATION = {
    **BASE_OCCUPATION,
    101: "Armed Forces officer",
    102: "Armed Forces sergeant",
    103: "Other Armed Forces personnel",
    112: "Administrative / commercial services director",
    114: "Hotel / catering / trade services director",
    121: "Physical science / engineering professional",
    122: "Health professional",
    123: "Teacher",
    124: "Finance / accounting professional",
    131: "Science / engineering technician",
    132: "Health technician",
    134: "Legal / social / cultural technician",
    135: "ICT technician",
    141: "Office / secretarial worker",
    143: "Accounting / financial / registry operator",
    144: "Other administrative support",
    151: "Personal service worker",
    152: "Seller",
    153: "Personal care worker",
    154: "Protection / security personnel",
    161: "Market-oriented farmer",
    163: "Subsistence farmer / fisher",
    171: "Skilled construction worker",
    172: "Metalworking worker",
    174: "Electrical / electronics worker",
    175: "Food / woodworking / clothing worker",
    181: "Plant / machine operator",
    182: "Assembly worker",
    183: "Vehicle / mobile equipment operator",
    192: "Unskilled agricultural worker",
    193: "Unskilled industrial / construction worker",
    194: "Meal preparation assistant",
    195: "Street vendor / service provider"
}


CATEGORY_OPTIONS = {
    "Marital Status": MARITAL_STATUS,
    "Application mode": APPLICATION_MODE,
    "Course": COURSE,
    "Daytime/evening attendance": ATTENDANCE,
    "Previous qualification": PREVIOUS_QUALIFICATION,

    # Keep this spelling because it is the spelling in the dataset/model.
    "Nacionality": NATIONALITY,

    "Mother's qualification": MOTHER_QUALIFICATION,
    "Father's qualification": FATHER_QUALIFICATION,
    "Mother's occupation": MOTHER_OCCUPATION,
    "Father's occupation": FATHER_OCCUPATION,

    "Displaced": YES_NO,
    "Educational special needs": YES_NO,
    "Debtor": YES_NO,
    "Tuition fees up to date": YES_NO,
    "Gender": GENDER,
    "Scholarship holder": YES_NO,
    "International": YES_NO
}