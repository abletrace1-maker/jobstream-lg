from src.utils.html_parser import extract_job_details


def test_extract_job_details_targets_linkedin_sections():
    raw_html = """
    <html>
      <head><style>.hidden { display: none; }</style></head>
      <body>
        <nav>Navigation noise</nav>
        <h1 class="top-card-layout__title font-sans text-lg papabear:text-xl font-bold leading-open text-color-text mb-0 topcard__title">Senior Data Analyst</h1>
        <div class="topcard__flavor-row">
          <a class="topcard__org-name-link">Acme Analytics</a>
          <span>Remote</span>
        </div>
        <section class="show-more-less-html">
          <div class="show-more-less-html__markup show-more-less-html__markup--clamp-after-5 relative overflow-hidden">
            <p>Build dashboards and data pipelines.</p>
            <p>Requires SQL and Python.</p>
          </div>
        </section>
        <ul class="description__job-criteria-list">
          <li><h3>Seniority level</h3><span>Mid-Senior level</span></li>
          <li><h3>Employment type</h3><span>Full-time</span></li>
        </ul>
        <div class="compensation__code-and-amount">$120,000 - $140,000</div>
      </body>
    </html>
    """

    result = extract_job_details(raw_html)

    assert "Job Title:\nSenior Data Analyst" in result
    assert "Company Info:" in result
    assert "Acme Analytics" in result
    assert "Remote" in result
    assert "Core Description:" in result
    assert "Build dashboards and data pipelines." in result
    assert "Requires SQL and Python." in result
    assert "Job Criteria:" in result
    assert "Mid-Senior level" in result
    assert "Compensation:\n$120,000 - $140,000" in result
    assert "Navigation noise" not in result


def test_extract_job_details_skips_missing_sections():
    raw_html = """
    <html>
      <body>
        <h1 class="topcard__title">Backend Engineer</h1>
        <div class="show-more-less-html__markup">Own APIs.</div>
      </body>
    </html>
    """

    result = extract_job_details(raw_html)

    assert "Job Title:\nBackend Engineer" in result
    assert "Core Description:\nOwn APIs." in result
    assert "Company Info:" not in result
    assert "Compensation:" not in result


def test_extract_job_details_falls_back_to_page_text():
    assert extract_job_details("<html><body><main>Plain posting text</main></body></html>") == "Plain posting text"
