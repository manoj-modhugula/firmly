import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseReport, safeURL } from './report';
import { addEvent, CATEGORIES, researchStage } from './progress';
test('known report sections preserve nested headings and source links', () => {
  const parsed = parseReport(
    '# Acme\n\n## Company Overview\n### Product\nText\n\n## News\nNews text\n\n## References\n[Acme](https://example.org/source)',
  );
  assert.equal(parsed.fallback, false);
  assert.match(parsed.sections.company!, /### Product/);
  assert.equal(parsed.references[0].url, 'https://example.org/source');
});
test('unknown headings and nonstandard reports retain the complete text', () => {
  const content = '# Report\nIntro\n\n## Unexpected heading\nImportant facts';
  assert.equal(parseReport(content).sections.full, content);
});
test('sparse reports do not invent absent sections', () => {
  const parsed = parseReport('## Company Overview\nOnly company information');
  assert.equal(parsed.sections.financial, undefined);
});
test('heading-like text inside fenced code stays in the current section', () => {
  const parsed = parseReport('## Company Overview\n```text\n## News\n```\nProduct');
  assert.equal(parsed.sections.news, undefined);
  assert.match(parsed.sections.company!, /## News/);
});
test('unsafe source URLs are rejected', () => {
  assert.equal(safeURL('javascript:alert(1)'), undefined);
  assert.equal(safeURL('data:text/html,test'), undefined);
  assert.equal(safeURL('https://example.org'), 'https://example.org/');
});
test('source links deduplicate and UI event history stays bounded', () => {
  assert.equal(
    parseReport('## References\n[One](https://example.org/)\n[Two](https://example.org/)')
      .references.length,
    1,
  );
  let events = [] as { type: string }[];
  for (let i = 0; i < 200; i++) events = addEvent(events, { type: 'progress' });
  assert.equal(events.length, 80);
  assert.equal(addEvent(events, { type: 'report_chunk' }).length, 80);
});
test('source links preserve parentheses and encoded paths', () => {
  const report =
    '## References\n* [Company](<https://example.org/Acme_(company)>)\n* https://example.org/report?q=a%20b';
  const parsed = parseReport(report);
  assert.equal(parsed.references[0].url, 'https://example.org/Acme_(company)');
  assert.equal(parsed.references[1].url, 'https://example.org/report?q=a%20b');
});
test('setext headings and formatted headings are parsed structurally', () => {
  const parsed = parseReport('**Company Overview**\n--------------------\nCompany details');
  assert.equal(parsed.fallback, false);
  assert.match(parsed.sections.company!, /Company details/);
});

test('saved example opens a source-backed briefing without hiding research sections', async () => {
  const { SAMPLE_REPORT } = await import('./sample');
  const parsed = parseReport(SAMPLE_REPORT);
  assert.equal(parsed.fallback, false);
  for (const section of [
    'briefing',
    'company',
    'industry',
    'financial',
    'news',
    'references',
  ] as const)
    assert.ok(parsed.sections[section], section);
  assert.match(parsed.sections.briefing!, /### Questions to bring/);
  assert.match(parsed.sections.briefing!, /Interpretation/);
  assert.equal(parsed.references.length, 5);
});

test('progress waits for all parallel tracks before showing collection', () => {
  assert.equal(researchStage([])?.[0], 'company_context');
  assert.equal(researchStage(['company_context']), undefined);
  assert.equal(researchStage(['company_context', 'company_track']), undefined);
  assert.equal(
    researchStage(['company_context', ...CATEGORIES.map((category) => category.node)])?.[0],
    'gather_stage',
  );
  assert.equal(
    researchStage([
      'company_context',
      ...CATEGORIES.map((category) => category.node),
      'gather_stage',
    ])?.[0],
    'selection_stage',
  );
});
