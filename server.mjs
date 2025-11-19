import express from 'express';
import cors from 'cors';
import { fetch } from 'undici';

// Simple structured logger
const DEBUG = (process.env.DEBUG || 'true').toLowerCase() === 'true';
function log(level, msg, extra = {}) {
  if (!DEBUG && level === 'debug') return;
  const ts = new Date().toISOString();
  // eslint-disable-next-line no-console
  console.log(JSON.stringify({ ts, level, msg, ...extra }));
}

const PUBMED_BASE = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils';
const PUBMED_EMAIL = process.env.PUBMED_EMAIL || '';
const PUBMED_API_KEY = process.env.PUBMED_API_KEY || '';
const MCP_TOOL_NAME = 'pubmed-mcp';

function addNcbiParams(url) {
  const u = new URL(url);
  if (PUBMED_EMAIL) u.searchParams.set('email', PUBMED_EMAIL);
  u.searchParams.set('tool', MCP_TOOL_NAME);
  if (PUBMED_API_KEY) u.searchParams.set('api_key', PUBMED_API_KEY);
  return u.toString();
}

async function esearch(term, retmax = 10) {
  const rawUrl = `${PUBMED_BASE}/esearch.fcgi?db=pubmed&retmode=json&retmax=${retmax}&term=${encodeURIComponent(term)}`;
  const url = addNcbiParams(rawUrl);
  const t0 = Date.now();
  log('info', 'esearch.request', { url });
  const res = await fetch(url, { headers: { 'User-Agent': MCP_TOOL_NAME } });
  log('info', 'esearch.response', { status: res.status, ms: Date.now() - t0 });
  if (!res.ok) throw new Error(`esearch failed: ${res.status}`);
  const data = await res.json();
  return data.esearchresult?.idlist ?? [];
}

async function esummary(ids) {
  if (!ids.length) return [];
  const rawUrl = `${PUBMED_BASE}/esummary.fcgi?db=pubmed&retmode=json&id=${ids.join(',')}`;
  const url = addNcbiParams(rawUrl);
  const t0 = Date.now();
  log('info', 'esummary.request', { url, count: ids.length });
  const res = await fetch(url, { headers: { 'User-Agent': MCP_TOOL_NAME } });
  log('info', 'esummary.response', { status: res.status, ms: Date.now() - t0 });
  if (!res.ok) throw new Error(`esummary failed: ${res.status}`);
  const data = await res.json();
  const result = data.result || {};
  const uidList = result.uids || [];
  return uidList.map((uid) => ({
    pmid: uid,
    title: result[uid]?.title,
    authors: (result[uid]?.authors || []).map((a) => a.name),
    journal: result[uid]?.fulljournalname,
    pubdate: result[uid]?.pubdate,
    doi: result[uid]?.elocationid,
  }));
}

async function efetch(pmid) {
  const rawUrl = `${PUBMED_BASE}/efetch.fcgi?db=pubmed&retmode=xml&id=${pmid}`;
  const url = addNcbiParams(rawUrl);
  const t0 = Date.now();
  log('info', 'efetch.request', { url });
  const res = await fetch(url, { headers: { 'User-Agent': MCP_TOOL_NAME } });
  log('info', 'efetch.response', { status: res.status, ms: Date.now() - t0 });
  if (!res.ok) throw new Error(`efetch failed: ${res.status}`);
  const xml = await res.text();
  return { pmid, xml };
}

// In-memory client registry for SSE streams
const clients = new Map(); // clientId -> res

// Tool implementations as async functions
function formatReferencesPT(items = []) {
  if (!items.length) return '–';
  const blocks = items.map((it, idx) => {
    const n = idx + 1;
    const title = (it.title || '').trim();
    const authorsArr = it.authors || [];
    const authors = authorsArr.length > 0
      ? `${authorsArr.slice(0, 3).join(', ')}${authorsArr.length > 3 ? ' et al.' : ''}.`
      : '';
    const year = String(it.pubdate || '').split(' ')[0] || '';
    const journal = it.journal ? `${it.journal}.` : '';
    const doiLine = it.doi ? `doi:${it.doi}.` : '';
    const pmidLine = it.pmid ? `PMID: ${it.pmid}.` : '';
    const url = it.pmid ? `https://pubmed.ncbi.nlm.nih.gov/${it.pmid}/` : '';

    const lines = [];
    lines.push(`${n}.`);
    if (title) lines.push(title);
    if (authors) lines.push(authors);
    lines.push([journal, year ? `${year}.` : ''].filter(Boolean).join(' '));
    if (doiLine || pmidLine) lines.push([doiLine, pmidLine].filter(Boolean).join(' '));
    if (url) lines.push(url);
    return lines.filter(Boolean).join('\n');
  });
  return blocks.join('\n\n');
}

function buildStructuredPT(items = [], context = {}) {
  if (!items.length) {
    return [
      'Nenhum artigo relevante encontrado.',
      '',
      'Referências:',
      '–'
    ].join('\n');
  }

  const bullets = items.slice(0, 6).map((it, idx) => {
    const n = idx + 1;
    const year = String(it.pubdate || '').split(' ')[0] || '';
    const j = it.journal ? ` — ${it.journal}` : '';
    return `• ${it.title || ''} (${year}${j}) [${n}]`;
  });

  const nextSteps = [
    '• Refinar termos técnicos (MeSH) conforme necessário;',
    '• Considerar filtros por intervalo de datas e tipo de estudo;',
    '• Validar achados com diretrizes clínicas atualizadas.'
  ];

  return [
    'Principais Achados:',
    ...bullets,
    '',
    'Mais Importantes a Não Perder:',
    '• Verificar estudos de alta qualidade (revisões sistemáticas/ensaios clínicos);',
    '• Avaliar riscos/benefícios reportados e desfechos clínicos;',
    '',
    'História e Exames Adicionais Sugeridos:',
    ...nextSteps,
    '',
    'Referências:',
    formatReferencesPT(items)
  ].join('\n');
}

async function tool_search_pubmed_key_words(args) {
  const term = args.key_words;
  const n = typeof args.num_results === 'number' ? args.num_results : 10;
  const startTime = Date.now();

  log('info', '🔍 PubMed Search: Searching by keywords', { term, num_results: n });

  let ids = await esearch(term, n);
  if (ids.length === 0 && term.includes(' ')) {
    const quoted = `"${term}"`;
    log('debug', '📝 Fallback search with quoted term', { quoted });
    ids = await esearch(quoted, n);
  }

  const items = ids.length ? await esummary(ids) : [];
  const elapsed = Date.now() - startTime;

  log('info', '✅ Search completed', {
    term,
    ids_found: ids.length,
    articles_retrieved: items.length,
    response_time_ms: elapsed
  });

  const formattedText = buildStructuredPT(items, { term });
  return { content: [
    { type: 'text', text: formattedText },
  ] };
}

async function tool_search_pubmed_advanced(args) {
  const parts = [];
  if (args.term) parts.push(args.term);
  if (args.title) parts.push(`${args.title}[Title]`);
  if (args.author) parts.push(`${args.author}[Author]`);
  if (args.journal) parts.push(`${args.journal}[Journal]`);
  if (args.start_date || args.end_date) {
    const start = args.start_date || '1900/01/01';
    const end = args.end_date || '3000/12/31';
    parts.push(`${start}:${end}[Date - Publication]`);
  }

  const term = parts.join(' AND ').trim() || '';
  const n = typeof args.num_results === 'number' ? args.num_results : 10;
  const startTime = Date.now();

  log('info', '🔍 PubMed Advanced Search', {
    term,
    filters: {
      title: args.title || null,
      author: args.author || null,
      journal: args.journal || null,
      date_range: (args.start_date || args.end_date) ? `${args.start_date} to ${args.end_date}` : null
    },
    num_results: n
  });

  let ids = await esearch(term || '*', n);
  if (ids.length === 0 && args.term) {
    const simple = String(args.term).split(' ').slice(0, 3).join(' ');
    log('debug', '📝 Fallback to simple search', { simple });
    ids = await esearch(simple, n);
  }

  const items = ids.length ? await esummary(ids) : [];
  const elapsed = Date.now() - startTime;

  log('info', '✅ Advanced search completed', {
    ids_found: ids.length,
    articles_retrieved: items.length,
    response_time_ms: elapsed
  });

  const formattedText = buildStructuredPT(items, { term, filters: args });
  return { content: [
    { type: 'text', text: formattedText },
  ] };
}

function formatArticleMetadata(item) {
  if (!item) return "Article not found.";

  const lines = [
    `## Article Details\n`,
    `**Title**: ${item.title || 'N/A'}`,
    `**PMID**: [${item.pmid}](https://pubmed.ncbi.nlm.nih.gov/${item.pmid}/)`,
  ];

  if (item.authors && item.authors.length > 0) {
    lines.push(`**Authors**: ${item.authors.join('; ')}`);
  }
  if (item.journal) lines.push(`**Journal**: ${item.journal}`);
  if (item.pubdate) lines.push(`**Published**: ${item.pubdate}`);
  if (item.doi) lines.push(`**DOI**: ${item.doi}`);

  return lines.join('\n');
}

async function tool_get_pubmed_article_metadata(args) {
  const items = await esummary([String(args.pmid)]);
  const item = items[0] || null;
  log('info', 'tool.get_pubmed_article_metadata.done', { pmid: args.pmid, found: !!item });

  const formattedText = formatArticleMetadata(item);
  return { content: [{ type: 'text', text: formattedText }] };
}

async function tool_download_pubmed_pdf(args) {
  const data = await efetch(String(args.pmid));
  return { content: [{ type: 'text', text: `EFetch XML retrieved for PMID ${data.pmid}` }] };
}

function listTools() {
  return [
    {
      name: 'search_pubmed_key_words',
      description: 'Search PubMed articles using keywords.',
      inputSchema: {
        type: 'object',
        properties: {
          key_words: { type: 'string' },
          num_results: { type: 'integer', minimum: 1, maximum: 50, default: 10 }
        },
        required: ['key_words']
      }
    },
    {
      name: 'search_pubmed_advanced',
      description: 'Advanced PubMed search with filters.',
      inputSchema: {
        type: 'object',
        properties: {
          term: { type: ['string', 'null'] },
          title: { type: ['string', 'null'] },
          author: { type: ['string', 'null'] },
          journal: { type: ['string', 'null'] },
          start_date: { type: ['string', 'null'] },
          end_date: { type: ['string', 'null'] },
          num_results: { type: 'integer', minimum: 1, maximum: 50, default: 10 }
        }
      }
    },
    {
      name: 'get_pubmed_article_metadata',
      description: 'Get article metadata by PMID.',
      inputSchema: {
        type: 'object',
        properties: { pmid: { type: ['string', 'integer'] } },
        required: ['pmid']
      }
    },
    {
      name: 'download_pubmed_pdf',
      description: 'Attempt to download full-text PDF by PMID.',
      inputSchema: {
        type: 'object',
        properties: { pmid: { type: ['string', 'integer'] } },
        required: ['pmid']
      }
    }
  ];
}

async function callTool(name, args) {
  if (name === 'search_pubmed_key_words') return tool_search_pubmed_key_words(args);
  if (name === 'search_pubmed_advanced') return tool_search_pubmed_advanced(args);
  if (name === 'get_pubmed_article_metadata') return tool_get_pubmed_article_metadata(args);
  if (name === 'download_pubmed_pdf') return tool_download_pubmed_pdf(args);
  throw new Error(`Unknown tool: ${name}`);
}

function writeSSE(res, obj) {
  res.write(`data: ${JSON.stringify(obj)}\n\n`);
}

const app = express();
app.use(cors());
app.use(express.json({ limit: '1mb' }));

// SSE endpoint (read stream)
app.get('/sse', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders?.();

  const clientId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  clients.set(clientId, res);

  // Initial ready message
  writeSSE(res, { jsonrpc: '2.0', method: 'ready', params: { server: 'pubmed-mcp', version: '1.0.0' } });

  req.on('close', () => {
    clients.delete(clientId);
  });
});

// Write endpoint (JSON-RPC requests)
app.post('/sse', async (req, res) => {
  const payload = req.body || {};
  const id = payload.id ?? null;
  const method = payload.method;
  const params = payload.params || {};

  try {
    log('info', 'rpc.request', { id, method, params });
    // Some clients may send keepalive or empty posts; acknowledge gracefully
    if (!method) {
      const response = { jsonrpc: '2.0', id, result: {} };
      for (const [, stream] of clients) writeSSE(stream, response);
      return res.json(response);
    }
    if (method === 'initialize') {
      const result = {
        protocolVersion: '2024-11-05',
        serverInfo: { name: 'pubmed-mcp', version: '1.0.0' },
        capabilities: { tools: {}, prompts: {} }
      };
      const response = { jsonrpc: '2.0', id, result };
      for (const [, stream] of clients) writeSSE(stream, response);
      log('info', 'rpc.response', { id, method, ok: true });
      return res.json(response);
    }
    if (method === 'tools/list' || method === 'tools.list' || method === 'list_tools') {
      const tools = listTools();
      const response = { jsonrpc: '2.0', id, result: { tools } };
      for (const [, stream] of clients) writeSSE(stream, response);
      log('info', 'rpc.response', { id, method, count: tools.length });
      return res.json(response);
    }
    if (method === 'tools/call' || method === 'tools.call' || method === 'call_tool') {
      const name = params.name;
      const args = params.arguments || {};
      const result = await callTool(name, args);
      const response = { jsonrpc: '2.0', id, result };
      for (const [, stream] of clients) writeSSE(stream, response);
      log('info', 'rpc.response', { id, method, tool: name, ok: true });
      return res.json(response);
    }
    if (method === 'prompts/list' || method === 'prompts.list') {
      const response = { jsonrpc: '2.0', id, result: { prompts: [{ name: 'deep_paper_analysis' }] } };
      for (const [, stream] of clients) writeSSE(stream, response);
      log('info', 'rpc.response', { id, method, count: 1 });
      return res.json(response);
    }
    if (method === 'prompts/call' || method === 'prompts.call') {
      const pmid = params.arguments?.pmid;
      const items = await esummary([String(pmid)]);
      const item = items[0] || {};
      const prompt = `Perform a deep analysis of the PubMed paper.\n\nTitle: ${item?.title}\nJournal: ${item?.journal} (${item?.pubdate})\nAuthors: ${(item?.authors || []).join(', ')}\nPMID: ${item?.pmid}`;
      const response = { jsonrpc: '2.0', id, result: { messages: [{ role: 'user', content: prompt }] } };
      for (const [, stream] of clients) writeSSE(stream, response);
      log('info', 'rpc.response', { id, method, ok: true });
      return res.json(response);
    }

    // Unknown method
    const response = { jsonrpc: '2.0', id, error: { code: -32601, message: 'Method not found' } };
    for (const [, stream] of clients) writeSSE(stream, response);
    log('warn', 'rpc.unknown_method', { id, method });
    return res.json(response);
  } catch (e) {
    const response = { jsonrpc: '2.0', id, error: { code: -32000, message: String(e.message || e) } };
    for (const [, stream] of clients) writeSSE(stream, response);
    log('error', 'rpc.error', { id, method, error: String(e.message || e) });
    return res.json(response);
  }
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'pubmed-mcp' });
});

const host = process.env.HOST || '0.0.0.0';
const port = Number(process.env.PORT || 8000);
app.listen(port, host, () => {
  console.log(`PubMed MCP HTTP listening on http://${host}:${port}/sse`);
});
