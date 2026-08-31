from services.ai_extraction import extract_crm_fields


test_transcript = """
Hi, I'm Ramesh. I need Polyhex fencing for around 800 feet
for my farmhouse in Coimbatore. I am interested in getting
the quotation. Please call me on Friday. I am looking to
complete the fencing soon.
"""


result = extract_crm_fields(test_transcript)

print("\nAI EXTRACTION RESULT:\n")
print(result)