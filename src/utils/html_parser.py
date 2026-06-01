from bs4 import BeautifulSoup


SECTION_SELECTORS = (
    ("Job Title", ("h1.top-card-layout__title", "h1.topcard__title")),
    ("Company Info", ("div.topcard__flavor-row",)),
    (
        "Core Description",
        (
            "div.show-more-less-html__markup",
            "section.show-more-less-html",
        ),
    ),
    ("Job Criteria", ("ul.description__job-criteria-list",)),
    (
        "Compensation",
        (
            "div.compensation__code-and-amount",
            "div.base-main-card__metadata",
        ),
    ),
)


def extract_job_details(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html or "", "html.parser")

    for element in soup(("script", "style", "noscript")):
        element.decompose()

    sections = []
    seen_text = set()

    for label, selectors in SECTION_SELECTORS:
        section_texts = []
        for selector in selectors:
            for element in soup.select(selector):
                text = _clean_text(element)
                if text and text not in seen_text:
                    section_texts.append(text)
                    seen_text.add(text)
        if section_texts:
            sections.append(f"{label}:\n" + "\n".join(section_texts))

    if sections:
        return "\n\n".join(sections)

    return _clean_text(soup)


def _clean_text(element) -> str:
    lines = []
    for line in element.get_text("\n", strip=True).splitlines():
        line = " ".join(line.split())
        if line:
            lines.append(line)
    return "\n".join(lines)
