import { fromMarkdown } from 'mdast-util-from-markdown';
import type { Section } from './types';
const aliases: Record<string, Section> = {
  'conversation briefing': 'briefing',
  briefing: 'briefing',
  'company overview': 'company',
  company: 'company',
  'industry overview': 'industry',
  industry: 'industry',
  'financial overview': 'financial',
  financial: 'financial',
  'financial context': 'financial',
  news: 'news',
  'recent news': 'news',
  references: 'references',
  sources: 'references',
};
type MarkdownNode = {
  type: string;
  value?: string;
  depth?: number;
  url?: string;
  children?: MarkdownNode[];
  position?: { start: { offset?: number }; end: { offset?: number } };
};
export type ParsedReport = {
  sections: Partial<Record<Section, string>>;
  fallback: boolean;
  references: { title: string; url: string }[];
};
export function safeURL(url: string) {
  try {
    const parsed = new URL(url);
    return ['https:', 'http:'].includes(parsed.protocol) && !parsed.username && !parsed.password
      ? parsed.href
      : undefined;
  } catch {
    return undefined;
  }
}
function text(node: MarkdownNode): string {
  return node.value || node.children?.map(text).join('') || '';
}
export function parseReport(markdown: string): ParsedReport {
  const sections: Partial<Record<Section, string>> = {};
  const tree = fromMarkdown(markdown);
  let current: Section | undefined;
  let start = 0;
  let unknown = false;
  let hasPreamble = false;
  const flush = (end: number) => {
    if (current)
      sections[current] = (sections[current] || '') + markdown.slice(start, end).trim() + '\n';
  };
  for (const node of tree.children) {
    if (node.type === 'heading' && node.depth === 2) {
      const offset = node.position?.start.offset || 0;
      flush(offset);
      current = aliases[text(node).trim().toLowerCase()];
      start = offset;
      if (!current) unknown = true;
    } else if (!current && !(node.type === 'heading' && node.depth === 1)) hasPreamble = true;
  }
  flush(markdown.length);
  const recognized = Object.keys(sections).filter((k) => k !== 'references');
  const fallback = recognized.length === 0 || unknown || hasPreamble;
  if (fallback) sections.full = markdown;
  const references: { title: string; url: string }[] = [];
  const add = (title: string, rawURL: string) => {
    const url = safeURL(rawURL);
    if (url && !references.some((r) => r.url === url))
      references.push({ title: title || new URL(url).hostname, url });
  };
  const sourceTree = fromMarkdown(sections.references || '');
  function walk(node: MarkdownNode) {
    if (node.type === 'link' && node.url) {
      add(text(node), node.url);
      return;
    }
    if (node.type === 'text')
      for (const match of (node.value || '').matchAll(/https?:\/\/[^\s<>]+/g)) {
        let raw = match[0].replace(/[.,;]+$/, '');
        while (
          raw.endsWith(')') &&
          (raw.match(/\)/g) || []).length > (raw.match(/\(/g) || []).length
        )
          raw = raw.slice(0, -1);
        add('', raw);
      }
    node.children?.forEach(walk);
  }
  walk(sourceTree);
  return { sections, fallback, references };
}
