# LinkedIn Job Page - HTML Section Mapping

Below is a map of the important HTML tags (sections/divs) found on public LinkedIn job view pages that contain relevant job data. This map can be used by downstream automation tools (like BeautifulSoup) to target and extract specific data points reliably.

## 1. Job Title
**HTML Tag:** `<h1 class="top-card-layout__title font-sans text-lg papabear:text-xl font-bold leading-open text-color-text mb-0 topcard__title">`
* **Description:** Contains the primary job title (e.g., "Project Manager | Remote").

## 2. Company Name & Basic Details
**HTML Tag:** `<div class="topcard__flavor-row">`
* **Description:** Contains the name of the company hiring, the location, and when it was posted. 
* **Note:** The company name itself is often wrapped in an anchor `<a>` tag with the class `topcard__org-name-link`.

## 3. The Core Job Description
**HTML Tag:** `<div class="show-more-less-html__markup show-more-less-html__markup--clamp-after-5 relative overflow-hidden">`
* **Parent Tag:** `<section class="show-more-less-html">`
* **Description:** This is the most important section. It holds the raw, unformatted text of the entire job posting provided by the employer (including role responsibilities, requirements, application process, and company background).

## 4. Job Criteria Metadata (Seniority, Type, Function, Industry)
**HTML Tag:** `<ul class="description__job-criteria-list">`
* **Description:** A structured list containing the categorized metadata about the job.
* **Child Elements:** It contains several `<li>` tags, usually detailing:
  * **Seniority level** (e.g., "Associate", "Mid-Senior level")
  * **Employment type** (e.g., "Full-time", "Contract")
  * **Job function** (e.g., "Management", "Engineering")
  * **Industries** (e.g., "Architecture and Planning")

## 5. Pay Range / Compensation (If Available)
**HTML Tag:** `<div class="compensation__code-and-amount">` or sometimes grouped directly inside `<div class="base-main-card__metadata">` on smaller cards.
* **Description:** Contains the salary or hourly wage range if the poster has chosen to include it.

---
**Note for Automation:** The `show-more-less-html__markup` div is the most reliable anchor point across all public LinkedIn job postings for grabbing the actual text of the job description without the surrounding UI noise.