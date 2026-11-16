// Saved editorial example from dated primary announcements; not a live pipeline result.
export const SAMPLE_COMPANY = {
  company: 'Cursor',
  company_url: 'https://cursor.com',
  industry: 'AI developer tools',
  hq_location: '',
};
export const SAMPLE_PERIOD = 'November 13, 2025';
export const SAMPLE_REPORT = `# Cursor Research Report

## Conversation Briefing
### The short version
Cursor is Anysphere's AI coding product. Its 2025 releases expanded into parallel agents and enterprise controls. The question to explore: **can teams ship reliable software faster, after review and testing?** [Cursor 2.0](https://cursor.com/blog/2-0) · [Enterprise announcement](https://cursor.com/blog/enterprise)

### What changed
* **October 29 · Agents move to the center.** Cursor 2.0 introduced Composer, its first coding model, and an interface for parallel agents. **Interpretation:** speed matters only if changes can be reviewed and tested. [Product announcement](https://cursor.com/blog/2-0)
* **October 31 · More controls for engineering teams.** Cursor announced hooks, shared team rules, analytics, audit logs, and sandboxing. **Interpretation:** adoption depends on governance as well as developer experience. [Enterprise announcement](https://cursor.com/blog/enterprise)
* **November 13 · A larger research budget.** The company announced a **$2.3B Series D** at a **$29.3B post-money valuation**. **Interpretation:** more capital supports research, but does not prove profitability. [Funding announcement](https://cursor.com/blog/series-d)

### What to clarify
* **Quality:** does faster generation reduce delivery time after review, testing, and rework?
* **Economics:** the selected announcements do not disclose model-serving costs, margins, or retention.
* **Adoption:** company-wide usage claims do not establish how many employees use the product, or whether it is deployed across an entire organization.

### Questions to bring
1. How do you measure useful agent output beyond lines of generated code?
2. Where do users lose the most time today: specifying tasks, reviewing changes, or testing them?
3. What determines when a team should use Composer versus another model?
4. Which governance requirements most often block a developer pilot from becoming a wider rollout?
5. What evidence would show that parallel agents improve delivery without increasing review burden?



## Company Overview
### What the company builds
Anysphere makes Cursor, a developer tool for working with AI on software projects. Its October 2025 release introduced an agent-focused interface while retaining access to a classic editor layout. [Cursor 2.0](https://cursor.com/blog/2-0)

### Product and customers
* **Coding model:** Composer was introduced for low-latency coding tasks.
* **Agent workflow:** multiple agents can work in parallel using isolated worktrees or remote machines.
* **Team controls:** shared rules, audit logs, hooks, and sandboxing support organizational workflows. [Enterprise announcement](https://cursor.com/blog/enterprise)

### Evidence of adoption
In June 2025, Cursor said its product was used at more than half of Fortune 500 companies, naming NVIDIA, Uber, and Adobe. This is a company-reported usage claim, not evidence of organization-wide contracts or standardized deployment. [Series C announcement](https://cursor.com/blog/series-c)

## Industry Overview
### A shift from suggestions to delegated work
Cursor's parallel-agent release and GitHub's coding agent illustrate competing approaches to delegating software tasks. GitHub's May 2025 announcement describes an agent that works on assigned issues and produces draft pull requests. [GitHub announcement](https://github.blog/news-insights/product-news/github-copilot-meet-the-new-coding-agent/)

### A practical alternative to evaluate
**GitHub Copilot coding agent** is a relevant comparison for teams whose work already runs through GitHub issues, pull requests, and Actions. Cursor's announcement instead emphasizes working with agents inside its development interface. These sources describe workflows; they do not establish a performance winner.

### What a buyer should compare
**Research interpretation:** run both approaches on representative tasks. Compare accepted changes, review effort, test outcomes, permissions, and total cost per completed task. A compelling demonstration or model benchmark alone does not establish value in your codebase.

## Financial Overview
### Dated funding and commercial milestones
Figures below are US dollars and reflect company announcements, not audited financial statements.

| Announcement | Reported funding | Reported valuation | Commercial metric |
| --- | ---: | ---: | --- |
| June 6, 2025 · Series C | $900M | $9.9B | Over $500M ARR |
| November 13, 2025 · Series D | $2.3B | $29.3B post-money | Over $1B annualized revenue |

Sources: [Series C](https://cursor.com/blog/series-c) · [Series D](https://cursor.com/blog/series-d).

### Read these figures correctly
**Annualized revenue is not full-year recognized revenue.** The two announcements also use different labels: ARR in June and annualized revenue in November. Their calculation methods are not explained in these posts, so an exact growth rate should not be inferred. Funding, valuation, and revenue describe different things.

### What remains unknown
The selected announcements do not establish profitability, cash burn, gross margin, or customer retention. A valuation is a financing figure, not cash earned by the business.

## News
### November 13, 2025 · Series D announced
Cursor named Accel, Thrive, and Andreessen Horowitz among existing investors, with Coatue, NVIDIA, and Google joining the round. The company said the capital would support research. [Announcement](https://cursor.com/blog/series-d)

### October 31, 2025 · Enterprise controls expanded
The announcement described hooks for observing or controlling agent actions, an audit log covering 19 event types, and sandbox restrictions on network and file access. These are company-described capabilities, not an independent security assessment. [Announcement](https://cursor.com/blog/enterprise)

### October 29, 2025 · Cursor 2.0 and Composer released
Alongside Composer and parallel agents, the release added a native browser tool for testing changes and a workflow for inspecting agent edits. Cursor also retained access to its classic editor layout. [Announcement](https://cursor.com/blog/2-0)

## References
* [Series D · November 13, 2025](https://cursor.com/blog/series-d)
* [Enterprise controls · October 31, 2025](https://cursor.com/blog/enterprise)
* [Cursor 2.0 & Composer · October 29, 2025](https://cursor.com/blog/2-0)
* [Series C · June 6, 2025](https://cursor.com/blog/series-c)
* [GitHub Copilot agent · May 19, 2025](https://github.blog/news-insights/product-news/github-copilot-meet-the-new-coding-agent/)

Historical example covering announcements through November 13, 2025. Company statements are attributed, and research interpretations are identified. This saved report is not a live run or a current company-status update.
`;
