# RFQ Parser --- Implementation Notes

## Approach

Implemented `parse_rfq(text)` in Python using standard-library modules
(`re` and `unicodedata`). The parser normalizes text, then uses separate
helper functions to identify the packaging category, order quantity and
unit, GSM, micron, and an Indian city/state from a predefined location
list. Numeric parsing supports formats including `k`, thousand,
hazaar/hazar/hajaar, lakh/lac, crore, and comma-separated Indian
numbers. Context rules exclude GSM, micron, and bag-capacity figures
from order quantity. The function returns the six required fields:
`category`, `quantity`, `unit`, `gsm`, `micron`, and `location`.

## Test results

Ran `python score.py my_tests.jsonl` on 40 test examples.

-   Category: 40/40 (100%)
-   Quantity: 40/40 (100%)
-   Unit: 40/40 (100%)
-   GSM: 40/40 (100%)
-   Micron: 40/40 (100%)
-   Location: 40/40 (100%)
-   All fields correct: 40/40 (100%)
-   Reported runtime: 0.02 seconds

This score describes performance on the supplied 40-example test set; it
does not establish accuracy on unseen production RFQs.

## Three limitations / examples that may be parsed incorrectly

1.  **Multiple products in one message:**
    `500 pcs BOPP bags and 2000 pcs woven sacks` contains two line
    items, but the current output schema and parser return only one
    category and one quantity. The parser may combine fields from
    different products.
2.  **Ambiguous category keyword:** `We need bulk packaging material`
    can trigger `fibc` because the current category rule treats the word
    `bulk` as an FIBC indicator, even when the buyer may mean a large
    order generally.
3.  **Multiple locations:**
    `Need BOPP bags 500 pcs, delivery to Pune, supplier in Mumbai` may
    return `Mumbai` because the parser selects the last recognized
    location rather than identifying the delivery destination
    semantically.

## What I would do with 1,000 labelled RFQs

I would first inspect and label the messages consistently, including
product line items, quantities, units, specifications, and delivery
locations. I would split the data into training/development and held-out
test sets, keeping similar messages together to reduce leakage. I would
analyze errors by field and category, expand the location and
terminology coverage from the labelled data, and add regression tests
for every corrected error. If rule-based patterns continued to struggle
with varied wording, I would evaluate an offline open-source NER or
text-classification model against the same held-out set. I would compare
it with the current rules on accuracy, speed, and maintainability before
adopting it.

## Monitoring in real use

I would log parser version, field-level outputs, confidence or
rule-match indicators, processing time, and validation failures while
protecting customer data. I would review low-confidence, missing, and
user-corrected fields with human reviewers, track field-level accuracy
and error rates over time, and add confirmed corrections to a regression
test set. I would monitor changes in message patterns and retrain or
update rules only after reviewing a representative sample.

## Tools used

-   Python standard library (`re`, `unicodedata`) was used to implement
    the parser; VS Code/PowerShell were used to edit and run the
    project.
-   ChatGPT was used for implementation guidance, debugging
    explanations, and test-case/documentation drafting; I ran the code
    and scorer locally and reviewed the results.
